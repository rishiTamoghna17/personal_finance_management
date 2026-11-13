"""Apply a parsed statement: confirm the closing balance and make sure every line on or after the ledger
start is in the ledger exactly once (rule 6). Matching is by day, not minute: statements carry no times."""
import datetime as dt

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.money import to_decimal_string
from ingest import accounts, reconcile
from ingest.models import BalanceObservation, LedgerEntry, ParsedTransaction, RawMessage, ReviewItem
from ingest.parser import IST
from ingest.services import content_hash

PT = ParsedTransaction
MATCH_DAYS = 2


def _at(day, hour=12):
    return dt.datetime.combine(day, dt.time(hour, 0), tzinfo=IST)


def _raw(att, index, text, when):
    raw, _ = RawMessage.objects.get_or_create(
        content_hash=content_hash("pdf", att.pk, index),
        defaults={"source": RawMessage.Source.PDF, "sender": att.key, "header": att.key.upper(), "body": text[:2000],
                  "sent_at": when, "status": RawMessage.Status.RECEIVED, "pattern_ref": f"statement/{att.key}"},
    )
    return raw


def _same_payment(account_id, line):
    lo, hi = _at(line.date - dt.timedelta(days=MATCH_DAYS), 0), _at(line.date + dt.timedelta(days=MATCH_DAYS), 23)
    candidates = (
        PT.objects.filter(firefly_account_id=account_id, direction=line.direction, amount_paise=line.amount_paise,
                          occurred_at__range=(lo, hi), entry__isnull=False)
        .exclude(entry__status=LedgerEntry.Status.CANCELLED)
        .exclude(entry__messages__raw__source=RawMessage.Source.PDF)  # one statement line per payment
        .select_related("entry")
    )
    if line.reference:
        by_ref = [c for c in candidates if c.reference == line.reference]
        if by_ref:
            candidates = by_ref
    entries = {c.entry_id: c.entry for c in candidates}
    return list(entries.values())


def apply_statement(att, statement):
    account, why = accounts.resolve(statement.account_digits)
    summary = f"{statement.period_start}..{statement.period_end}, {len(statement.lines)} lines"
    with transaction.atomic():
        head = _raw(att, "summary", f"statement {att.key} ..{statement.account_digits} {summary}", _at(statement.period_end, 23))
        if account is None:
            head.status, head.status_reason = RawMessage.Status.REVIEW, ReviewItem.Reason.UNKNOWN_ACCOUNT
            head.save(update_fields=["status", "status_reason"])
            ReviewItem.objects.get_or_create(raw=head, reason=ReviewItem.Reason.UNKNOWN_ACCOUNT, defaults={"detail": why})
            return f"{summary}; account not found ({why})"
        head.status, head.status_reason = RawMessage.Status.IGNORED, "statement summary"
        head.save(update_fields=["status", "status_reason"])
        if statement.closing_paise is not None:
            # A card statement's closing figure is money owed, so the account balance is its negative.
            balance = statement.closing_paise if statement.kind == "bank" else -statement.closing_paise
            BalanceObservation.objects.get_or_create(
                firefly_account_id=account.id, observed_at=_at(statement.period_end, 23), raw=head,
                defaults={"balance_paise": balance},
            )
        from wealth.apply import record_card_due

        record_card_due(att, statement, account.id)
        start = dt.date.fromisoformat(settings.INGEST_LEDGER_START)
        counts = {"matched": 0, "added": 0, "review": 0, "before_start": 0}
        for index, line in enumerate(statement.lines):
            if line.date < start:
                counts["before_start"] += 1
                continue
            raw = _raw(att, index, f"{line.date} {line.description} {to_decimal_string(line.amount_paise)} {line.direction}", _at(line.date))
            if raw.status != RawMessage.Status.RECEIVED:
                continue  # already applied
            pt = PT.objects.create(
                raw=raw, pattern_ref=f"statement/{att.key}", amount_paise=line.amount_paise, direction=line.direction,
                channel="other", account_last4=statement.account_digits, firefly_account_id=account.id,
                counterparty=line.description[:200], reference=line.reference, occurred_at=_at(line.date),
            )
            found = _same_payment(account.id, line)
            if len(found) == 1:
                reconcile._attach(pt, found[0])
                counts["matched"] += 1
            elif len(found) > 1:
                reconcile._review(raw, ReviewItem.Reason.AMBIGUOUS_MATCH, "statement line matches several payments",
                                  [e.pk for e in found])
                counts["review"] += 1
            else:
                reconcile._reconcile(pt)  # not seen by SMS or email: a new transaction (or the other half of a transfer)
                counts["added"] += 1
    return f"{summary}; " + ", ".join(f"{k} {v}" for k, v in counts.items() if v)
