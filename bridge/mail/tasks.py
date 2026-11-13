"""Gmail polling. Read-only; only mail from senders that have an email profile is fetched."""
import datetime as dt
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from ingest import parser, services
from ingest.models import RawMessage
from ingest.otp import contains_secret_email

from . import gmail
from .models import GmailAccount, StatementAttachment
from .text import message_parts

log = logging.getLogger(__name__)


def bank_query(after_seconds):
    domains = sorted({h.lower() for h in parser.profiles("email")})
    return f"after:{after_seconds} from:({' OR '.join(domains)})"


def statement_key(header):
    """'HDFCBANK.BANK.IN' -> 'hdfc' (the email profile id without '-email'); used to pick statement passwords."""
    profile = parser.profiles("email").get(header)
    return profile.id.removesuffix("-email") if profile else ""


def start_ms(account):
    ledger_start = dt.datetime.fromisoformat(settings.INGEST_LEDGER_START).replace(tzinfo=parser.IST)
    return max(account.last_seen_ms, int(ledger_start.timestamp() * 1000))


def ingest_message(account, message):
    """Exact bank sender only, secret filter first (in memory), then store once.
    Returns 'other_sender', 'dropped', 'stored' or 'duplicate'."""
    sender, subject, text, pdfs = message_parts(message)
    header = parser.header_of_email(sender)
    if header not in parser.profiles("email"):
        # Gmail's from: search also matches sub-domains (mailers., offers., customer.), which only send offers.
        return "other_sender"
    if contains_secret_email(subject, text):
        services.tally_drop(header)
        return "dropped"
    sent_at = dt.datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=dt.timezone.utc)
    digest = services.content_hash("email", account.tag, message["id"])
    with transaction.atomic():
        raw, created = services.store(RawMessage.Source.EMAIL, sender, header, f"{subject}\n{text}", sent_at, digest)
        if created:
            for pdf in pdfs:
                StatementAttachment.objects.get_or_create(
                    gmail_message_id=message["id"], filename=pdf["filename"],
                    defaults={"raw": raw, "account": account, "attachment_id": pdf["attachment_id"], "size": pdf["size"],
                              "key": statement_key(header), "subject": subject[:300], "sent_at": sent_at},
                )
    return "stored" if created else "duplicate"


@shared_task
def poll_account(account_id):
    account = GmailAccount.objects.get(pk=account_id)
    service = gmail.service_for(account)
    since = start_ms(account)
    ids = gmail.list_ids(service, bank_query(since // 1000))
    counts = {"stored": 0, "dropped": 0, "duplicate": 0, "other_sender": 0}
    newest = account.last_seen_ms
    for message_id in reversed(ids):  # oldest first
        message = gmail.get_message(service, message_id)
        counts[ingest_message(account, message)] += 1
        newest = max(newest, int(message["internalDate"]))
    if newest != account.last_seen_ms:
        GmailAccount.objects.filter(pk=account.pk).update(last_seen_ms=newest)
    log.info("gmail %s: %s", account.tag, counts)
    return counts


@shared_task
def poll_all():
    for account_id in GmailAccount.objects.filter(enabled=True).values_list("pk", flat=True):
        poll_account.delay(account_id)
