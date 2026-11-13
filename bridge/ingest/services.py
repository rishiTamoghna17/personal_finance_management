"""Storing an incoming message. Callers MUST run the secret filter first (rule 3)."""
import hashlib

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import DropTally, RawMessage
from .parser import IST
from .tasks import process_raw


def content_hash(*parts):
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode()).hexdigest()


def tally_drop(header):
    day = timezone.now().astimezone(IST).date()
    tally, _ = DropTally.objects.get_or_create(header=header[:32], day=day)
    DropTally.objects.filter(pk=tally.pk).update(count=F("count") + 1)


def store(source, sender, header, body, sent_at, digest, received_at=None):
    """Store a message once and queue it for processing. Returns (raw, created)."""
    try:
        with transaction.atomic():
            raw = RawMessage.objects.create(
                source=source, sender=sender[:255], header=header[:128], body=body, sent_at=sent_at,
                received_at=received_at, content_hash=digest,
            )
    except IntegrityError:
        return RawMessage.objects.get(content_hash=digest), False
    transaction.on_commit(lambda: process_raw.delay(raw.pk))
    return raw, True
