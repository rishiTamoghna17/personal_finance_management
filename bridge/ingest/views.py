import datetime as dt
import hashlib
import hmac
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import otp, reconcile
from .models import DropTally, LedgerEntry, ParsedTransaction, RawMessage, ReviewItem
from .parser import IST, header_of
from .tasks import post_entry, process_raw

log = logging.getLogger(__name__)


class EpochMillisField(serializers.Field):
    """The forwarder sends epoch milliseconds, as a number or a quoted number."""

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, str)) or not str(data).strip().isdigit():
            raise serializers.ValidationError("expected epoch milliseconds")
        value = int(str(data).strip())
        if not 10**12 <= value < 10**13:
            raise serializers.ValidationError("expected epoch milliseconds")
        return dt.datetime.fromtimestamp(value / 1000, tz=dt.timezone.utc)


class SmsSerializer(serializers.Serializer):
    """Payload of the "Incoming SMS to URL forwarder" app. "from" is a Python keyword, hence get_fields."""

    def get_fields(self):
        return {
            "from": serializers.CharField(max_length=64),
            "text": serializers.CharField(max_length=2000, trim_whitespace=False),
            "sentStamp": EpochMillisField(),
            "receivedStamp": EpochMillisField(required=False),
        }


def _signature_ok(request):
    secret = settings.BRIDGE_SMS_HMAC_SECRET
    if not secret:
        return False
    given = request.headers.get("X-Signature", "").strip().lower()
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return bool(given) and hmac.compare_digest(given, expected)


def _content_hash(source, sender, sent_at, body):
    key = "\x1f".join([source, sender, str(int(sent_at.timestamp() * 1000)), body])
    return hashlib.sha256(key.encode()).hexdigest()


def _tally_drop(header):
    day = timezone.now().astimezone(IST).date()
    tally, _ = DropTally.objects.get_or_create(header=header[:32], day=day)
    DropTally.objects.filter(pk=tally.pk).update(count=F("count") + 1)


class IngestSmsView(APIView):
    """POST /api/v1/ingest/sms - from the Android forwarder (and later the Phase 2 app)."""

    def post(self, request):
        if not _signature_ok(request):
            return Response({"detail": "bad or missing X-Signature"}, status=401)
        serializer = SmsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "invalid payload", "fields": sorted(serializer.errors)}, status=400)
        data = serializer.validated_data
        header = header_of(data["from"])

        # Rule 3: the secret filter runs before anything is stored, logged or queued.
        if otp.contains_secret(data["text"]):
            _tally_drop(header)
            return Response({"status": "dropped"})

        content_hash = _content_hash(RawMessage.Source.SMS, data["from"], data["sentStamp"], data["text"])
        try:
            with transaction.atomic():
                raw = RawMessage.objects.create(
                    source=RawMessage.Source.SMS, sender=data["from"], header=header, body=data["text"],
                    sent_at=data["sentStamp"], received_at=data.get("receivedStamp"), content_hash=content_hash,
                )
        except IntegrityError:
            existing = RawMessage.objects.get(content_hash=content_hash)
            return Response({"status": "duplicate", "id": existing.pk})
        transaction.on_commit(lambda: process_raw.delay(raw.pk))
        log.info("stored raw message %s from %s", raw.pk, header)
        return Response({"status": "accepted", "id": raw.pk}, status=202)


def _review_json(item):
    raw = item.raw
    return {
        "id": item.pk,
        "reason": item.reason,
        "detail": item.detail,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "candidates": item.candidates,
        "entry_id": item.entry_id,
        "message": None if raw is None else {
            "id": raw.pk, "source": raw.source, "sender": raw.sender, "text": raw.body,
            "sent_at": raw.sent_at.isoformat(),
        },
    }


class ReviewListView(APIView):
    """GET /api/v1/review?status=open|resolved|ignored|all"""

    def get(self, request):
        status = request.query_params.get("status", "open")
        qs = ReviewItem.objects.select_related("raw").order_by("-created_at")
        if status != "all":
            qs = qs.filter(status=status)
        return Response({"items": [_review_json(i) for i in qs[:200]]})


class ReviewActionView(APIView):
    """POST /api/v1/review/<id>/<action>  actions: ignore, reparse, resolve"""

    def post(self, request, pk, action):
        item = get_object_or_404(ReviewItem, pk=pk)
        if item.status != ReviewItem.Status.OPEN:
            return Response({"detail": "already closed"}, status=409)
        handler = {"ignore": self._ignore, "reparse": self._reparse, "resolve": self._resolve}.get(action)
        if handler is None:
            return Response({"detail": "unknown action"}, status=404)
        return handler(request, item)

    def _close(self, item, status, resolution):
        item.status, item.resolution, item.resolved_at = status, resolution[:200], timezone.now()
        item.save(update_fields=["status", "resolution", "resolved_at"])

    def _ignore(self, request, item):
        with transaction.atomic():
            if item.raw and item.raw.status == RawMessage.Status.REVIEW:
                item.raw.status, item.raw.status_reason = RawMessage.Status.IGNORED, "ignored by owner"
                item.raw.save(update_fields=["status", "status_reason"])
            self._close(item, ReviewItem.Status.IGNORED, "ignored by owner")
        return Response(_review_json(item))

    def _reparse(self, request, item):
        if item.raw is None:
            return Response({"detail": "this item has no message to re-parse"}, status=400)
        from .parser import clear_cache

        clear_cache()  # pick up profiles added since
        try:
            reconcile.reset_for_reparse(item.raw)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        self._close(item, ReviewItem.Status.RESOLVED, "re-parsed")
        status = reconcile.process(item.raw.pk)
        return Response({"item": _review_json(item), "message_status": status})

    def _resolve(self, request, item):
        """Body for ambiguous_match: {"entry_id": N} to merge, or {"entry_id": null} for a new payment.
        Body for unpaired_transfer or post_failed: {"post": true} to post the entry as it is."""
        if item.reason == ReviewItem.Reason.AMBIGUOUS_MATCH:
            return self._resolve_ambiguous(request, item)
        if item.reason in (ReviewItem.Reason.UNPAIRED_TRANSFER, ReviewItem.Reason.POST_FAILED) and request.data.get("post") is True:
            entry = item.entry
            LedgerEntry.objects.filter(pk=entry.pk).update(status=LedgerEntry.Status.PENDING, awaiting_partner=False)
            self._close(item, ReviewItem.Status.RESOLVED, "posted on owner's instruction")
            transaction.on_commit(lambda: post_entry.delay(entry.pk))
            return Response(_review_json(item))
        return Response({"detail": "nothing to resolve this way; use ignore or reparse"}, status=400)

    def _resolve_ambiguous(self, request, item):
        if "entry_id" not in request.data:
            return Response({"detail": "entry_id is required (a candidate id, or null)"}, status=400)
        pt = ParsedTransaction.objects.filter(raw=item.raw).first()
        if pt is None:
            return Response({"detail": "message has no parsed transaction"}, status=400)
        entry_id = request.data["entry_id"]
        with transaction.atomic():
            if entry_id is None:
                if pt.direction == ParsedTransaction.Direction.DEBIT:
                    entry = reconcile._new_entry(pt, type=LedgerEntry.Type.WITHDRAWAL, source_account_id=pt.firefly_account_id)
                else:
                    entry = reconcile._new_entry(pt, type=LedgerEntry.Type.DEPOSIT, destination_account_id=pt.firefly_account_id)
                resolution = "new payment"
            else:
                if entry_id not in item.candidates:
                    return Response({"detail": "entry_id is not one of the candidates"}, status=400)
                entry = LedgerEntry.objects.get(pk=entry_id)
                resolution = f"merged into entry {entry_id}"
            reconcile._attach(pt, entry)
            self._close(item, ReviewItem.Status.RESOLVED, resolution)
        return Response(_review_json(item))
