"""M7: renew Google sign-ins from the phone with a one-time link. Google is mocked."""
import datetime as dt
from types import SimpleNamespace

import pytest
from django.test import Client

from mail import reconnect
from mail.models import GmailAccount, GoogleCredential, ReconnectLink

pytestmark = pytest.mark.django_db
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)  # links are checked against the real clock


@pytest.fixture
def setup(settings, tmp_path):
    settings.PUBLIC_BASE_URL = "https://finance.tail0.ts.net"
    settings.GOOGLE_OAUTH_TESTING = True
    settings.GOOGLE_WEB_CLIENTS = {"1": ("id-1", "secret-1"), "2": ("id-2", "secret-2")}
    settings.GOOGLE_CONNECTION_CLIENT = {"acct1": "1", "acct2": "2", "drive": "1"}
    settings.GDRIVE_CONNECTED_AT = ""
    settings.BACKUP_SECRETS_DIR = tmp_path
    settings.ALLOWED_HOSTS = ["testserver", "finance.tail0.ts.net"]
    return GmailAccount.objects.create(tag="acct1", token_encrypted="x", connected_at=NOW - dt.timedelta(days=4),
                                       email_hash=reconnect.email_hash("owner@gmail.com"))


class FakeFlow:
    """Stands in for google_auth_oauthlib's Flow."""
    granted = ["https://www.googleapis.com/auth/gmail.readonly"]
    refresh = "refresh-token"

    def __init__(self, connection, code_verifier=None):
        self.connection, self.code_verifier = connection, code_verifier or "verifier-123"
        self.credentials = None

    def authorization_url(self, **kw):
        self.kw = kw
        return f"https://accounts.google.com/o/oauth2/auth?state={kw['state']}", kw["state"]

    def fetch_token(self, code):
        assert code == "good-code" and self.code_verifier == "verifier-123"
        self.credentials = SimpleNamespace(scopes=self.granted, refresh_token=self.refresh, token="access",
                                           expiry=None, to_json=lambda: '{"refresh_token": "refresh-token"}')


@pytest.fixture
def fake_google(monkeypatch):
    monkeypatch.setattr(reconnect, "_flow", lambda connection, code_verifier=None: FakeFlow(connection, code_verifier))
    return FakeFlow


def make_link(connection="gmail:acct1"):
    assert reconnect.prepare_links(NOW) >= 1
    return ReconnectLink.objects.get(connection=connection)


def test_links_only_for_sign_ins_three_days_old_and_only_once(setup):
    GmailAccount.objects.create(tag="acct2", token_encrypted="x", connected_at=NOW - dt.timedelta(days=1))
    assert reconnect.prepare_links(NOW) == 1
    assert reconnect.prepare_links(NOW) == 0  # a live link already exists
    link = ReconnectLink.objects.get()
    assert link.connection == "gmail:acct1" and reconnect.link_url(link).startswith("https://finance.tail0.ts.net/api/v1/google/connect/")


def test_no_links_without_https_address(setup, settings):
    settings.PUBLIC_BASE_URL = "http://192.168.0.106:8000"
    assert reconnect.prepare_links(NOW) == 0


def test_alert_carries_the_link(setup, settings):
    from advisor import health

    make_link()
    alert = health.reconnect_reminders(NOW)[0]
    assert "tap the link" in alert["message"] and alert["data"]["link"].startswith("https://finance.tail0.ts.net/")


def test_full_reconnect_same_account(setup, fake_google):
    link = make_link()
    token = reconnect.link_url(link).rsplit("/", 1)[1]
    response = Client().get(f"/api/v1/google/connect/{token}", HTTP_HOST="finance.tail0.ts.net")
    assert response.status_code == 302 and "accounts.google.com" in response["Location"]
    link.refresh_from_db()
    label = reconnect.finish(link.oauth_state, "good-code", NOW, address_of=lambda c, creds: "Owner@gmail.com")
    assert label == "Gmail (acct1)"
    account = GmailAccount.objects.get(tag="acct1")
    assert account.connected_at == NOW and "refresh-token" not in account.token_encrypted  # stored encrypted
    with pytest.raises(reconnect.ReconnectError):  # single use
        reconnect.finish(link.oauth_state, "good-code", NOW, address_of=lambda c, creds: "owner@gmail.com")


def test_different_google_account_is_refused(setup, fake_google):
    link = make_link()
    reconnect.start(reconnect.link_url(link).rsplit("/", 1)[1], NOW)
    link.refresh_from_db()
    with pytest.raises(reconnect.ReconnectError, match="different Google account"):
        reconnect.finish(link.oauth_state, "good-code", NOW, address_of=lambda c, creds: "someone@else.com")
    assert GmailAccount.objects.get(tag="acct1").connected_at == NOW - dt.timedelta(days=4)


def test_more_access_than_asked_is_refused(setup, fake_google, monkeypatch):
    monkeypatch.setattr(FakeFlow, "granted", ["https://www.googleapis.com/auth/gmail.modify"])
    link = make_link()
    reconnect.start(reconnect.link_url(link).rsplit("/", 1)[1], NOW)
    link.refresh_from_db()
    with pytest.raises(reconnect.ReconnectError, match="more access"):
        reconnect.finish(link.oauth_state, "good-code", NOW, address_of=lambda c, creds: "owner@gmail.com")


def test_expired_link_is_refused(setup, fake_google):
    link = make_link()
    with pytest.raises(reconnect.ReconnectError, match="expired"):
        reconnect.start(reconnect.link_url(link).rsplit("/", 1)[1], NOW + dt.timedelta(hours=25))
    assert Client().get("/api/v1/google/connect/not-a-real-token", HTTP_HOST="finance.tail0.ts.net").status_code == 410


def test_drive_reconnect_hands_the_token_to_the_backup_job(setup, fake_google, monkeypatch, settings, tmp_path):
    monkeypatch.setattr(FakeFlow, "granted", ["https://www.googleapis.com/auth/drive.file"])
    settings.GDRIVE_CONNECTED_AT = "2026-11-10T00:00:00Z"
    reconnect.prepare_links(NOW)
    link = ReconnectLink.objects.get(connection="drive")
    reconnect.start(reconnect.link_url(link).rsplit("/", 1)[1], NOW)
    link.refresh_from_db()
    assert reconnect.finish(link.oauth_state, "good-code", NOW, address_of=lambda c, creds: "owner@gmail.com") == \
        "Google Drive (backups)"
    env = (tmp_path / "gdrive.env").read_text()
    assert "RCLONE_CONFIG_GDRIVE_CLIENT_ID=id-1" in env and "refresh-token" in env
    assert oct((tmp_path / "gdrive.env").stat().st_mode & 0o777) == "0o600"
    assert GoogleCredential.objects.get(name="drive").connected_at == NOW


def test_cancelled_sign_in_changes_nothing(setup):
    response = Client().get("/api/v1/google/callback?error=access_denied", HTTP_HOST="finance.tail0.ts.net")
    assert response.status_code == 400 and b"Nothing changed" in response.content
