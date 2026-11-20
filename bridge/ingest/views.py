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

from . import otp, reconcile, services
from .models import DropTally, LedgerEntry, MessageFeedback, ParsedTransaction, RawMessage, ReviewItem
from .parser import IST, header_of, header_of_email
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
            services.tally_drop(header)
            return Response({"status": "dropped"})

        digest = _content_hash(RawMessage.Source.SMS, data["from"], data["sentStamp"], data["text"])
        raw, created = services.store(RawMessage.Source.SMS, data["from"], header, data["text"], data["sentStamp"],
                                      digest, data.get("receivedStamp"))
        if not created:
            return Response({"status": "duplicate", "id": raw.pk})
        log.info("stored raw message %s from %s", raw.pk, header)
        return Response({"status": "accepted", "id": raw.pk}, status=202)


class EmailSerializer(serializers.Serializer):
    def get_fields(self):
        return {
            "from": serializers.CharField(max_length=255),
            "subject": serializers.CharField(max_length=500, allow_blank=True, trim_whitespace=False),
            "text": serializers.CharField(max_length=20000, trim_whitespace=False),
            "sentStamp": EpochMillisField(),
        }


class IngestEmailView(APIView):
    """POST /api/v1/ingest/email - one bank email (the Gmail poller uses the same path internally)."""

    def post(self, request):
        if not _signature_ok(request):
            return Response({"detail": "bad or missing X-Signature"}, status=401)
        serializer = EmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "invalid payload", "fields": sorted(serializer.errors)}, status=400)
        data = serializer.validated_data
        header = header_of_email(data["from"])
        if otp.contains_secret_email(data["subject"], data["text"]):  # rule 3, before anything is stored
            services.tally_drop(header)
            return Response({"status": "dropped"})
        body = f"{data['subject']}\n{data['text']}"
        digest = _content_hash(RawMessage.Source.EMAIL, data["from"], data["sentStamp"], body)
        raw, created = services.store(RawMessage.Source.EMAIL, data["from"], header, body, data["sentStamp"], digest)
        if not created:
            return Response({"status": "duplicate", "id": raw.pk})
        log.info("stored raw message %s from %s", raw.pk, header)
        return Response({"status": "accepted", "id": raw.pk}, status=202)


def _candidate_details(ids):
    """What each candidate payment is, so a person can pick one without looking it up."""
    out = []
    for entry in LedgerEntry.objects.filter(pk__in=ids or []):
        out.append({"id": entry.pk, "type": entry.type, "amount_paise": entry.amount_paise,
                    "occurred_at": entry.occurred_at.isoformat(), "counterparty": entry.counterparty,
                    "status": entry.status})
    return out


def _review_json(item):
    raw = item.raw
    return {
        "id": item.pk,
        "reason": item.reason,
        "detail": item.detail,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "candidates": item.candidates,
        "candidate_details": _candidate_details(item.candidates),
        "suggestion": item.suggestion,
        "feedback": getattr(getattr(raw, "feedback", None), "label", None) if raw else None,
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
        handler = {"ignore": self._ignore, "reparse": self._reparse, "resolve": self._resolve, "accept": self._accept,
                   "category": self._category}.get(action)
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

    def _accept(self, request, item):
        """Accept a checked AI reading, optionally with owner corrections, through normal reconciliation."""
        import datetime as dt

        from . import accounts
        from llm import fallback

        if item.reason != ReviewItem.Reason.UNPARSED or item.raw is None:
            return Response({"detail": "only an open unparsed message can accept corrected transaction details"}, status=400)
        s = item.suggestion or {}
        correction = request.data.get("correction")
        if correction is not None:
            fields = {"amount", "direction", "account_last4", "date", "counterparty", "reference"}
            if not isinstance(correction, dict) or set(correction) != fields:
                return Response({"detail": "correction must include amount, direction, account_last4, date, counterparty and reference"}, status=400)
            if any(not isinstance(correction[key], str) for key in fields):
                return Response({"detail": "all corrected fields must be text"}, status=400)
            if len(correction["counterparty"]) > 200 or len(correction["reference"]) > 64:
                return Response({"detail": "counterparty or reference is too long"}, status=400)
            answer = {
                "is_transaction": True,
                "amount": correction["amount"],
                "direction": correction["direction"],
                "account_digits": correction["account_last4"],
                "date": correction["date"] or None,
                "counterparty": correction["counterparty"],
                "reference": correction["reference"],
            }
            try:
                s = fallback.check(answer, item.raw.body, item.raw.sent_at)
            except fallback.Rejected as exc:
                return Response({"detail": f"Correction rejected: {exc}"}, status=400)
            if correction["reference"] and not s["reference"]:
                return Response({"detail": "reference was not found in the original message"}, status=400)
        elif s.get("status") != "ok":
            return Response({"detail": "no checked AI suggestion; enter corrected transaction details"}, status=400)
        account, why = accounts.resolve(s["account_last4"])
        if account is None:
            return Response({"detail": why}, status=409)
        with transaction.atomic():
            raw = item.raw
            raw.pattern_ref = "ai-suggestion"
            raw.save(update_fields=["pattern_ref"])
            pt = ParsedTransaction.objects.create(
                raw=raw, pattern_ref="ai-suggestion", amount_paise=s["amount_paise"], direction=s["direction"],
                channel="other", account_last4=s["account_last4"], firefly_account_id=account.id,
                counterparty=s.get("counterparty", ""), reference=s.get("reference", ""),
                occurred_at=dt.datetime.fromisoformat(s["occurred_at"]),
            )
            reconcile._reconcile(pt)
            if not MessageFeedback.objects.filter(raw=raw).exists():
                MessageFeedback.objects.create(raw=raw, label=MessageFeedback.Label.TRANSACTION)
            self._close(item, ReviewItem.Status.RESOLVED, "accepted AI suggestion")
        return Response(_review_json(item))

    def _category(self, request, item):
        """Body: {"category": "<one of the Firefly categories>", "always": true|false}."""
        from . import categorise

        name, always = request.data.get("category"), request.data.get("always", False)
        if not isinstance(name, str) or not isinstance(always, bool):
            return Response({"detail": "category (text) is required; always must be true or false"}, status=400)
        try:
            result = categorise.choose(item, name, always)
        except categorise.CategoryError as exc:
            return Response({"detail": str(exc)}, status=400)
        item.refresh_from_db()
        return Response({"item": _review_json(item), **result})

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


class ReviewFeedbackView(APIView):
    """POST /api/v1/review/<id>/feedback with {"label": <MessageFeedback.Label>}.

    Feedback labels never parse a transaction or authorize posting to Firefly.
    """

    def post(self, request, pk):
        item = get_object_or_404(ReviewItem.objects.select_related("raw"), pk=pk)
        raw = item.raw
        if raw is None or item.reason not in (ReviewItem.Reason.UNKNOWN_SENDER, ReviewItem.Reason.UNPARSED):
            return Response({"detail": "feedback is only available for unclassified messages"}, status=400)
        prior = MessageFeedback.objects.filter(raw=raw).first()
        if item.status != ReviewItem.Status.OPEN and prior is None:
            return Response({"detail": "review item is already closed"}, status=409)
        label = request.data.get("label")
        allowed = {value for value, _ in MessageFeedback.Label.choices}
        if not isinstance(label, str) or label not in allowed:
            return Response({"detail": "label must be one of the documented message types"}, status=400)

        with transaction.atomic():
            MessageFeedback.objects.update_or_create(raw=raw, defaults={"label": label})
            # A correction to a prior owner label can reopen review, but never reprocesses
            # or posts the message automatically.
            if label in (MessageFeedback.Label.TRANSACTION, MessageFeedback.Label.CARD_PAYMENT,
                         MessageFeedback.Label.REFUND) and item.status != ReviewItem.Status.OPEN:
                raw.status, raw.status_reason = RawMessage.Status.REVIEW, "owner corrected message classification"
                raw.save(update_fields=["status", "status_reason"])
                item.status, item.resolution, item.resolved_at = ReviewItem.Status.OPEN, "", None
                item.save(update_fields=["status", "resolution", "resolved_at"])
            if label == MessageFeedback.Label.PROMOTION:
                raw.status, raw.status_reason = RawMessage.Status.IGNORED, "classified as promotion by owner"
                raw.save(update_fields=["status", "status_reason"])
                item.status, item.resolution, item.resolved_at = ReviewItem.Status.IGNORED, "classified as promotion by owner", timezone.now()
                item.save(update_fields=["status", "resolution", "resolved_at"])
            elif label in (MessageFeedback.Label.FAILED, MessageFeedback.Label.REMINDER,
                           MessageFeedback.Label.OTHER):
                raw.status, raw.status_reason = RawMessage.Status.IGNORED, f"classified as {label} by owner"
                raw.save(update_fields=["status", "status_reason"])
                item.status, item.resolution, item.resolved_at = ReviewItem.Status.IGNORED, f"classified as {label} by owner", timezone.now()
                item.save(update_fields=["status", "resolution", "resolved_at"])
        item.refresh_from_db()
        return Response(_review_json(item))

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
