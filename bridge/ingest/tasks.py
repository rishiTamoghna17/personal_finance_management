"""Celery tasks. Arguments are row ids only: never message text, amounts or secrets."""
import datetime as dt
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.money import to_decimal_string
from firefly.client import FireflyClient, FireflyError

from . import reconcile
from .models import LedgerEntry, RawMessage, ReviewItem
from .parser import IST

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def process_raw(self, raw_id):
    try:
        status = reconcile.process(raw_id)
    except FireflyError:
        # Firefly is needed to look up accounts; the message stays "received" and is retried.
        raise self.retry(countdown=min(600, 30 * 2**self.request.retries))
    log.info("raw message %s -> %s", raw_id, status)
    return status


def describe(entry):
    if entry.type == LedgerEntry.Type.TRANSFER:
        return "Transfer between own accounts"
    channel = (entry.channel or "").upper()
    who = entry.counterparty or ("unknown payee" if entry.type == LedgerEntry.Type.WITHDRAWAL else "unknown payer")
    prefix = "Reversal: " if entry.is_reversal else ""
    return f"{prefix}{channel + ' ' if channel else ''}{who}"[:255]


def build_payload(entry):
    raw_ids = sorted(entry.messages.values_list("raw_id", flat=True))
    sources = sorted(set(entry.messages.values_list("raw__source", flat=True)))
    tx = {
        "type": entry.type,
        "date": entry.occurred_at.astimezone(IST).isoformat(),
        "amount": to_decimal_string(entry.amount_paise),
        "currency_code": "INR",
        "description": describe(entry),
        "external_id": str(entry.external_id),
        "notes": "bridge raw message ids: " + ", ".join(str(i) for i in raw_ids),
        "tags": ["bridge"] + [f"source-{s}" for s in sources] + ([f"channel-{entry.channel}"] if entry.channel else []),
    }
    if entry.reference:
        tx["internal_reference"] = entry.reference
    if entry.type == LedgerEntry.Type.WITHDRAWAL:
        tx["source_id"] = entry.source_account_id
        tx["destination_name"] = entry.counterparty or "Unknown payee"
    elif entry.type == LedgerEntry.Type.DEPOSIT:
        tx["source_name"] = entry.counterparty or "Unknown payer"
        tx["destination_id"] = entry.destination_account_id
    else:
        tx["source_id"] = entry.source_account_id
        tx["destination_id"] = entry.destination_account_id
    return {"error_if_duplicate_hash": True, "apply_rules": True, "fire_webhooks": True, "transactions": [tx]}


@shared_task(bind=True, max_retries=5)
def post_entry(self, entry_id):
    with transaction.atomic():
        entry = LedgerEntry.objects.select_for_update().get(pk=entry_id)
        if entry.status != LedgerEntry.Status.PENDING or entry.awaiting_partner:
            return entry.status
        entry.status = LedgerEntry.Status.POSTING
        entry.save(update_fields=["status", "updated_at"])
    payload = build_payload(entry)
    try:
        group = FireflyClient.from_settings().create_transaction(payload)
    except FireflyError as exc:
        client_error = exc.status_code is not None and 400 <= exc.status_code < 500
        if not client_error and self.request.retries < self.max_retries:
            LedgerEntry.objects.filter(pk=entry_id).update(status=LedgerEntry.Status.PENDING)
            raise self.retry(countdown=min(900, 60 * 2**self.request.retries))
        LedgerEntry.objects.filter(pk=entry_id).update(status=LedgerEntry.Status.REVIEW)
        ReviewItem.objects.create(entry=entry, reason=ReviewItem.Reason.POST_FAILED, detail=str(exc)[:300])
        log.warning("entry %s could not be posted (status %s)", entry_id, exc.status_code)
        return "review"
    LedgerEntry.objects.filter(pk=entry_id).update(
        status=LedgerEntry.Status.POSTED, firefly_group_id=str(group.get("id", "")), posted_at=timezone.now()
    )
    log.info("entry %s posted to Firefly", entry_id)
    return "posted"


@shared_task
def sweep():
    """Every minute: post entries past the settle window, flag unpaired transfers, retry stuck messages."""
    posted = flagged = 0
    for entry in LedgerEntry.objects.filter(status=LedgerEntry.Status.PENDING, created_at__lte=reconcile.due_cutoff()):
        if entry.awaiting_partner:
            with transaction.atomic():
                updated = LedgerEntry.objects.filter(pk=entry.pk, status=LedgerEntry.Status.PENDING).update(
                    status=LedgerEntry.Status.REVIEW
                )
                if updated:
                    first = entry.messages.select_related("raw").first()
                    ReviewItem.objects.create(
                        entry=entry, raw=first.raw if first else None, reason=ReviewItem.Reason.UNPAIRED_TRANSFER,
                        detail="only one side of a transfer or card payment arrived",
                    )
                    flagged += 1
        else:
            post_entry.delay(entry.pk)
            posted += 1
    stuck_before = timezone.now() - dt.timedelta(minutes=2)
    for raw_id in RawMessage.objects.filter(status=RawMessage.Status.RECEIVED, created_at__lte=stuck_before).values_list(
        "pk", flat=True
    ):
        process_raw.delay(raw_id)
    return {"queued_posts": posted, "unpaired": flagged}
