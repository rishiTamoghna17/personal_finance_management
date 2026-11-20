"""FCM HTTP v1 sender. Notifications contain only generic text and opaque event ids."""
import hashlib
import hmac
import json
import logging
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

log = logging.getLogger(__name__)

GENERIC = {
    "category_needed": ("My Finance", "A payment needs a category. Open the app to review."),
    "review_waiting": ("My Finance", "An item needs your review. Open the app to see details."),
    "reconnect_google": ("My Finance", "A connected service needs attention. Open the app to reconnect."),
    "due": ("My Finance", "A finance reminder is ready. Open the app to review."),
    "alert": ("My Finance", "A finance update is ready. Open the app to review."),
    "weekly_digest": ("My Finance", "Your weekly finance summary is ready. Open the app to view it."),
}


def _client():
    """Return an AuthorizedSession, or None until the owner installs the server credential."""
    credential_file = Path(settings.FCM_SERVICE_ACCOUNT_FILE)
    if not credential_file.is_file() or not settings.FCM_PROJECT_ID:
        return None
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        credential_file, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    return AuthorizedSession(creds)


def _fingerprint(kind, key):
    canonical = json.dumps([kind, key], ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    secret = (settings.BRIDGE_ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    return hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def send_event(device, kind, key):
    from .models import PushDelivery

    event_hash = _fingerprint(kind, key)
    if PushDelivery.objects.filter(device=device, event_hash=event_hash).exists():
        return False
    session = _client()
    if session is None:
        return False
    title, body = GENERIC[kind]
    payload = {
        "message": {
            "token": device.token,
            "notification": {"title": title, "body": body},
            "data": {"kind": kind, "route": "review" if kind in ("category_needed", "review_waiting") else "home"},
            "android": {"priority": "NORMAL", "notification": {"channel_id": "finance_updates", "visibility": "PRIVATE"}},
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
    response = session.post(url, json=payload, timeout=15)
    if response.status_code in (404, 410):
        try:
            error_codes = {detail.get("errorCode") for detail in response.json().get("error", {}).get("details", [])}
        except (ValueError, AttributeError):
            error_codes = set()
        if "UNREGISTERED" in error_codes:
            device.active = False
            device.save(update_fields=["active", "updated_at"])
        return False
    if response.status_code >= 300:
        log.warning("FCM delivery failed with HTTP %s", response.status_code)
        return False
    try:
        PushDelivery.objects.create(device=device, event_hash=event_hash)
    except IntegrityError:
        return False
    return True


def dispatch_alerts():
    from . import alerts
    from .models import PushDevice

    if not settings.FCM_PROJECT_ID or not Path(settings.FCM_SERVICE_ACCOUNT_FILE).is_file():
        return {"enabled": False, "sent": 0}
    sent = 0
    devices = PushDevice.objects.filter(active=True)
    for alert in alerts.build():
        alert_type = alert.get("type", "")
        data = alert.get("data") or {}
        if alert_type == "category_needed":
            kind, key = "category_needed", data.get("review_id")
        elif "reconnect" in alert_type:
            kind, key = "reconnect_google", [alert_type, data.get("connected_at")]
        elif alert_type in ("due_soon", "card_due_unpaid"):
            kind, key = "due", [alert_type, data]
        elif alert_type == "review_waiting":
            kind, key = "review_waiting", data.get("count", 0)
        else:
            kind, key = "alert", [alert_type, data]
        if key is None:
            continue
        for device in devices.iterator():
            sent += int(send_event(device, kind, key))
    return {"enabled": True, "sent": sent}


def dispatch_weekly_digest():
    from .models import PushDevice

    if not settings.FCM_PROJECT_ID or not Path(settings.FCM_SERVICE_ACCOUNT_FILE).is_file():
        return {"enabled": False, "sent": 0}
    week = timezone.localdate().isocalendar()
    key = f"{week.year}-W{week.week:02d}"
    sent = sum(send_event(device, "weekly_digest", key) for device in PushDevice.objects.filter(active=True))
    return {"enabled": True, "sent": sent}
