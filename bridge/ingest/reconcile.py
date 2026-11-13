"""Turn a stored message into at most one ledger entry per real payment.

Order (SPEC "Data rules"):
  1. same reference (UPI/IMPS/NEFT) -> same payment
  2. same account + amount + direction inside a time window -> same payment,
     only if there is exactly one candidate; more than one -> review
  3. a debit on one own account and a credit on another -> one transfer
Entries wait out a settle window before posting so the other half of a
transfer can still arrive.
"""
import datetime as dt

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from . import accounts, parser
from .models import BalanceObservation, LedgerEntry, ParsedTransaction, RawMessage, ReviewItem

PT = ParsedTransaction
_MONEY_WORDS = __import__("re").compile(
    r"(?i)(rs\.?|inr|₹)\s?[\d,]+(\.\d+)?\s+(has been|have been|is|was)\s+(successfully\s+)?"
    r"(debited|credited|spent|withdrawn|paid|received|refunded|reversed)"
    r"|\b(debited|credited)\s+(with|by|for)\s+(rs\.?|inr|₹)|\bspent (inr|rs\.?|₹)"
)
FLAGGED = (PT.Kind.OWN_TRANSFER, PT.Kind.CARD_PAYMENT)


def _lock():
    # One reconciliation at a time, so two halves of a transfer cannot miss each other.
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(724001)")


def _review(raw, reason, detail="", candidates=(), entry=None):
    if raw is not None:
        raw.status = RawMessage.Status.REVIEW
        raw.status_reason = reason
        raw.save(update_fields=["status", "status_reason", "pattern_ref"])
    return ReviewItem.objects.create(raw=raw, entry=entry, reason=reason, detail=detail[:300], candidates=list(candidates))


def _minutes(name):
    return dt.timedelta(minutes=getattr(settings, name))


def _live(qs):
    return qs.filter(entry__isnull=False).exclude(entry__status=LedgerEntry.Status.CANCELLED)


def _distinct_entries(pts):
    seen, entries = set(), []
    for pt in pts:
        if pt.entry_id not in seen:
            seen.add(pt.entry_id)
            entries.append(pt.entry)
    return entries


def find_same_payment(pt):
    """Return (entry, ambiguous_entries)."""
    base = _live(
        PT.objects.filter(firefly_account_id=pt.firefly_account_id, direction=pt.direction, amount_paise=pt.amount_paise)
    ).exclude(pk=pt.pk).select_related("entry")

    if pt.reference:
        window = dt.timedelta(days=settings.INGEST_REFERENCE_WINDOW_DAYS)
        by_ref = _distinct_entries(
            base.filter(reference=pt.reference, occurred_at__range=(pt.occurred_at - window, pt.occurred_at + window))
        )
        if len(by_ref) == 1:
            return by_ref[0], []
        if len(by_ref) > 1:
            return None, by_ref

    window = _minutes("INGEST_SAME_PAYMENT_WINDOW_MINUTES")
    candidates = []
    for other in base.filter(occurred_at__range=(pt.occurred_at - window, pt.occurred_at + window)):
        if pt.reference and other.reference and pt.reference != other.reference:
            continue  # two different references are two different payments
        # A bank sends one SMS of a given type per payment, so a second message of
        # the same type is a second payment, not a copy.
        if other.entry.messages.filter(pattern_ref=pt.pattern_ref).exists():
            continue
        candidates.append(other)
    entries = _distinct_entries(candidates)
    if len(entries) == 1:
        return entries[0], []
    return None, entries


def find_expected_side(pt):
    """A transfer already created from the other side, which names this account."""
    window = _minutes("INGEST_TRANSFER_WINDOW_MINUTES")
    side = "destination_account_id" if pt.direction == PT.Direction.CREDIT else "source_account_id"
    qs = LedgerEntry.objects.filter(
        type=LedgerEntry.Type.TRANSFER,
        amount_paise=pt.amount_paise,
        occurred_at__range=(pt.occurred_at - window, pt.occurred_at + window),
        **{side: pt.firefly_account_id},
    ).exclude(status=LedgerEntry.Status.CANCELLED)
    entries = [e for e in qs if not e.messages.filter(firefly_account_id=pt.firefly_account_id).exists()]
    return entries[0] if len(entries) == 1 else None, entries if len(entries) > 1 else []


def find_transfer_partner(pt):
    """The other half of a move between own accounts. Returns (partner_pt, ambiguous_entries)."""
    opposite = PT.Direction.CREDIT if pt.direction == PT.Direction.DEBIT else PT.Direction.DEBIT
    base = (
        _live(PT.objects.filter(direction=opposite, amount_paise=pt.amount_paise))
        .exclude(firefly_account_id="")
        .exclude(firefly_account_id=pt.firefly_account_id)
        .exclude(entry__type=LedgerEntry.Type.TRANSFER)
        .select_related("entry")
    )
    if pt.reference:
        window = dt.timedelta(days=settings.INGEST_REFERENCE_WINDOW_DAYS)
        by_ref = list(base.filter(reference=pt.reference, occurred_at__range=(pt.occurred_at - window, pt.occurred_at + window)))
        if len(by_ref) == 1:
            return by_ref[0], []
        if len(by_ref) > 1:
            return None, _distinct_entries(by_ref)

    # Without a shared reference, pair only when a profile says this is a move between own accounts.
    window = _minutes("INGEST_TRANSFER_WINDOW_MINUTES")
    near = base.filter(occurred_at__range=(pt.occurred_at - window, pt.occurred_at + window))
    if pt.kind not in FLAGGED:
        near = near.filter(kind__in=FLAGGED)
    near = [o for o in near if not (pt.reference and o.reference and pt.reference != o.reference)]
    if len(near) == 1:
        return near[0], []
    return None, _distinct_entries(near)


def _make_transfer(entry, debit_account, credit_account):
    entry.type = LedgerEntry.Type.TRANSFER
    entry.source_account_id = debit_account
    entry.destination_account_id = credit_account
    entry.awaiting_partner = False
    entry.counterparty = ""
    entry.save()


def _attach(pt, entry):
    pt.entry = entry
    pt.save(update_fields=["entry"])
    raw = pt.raw
    raw.status = RawMessage.Status.PARSED
    raw.status_reason = ""
    raw.save(update_fields=["status", "status_reason", "pattern_ref"])
    if not entry.reference and pt.reference:
        entry.reference = pt.reference
        entry.save(update_fields=["reference", "updated_at"])
    return entry


def _new_entry(pt, **fields):
    data = dict(
        amount_paise=pt.amount_paise,
        occurred_at=pt.occurred_at,
        channel=pt.channel,
        reference=pt.reference,
        counterparty=pt.counterparty or pt.vpa,
        category=pt.category,
    )
    data.update(fields)
    return LedgerEntry.objects.create(**data)


def _reconcile(pt):
    raw = pt.raw

    if pt.kind == PT.Kind.REVERSAL and pt.reference:
        original = (
            _live(PT.objects.filter(firefly_account_id=pt.firefly_account_id, reference=pt.reference,
                                    amount_paise=pt.amount_paise, direction=PT.Direction.DEBIT))
            .select_related("entry").first()
        )
        if original and original.entry.status == LedgerEntry.Status.PENDING:
            original.entry.status = LedgerEntry.Status.CANCELLED  # debit and reversal cancel out
            original.entry.save(update_fields=["status", "updated_at"])
            return _attach(pt, original.entry)

    entry, ambiguous = find_same_payment(pt)
    if ambiguous:
        return _review(raw, ReviewItem.Reason.AMBIGUOUS_MATCH, "several earlier payments look the same",
                       [e.pk for e in ambiguous])
    if entry:
        return _attach(pt, entry)

    entry, ambiguous = find_expected_side(pt)
    if ambiguous:
        return _review(raw, ReviewItem.Reason.AMBIGUOUS_MATCH, "several transfers expect this message",
                       [e.pk for e in ambiguous])
    if entry:
        return _attach(pt, entry)

    partner, ambiguous = find_transfer_partner(pt)
    if ambiguous:
        return _review(raw, ReviewItem.Reason.AMBIGUOUS_MATCH, "several possible transfer partners",
                       [e.pk for e in ambiguous])
    if partner:
        entry = partner.entry
        debit, credit = (pt, partner) if pt.direction == PT.Direction.DEBIT else (partner, pt)
        if entry.status == LedgerEntry.Status.PENDING:
            _make_transfer(entry, debit.firefly_account_id, credit.firefly_account_id)
            return _attach(pt, entry)
        _attach(pt, entry)
        return _review(None, ReviewItem.Reason.TRANSFER_ALREADY_POSTED,
                       "the other half of this transfer was already posted as a plain transaction", [entry.pk], entry)

    if pt.kind == PT.Kind.CARD_PAYMENT and pt.direction == PT.Direction.DEBIT and pt.target_last4:
        card, _reason = accounts.resolve(pt.target_last4)
        if card is not None:
            entry = _new_entry(pt, type=LedgerEntry.Type.TRANSFER, counterparty="",
                               source_account_id=pt.firefly_account_id, destination_account_id=card.id)
            return _attach(pt, entry)

    if pt.direction == PT.Direction.DEBIT:
        entry = _new_entry(pt, type=LedgerEntry.Type.WITHDRAWAL, source_account_id=pt.firefly_account_id)
    else:
        entry = _new_entry(pt, type=LedgerEntry.Type.DEPOSIT, destination_account_id=pt.firefly_account_id)
    entry.awaiting_partner = pt.kind in FLAGGED  # never post half of a transfer as spend or income
    entry.is_reversal = pt.kind == PT.Kind.REVERSAL
    entry.save(update_fields=["awaiting_partner", "is_reversal", "updated_at"])
    return _attach(pt, entry)


def process(raw_id):
    """Parse and reconcile one stored message. Safe to call twice."""
    with transaction.atomic():
        _lock()
        raw = RawMessage.objects.select_for_update().get(pk=raw_id)
        if raw.status != RawMessage.Status.RECEIVED:
            return raw.status
        result = parser.parse(raw.header, raw.body, raw.sent_at, raw.source)
        raw.pattern_ref = result.pattern_ref

        if result.status == "unknown_sender":
            _review(raw, ReviewItem.Reason.UNKNOWN_SENDER, result.reason)
            return raw.status
        if result.status == "unparsed":
            if raw.source == RawMessage.Source.EMAIL and not _MONEY_WORDS.search(raw.body):
                # Banks send many newsletters and offers; only mail that talks about money moving goes to review.
                raw.status, raw.status_reason = RawMessage.Status.IGNORED, "bank email without a transaction (notice or offer)"
                raw.save(update_fields=["status", "status_reason", "pattern_ref"])
                return raw.status
            item = _review(raw, ReviewItem.Reason.UNPARSED, result.reason)
            if settings.LLM_FALLBACK_ENABLED and parser.profiles(raw.source).get(raw.header):
                from llm.tasks import suggest_for_review  # only messages from known bank senders

                transaction.on_commit(lambda: suggest_for_review.delay(item.pk))
            return raw.status
        if result.status == "review":
            _review(raw, ReviewItem.Reason.UNPARSED, result.reason)
            return raw.status
        if result.status == "ignored":
            raw.status, raw.status_reason = RawMessage.Status.IGNORED, result.reason[:200]
            raw.save(update_fields=["status", "status_reason", "pattern_ref"])
            return raw.status

        p = result.parsed
        if not p.account_last4:
            _review(raw, ReviewItem.Reason.UNKNOWN_ACCOUNT,
                    "this SMS does not say which account or card it is for")
            return raw.status
        account, why = accounts.resolve(p.account_last4)
        if account is None:
            _review(raw, ReviewItem.Reason.UNKNOWN_ACCOUNT, why)
            return raw.status

        if p.balance_paise is not None:
            BalanceObservation.objects.create(
                firefly_account_id=account.id, balance_paise=p.balance_paise, observed_at=p.occurred_at, raw=raw
            )
        if p.type == "balance":
            raw.status, raw.status_reason = RawMessage.Status.IGNORED, "balance alert (balance recorded)"
            raw.save(update_fields=["status", "status_reason", "pattern_ref"])
            return raw.status

        kind = p.kind
        if kind == PT.Kind.PAYMENT and p.vpa and p.vpa.lower() in settings.INGEST_OWN_VPAS:
            kind = PT.Kind.OWN_TRANSFER
        pt = PT.objects.create(
            raw=raw, pattern_ref=p.pattern_ref, amount_paise=p.amount_paise, direction=p.direction, kind=kind,
            channel=p.channel, account_last4=p.account_last4, firefly_account_id=account.id,
            target_last4=p.target_last4, counterparty=p.counterparty, vpa=p.vpa, reference=p.reference,
            occurred_at=p.occurred_at, category=p.category,
        )
        _reconcile(pt)
        raw.refresh_from_db(fields=["status"])
        return raw.status


def reset_for_reparse(raw):
    """Undo a message's processing so it can be parsed again (e.g. after a profile was added)."""
    with transaction.atomic():
        parsed = getattr(raw, "parsed", None)
        if parsed is not None:
            entry = parsed.entry
            if entry is not None and entry.status not in (LedgerEntry.Status.PENDING, LedgerEntry.Status.REVIEW):
                raise ValueError("this message is part of a posted transaction")
            parsed.delete()
            if entry is not None and not entry.messages.exists():
                entry.delete()
        raw.balances.all().delete()
        raw.status, raw.status_reason, raw.pattern_ref = RawMessage.Status.RECEIVED, "", ""
        raw.save(update_fields=["status", "status_reason", "pattern_ref"])


def due_cutoff():
    return timezone.now() - dt.timedelta(seconds=settings.INGEST_SETTLE_SECONDS)
