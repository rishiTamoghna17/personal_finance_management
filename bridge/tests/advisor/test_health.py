"""M7: alerts when background jobs, the phone or the nightly backup go quiet."""
import datetime as dt
import json

import pytest
from django.utils import timezone

from advisor import health
from ingest.models import Heartbeat, RawMessage

pytestmark = pytest.mark.django_db
NOW = dt.datetime(2026, 11, 14, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def backup_file(tmp_path, settings):
    path = tmp_path / "last.json"
    settings.BACKUP_STATUS_FILE = str(path)
    return path


def types(now=NOW):
    return sorted(a["type"] for a in health.checks(now))


def fresh_jobs():
    for name in ("sweep", "statements"):
        Heartbeat.objects.create(name=name, at=NOW - dt.timedelta(minutes=1))


def test_all_quiet_and_healthy(backup_file):
    fresh_jobs()
    backup_file.write_text(json.dumps({"ok": True, "at": "2026-11-14T08:00:00Z", "detail": "snapshot abc"}))
    assert types() == []


def test_stopped_job_and_missing_backup(backup_file):
    Heartbeat.objects.create(name="sweep", at=NOW - dt.timedelta(hours=1))
    assert types() == ["backup_missing", "job_stopped", "job_stopped"]  # sweep late, statements never ran


def test_failed_and_late_backups(backup_file):
    fresh_jobs()
    backup_file.write_text(json.dumps({"ok": False, "at": "2026-11-14T08:00:00Z", "detail": "x"}))
    assert types() == ["backup_failed"]
    backup_file.write_text(json.dumps({"ok": True, "at": "2026-11-12T08:00:00Z", "detail": "x"}))
    assert types() == ["backup_late"]


def test_phone_quiet_for_two_days(backup_file):
    fresh_jobs()
    backup_file.write_text(json.dumps({"ok": True, "at": "2026-11-14T08:00:00Z", "detail": "x"}))
    raw = RawMessage.objects.create(source="sms", sender="S", header="S", content_hash="q", body="b", sent_at=NOW)
    RawMessage.objects.filter(pk=raw.pk).update(created_at=NOW - dt.timedelta(days=3))
    assert types() == ["sms_quiet"]


def test_heartbeat_written_by_sweep(firefly):
    from ingest.tasks import sweep

    sweep()
    assert timezone.now() - Heartbeat.objects.get(name="sweep").at < dt.timedelta(minutes=1)


def test_google_reconnect_reminders_from_day_three(backup_file, settings):
    from mail.models import GmailAccount

    settings.GOOGLE_OAUTH_TESTING = True
    settings.GDRIVE_CONNECTED_AT = "2026-11-13T12:00:00Z"  # 1 day before NOW
    GmailAccount.objects.create(tag="acct1", token_encrypted="x", connected_at=NOW - dt.timedelta(days=2))
    assert health.reconnect_reminders(NOW) == []
    later = NOW + dt.timedelta(days=2)  # Gmail day 4, Drive day 3
    alerts = health.reconnect_reminders(later)
    assert [(a["data"]["connection"], a["severity"], a["data"]["days_left"]) for a in alerts] == [
        ("Gmail (acct1)", "medium", 3), ("Google Drive (backups)", "medium", 4)]
    assert "scripts/google-reconnect.sh" in alerts[0]["message"]
    last_day = health.reconnect_reminders(NOW + dt.timedelta(days=4, hours=12))
    assert last_day[0]["severity"] == "high"
    expired = health.reconnect_reminders(NOW + dt.timedelta(days=6))
    assert "has expired" in expired[0]["message"]


def test_no_reminders_once_the_apps_are_published(settings):
    from mail.models import GmailAccount

    settings.GOOGLE_OAUTH_TESTING = False
    GmailAccount.objects.create(tag="acct1", token_encrypted="x", connected_at=NOW - dt.timedelta(days=6))
    assert health.reconnect_reminders(NOW) == []
