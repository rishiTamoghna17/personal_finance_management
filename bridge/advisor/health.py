"""Is the system itself working? Alerts when a background job, the phone, or the nightly backup has gone quiet (M7).
Only times and job names are read."""
import datetime as dt
import json
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ingest.models import Heartbeat, RawMessage
from mail.models import GmailAccount

LIMITS = {"sweep": dt.timedelta(minutes=10), "gmail": dt.timedelta(minutes=60), "statements": dt.timedelta(hours=3)}
NAMES = {"sweep": "Posting to the ledger", "gmail": "Bank email reading", "statements": "Statement reading"}
SMS_QUIET = dt.timedelta(hours=48)
BACKUP_LATE = dt.timedelta(hours=36)


def _alert(kind, severity, message, **data):
    return {"type": kind, "severity": severity, "message": message, "data": data}


def backup_status():
    path = Path(settings.BACKUP_STATUS_FILE)
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def checks(now=None):
    now = now or timezone.now()
    out = []
    beats = dict(Heartbeat.objects.values_list("name", "at"))
    for name, limit in LIMITS.items():
        if name == "gmail" and not GmailAccount.objects.filter(enabled=True).exists():
            continue
        last = beats.get(name)
        if last is None or now - last > limit:
            when = f"last ran {timezone.localtime(last):%d %b %H:%M}" if last else "has not run yet"
            out.append(_alert("job_stopped", "high", f"{NAMES[name]} {when}; the background worker may be down.",
                              job=name))
    last_sms = RawMessage.objects.filter(source=RawMessage.Source.SMS).order_by("-created_at").values_list(
        "created_at", flat=True).first()
    if last_sms and now - last_sms > SMS_QUIET:
        out.append(_alert("sms_quiet", "medium", f"No SMS from the phone since {timezone.localtime(last_sms):%d %b %H:%M}; "
                                                 f"check the forwarder app and its connection.", last=last_sms.isoformat()))
    out += reconnect_reminders(now)
    status = backup_status()
    if status is None:
        out.append(_alert("backup_missing", "high", "No backup has been made yet."))
    else:
        at = dt.datetime.fromisoformat(status["at"].replace("Z", "+00:00"))
        if not status.get("ok"):
            out.append(_alert("backup_failed", "high", f"The last backup failed ({timezone.localtime(at):%d %b %H:%M}).",
                              at=status["at"]))
        elif now - at > BACKUP_LATE:
            out.append(_alert("backup_late", "high", f"The last backup is from {timezone.localtime(at):%d %b %H:%M}.",
                              at=status["at"]))
    return out


GOOGLE_TOKEN_DAYS = 7
REMIND_FROM_DAYS = 3


def _reconnect_alert(label, connected_at, command, now):
    age = now - connected_at
    left = dt.timedelta(days=GOOGLE_TOKEN_DAYS) - age
    if age < dt.timedelta(days=REMIND_FROM_DAYS):
        return None
    if left <= dt.timedelta(0):
        return _alert("google_reconnect", "high", f"{label} sign-in has expired; reconnect it: {command}",
                      connection=label, connected_at=connected_at.isoformat())
    days = max(1, left.days + (1 if left.seconds else 0))
    severity = "high" if left <= dt.timedelta(days=1) else "medium"
    return _alert("google_reconnect", severity,
                  f"{label} sign-in expires in about {days} day{'s' if days != 1 else ''}; reconnect it now: {command}",
                  connection=label, connected_at=connected_at.isoformat(), days_left=days)


def reconnect_reminders(now=None):
    """Google apps in "Testing" lose their tokens 7 days after sign-in. Remind from day 3, so a reconnect every 3-4
    days keeps everything running (owner's choice instead of publishing the apps). When a one-time link exists
    (tap-to-reconnect over Tailscale), the alert carries it."""
    if not settings.GOOGLE_OAUTH_TESTING:
        return []
    from mail import reconnect

    now = now or timezone.now()
    out = []
    labels = {"drive": "Google Drive (backups)"}
    for connection, connected_at in reconnect.connections():
        label = labels.get(connection, f"Gmail ({connection.split(':', 1)[-1]})")
        link = reconnect.live_link(connection, now) if reconnect.enabled() else None
        how = "tap the link" if link else "sh scripts/google-reconnect.sh"
        alert = _reconnect_alert(label, connected_at, how, now)
        if alert:
            if link:
                alert["data"]["link"] = reconnect.link_url(link)
            out.append(alert)
    return out
