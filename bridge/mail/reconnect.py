"""Renew Google sign-ins from the phone (M7). Celery creates a one-time link when a sign-in is 3 days old; the alert
(later a phone notification) carries it; the owner taps it, signs in at Google, and the bridge saves the new token.

Safety: links are random, single use and expire after 24 hours; the scopes are exactly the ones already used
(Gmail read-only, Drive drive.file); the Google account must be the same one as before (compared by SHA-256 of the
address); the whole thing only works over the private HTTPS address (Tailscale)."""
import datetime as dt
import hashlib
import json
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.crypto import decrypt, encrypt

from .models import GmailAccount, GoogleCredential, ReconnectLink

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REMIND_FROM_DAYS = 3


class ReconnectError(Exception):
    pass


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def email_hash(address):
    return _hash(address.strip().lower())


def callback_url():
    return f"{settings.PUBLIC_BASE_URL}/api/v1/google/callback"


def enabled():
    return settings.PUBLIC_BASE_URL.startswith("https://")


def client_for(connection):
    tag = combined_gmail_tag(connection)
    if tag:
        gmail_key = settings.GOOGLE_CONNECTION_CLIENT.get(tag, "")
        drive_key = settings.GOOGLE_CONNECTION_CLIENT.get("drive", "")
        if not gmail_key or gmail_key != drive_key:
            raise ReconnectError("Gmail and Drive do not share the same OAuth client")
        key = gmail_key
    else:
        key = settings.GOOGLE_CONNECTION_CLIENT.get(connection.split(":")[-1], "")
    client_id, client_secret = settings.GOOGLE_WEB_CLIENTS.get(key, ("", ""))
    return key, client_id, client_secret


def combined_gmail_tag(connection=None):
    """Return the Gmail tag for a combined link, or the configured Gmail tag eligible for grouping."""
    if connection is not None:
        prefix = "gmail:"
        suffix = "+drive"
        if connection.startswith(prefix) and connection.endswith(suffix):
            return connection[len(prefix):-len(suffix)]
        return ""
    tag = getattr(settings, "GOOGLE_DRIVE_GMAIL_TAG", "")
    if not tag:
        return ""
    account = GmailAccount.objects.filter(tag=tag, enabled=True).first()
    if account is None:
        return ""
    gmail_key = settings.GOOGLE_CONNECTION_CLIENT.get(tag, "")
    drive_key = settings.GOOGLE_CONNECTION_CLIENT.get("drive", "")
    if not gmail_key or gmail_key != drive_key:
        return ""
    drive = GoogleCredential.objects.filter(name="drive").first()
    if drive and account.email_hash and drive.email_hash and account.email_hash != drive.email_hash:
        return ""
    if not drive and not settings.GDRIVE_CONNECTED_AT:
        return ""
    return tag


def scopes_for(connection):
    if connection == "drive":
        return DRIVE_SCOPES
    if combined_gmail_tag(connection):
        return GMAIL_SCOPES + DRIVE_SCOPES
    return GMAIL_SCOPES


def connections():
    """[(connection, connected_at)] for every Google sign-in the bridge depends on."""
    out = []
    drive = GoogleCredential.objects.filter(name="drive").first()
    drive_at = drive.connected_at if drive else None
    if drive_at is None and settings.GDRIVE_CONNECTED_AT:
        drive_at = dt.datetime.fromisoformat(settings.GDRIVE_CONNECTED_AT.replace("Z", "+00:00"))
    combined_tag = combined_gmail_tag()
    for account in GmailAccount.objects.filter(enabled=True):
        connected_at = account.connected_at or account.created_at
        if account.tag == combined_tag:
            connected_at = min(connected_at, drive_at)
            out.append((f"gmail:{account.tag}+drive", connected_at))
        else:
            out.append((f"gmail:{account.tag}", connected_at))
    if drive_at and not combined_tag:
        out.append(("drive", drive_at))
    return out


def live_link(connection, now=None):
    now = now or timezone.now()
    return ReconnectLink.objects.filter(connection=connection, used_at__isnull=True, expires_at__gt=now).first()


def link_url(link):
    return f"{settings.PUBLIC_BASE_URL}/api/v1/google/connect/{decrypt(link.token_encrypted)}"


def prepare_links(now=None):
    """Daily (Celery): a fresh link for each sign-in that is 3 or more days old and has no live link."""
    if not (settings.GOOGLE_OAUTH_TESTING and enabled()):
        return 0
    now = now or timezone.now()
    made = 0
    for connection, connected_at in connections():
        if now - connected_at < dt.timedelta(days=REMIND_FROM_DAYS) or live_link(connection, now):
            continue
        if not client_for(connection)[1]:
            continue  # no web client configured for this Google project yet
        tag = combined_gmail_tag(connection)
        if tag:
            ReconnectLink.objects.filter(connection__in=[f"gmail:{tag}", "drive"], used_at__isnull=True).update(used_at=now)
        token = secrets.token_urlsafe(32)
        ReconnectLink.objects.create(connection=connection, token_hash=_hash(token), token_encrypted=encrypt(token),
                                     expires_at=now + dt.timedelta(hours=settings.RECONNECT_LINK_HOURS))
        made += 1
    return made


def _flow(connection, code_verifier=None):
    from google_auth_oauthlib.flow import Flow

    _, client_id, client_secret = client_for(connection)
    if not client_id:
        raise ReconnectError("no web sign-in client is configured for this account")
    config = {"web": {"client_id": client_id, "client_secret": client_secret,
                      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                      "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": [callback_url()]}}
    return Flow.from_client_config(config, scopes=scopes_for(connection), redirect_uri=callback_url(),
                                   code_verifier=code_verifier, autogenerate_code_verifier=code_verifier is None)


def start(token, now=None):
    """The owner tapped the link: returns the Google sign-in URL to send them to."""
    now = now or timezone.now()
    link = ReconnectLink.objects.filter(token_hash=_hash(token)).first()
    if link is None or link.used_at or link.expires_at <= now:
        raise ReconnectError("this link has expired or was already used; a new one comes with the next reminder")
    flow = _flow(link.connection)
    state = secrets.token_urlsafe(24)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state,
                                    include_granted_scopes="false")
    link.oauth_state, link.code_verifier = state, encrypt(flow.code_verifier)
    link.save(update_fields=["oauth_state", "code_verifier"])
    return url


def _address(connection, creds):
    from googleapiclient.discovery import build

    if connection == "drive":
        about = build("drive", "v3", credentials=creds, cache_discovery=False).about().get(fields="user").execute()
        return about["user"]["emailAddress"]
    return build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()[
        "emailAddress"]


def write_backup_token(client_key, creds):
    """Hand the Drive sign-in to the backup container (shared volume, owner-only file)."""
    _, client_id, client_secret = client_for("drive")
    token = {"access_token": creds.token, "token_type": "Bearer", "refresh_token": creds.refresh_token,
             "expiry": (creds.expiry or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    folder = Path(settings.BACKUP_SECRETS_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "gdrive.env"
    lines = [f"RCLONE_CONFIG_GDRIVE_CLIENT_ID={client_id}", f"RCLONE_CONFIG_GDRIVE_CLIENT_SECRET={client_secret}",
             f"RCLONE_CONFIG_GDRIVE_TOKEN='{json.dumps(token, separators=(',', ':'))}'"]
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def finish(state, code, now=None, address_of=None):
    """Google sent the owner back. Exchange the code, check it is the same account, save. Returns a label."""
    now = now or timezone.now()
    link = ReconnectLink.objects.filter(oauth_state=state).first() if state else None
    if link is None or link.used_at or link.expires_at <= now or not link.code_verifier:
        raise ReconnectError("this sign-in link has expired or was already used")
    connection = link.connection
    combined_tag = combined_gmail_tag(connection)
    flow = _flow(connection, code_verifier=decrypt(link.code_verifier))
    flow.fetch_token(code=code)
    creds = flow.credentials
    if set(creds.scopes or []) - set(scopes_for(connection)):
        raise ReconnectError("Google granted more access than asked for; nothing was saved")
    if not creds.refresh_token:
        raise ReconnectError("Google did not return a lasting sign-in; try the link again")
    address = (address_of or _address)(connection, creds)
    digest = email_hash(address)
    with transaction.atomic():
        if connection.startswith("gmail:"):
            tag = combined_tag or connection.split(":", 1)[1]
            account = GmailAccount.objects.select_for_update().get(tag=tag)
            if account.email_hash and account.email_hash != digest:
                raise ReconnectError("that is a different Google account from the one connected before; nothing saved")
            account.token_encrypted = encrypt(creds.to_json())
            account.email_hash, account.connected_at = digest, now
            account.save(update_fields=["token_encrypted", "email_hash", "connected_at"])
            if combined_tag:
                existing = GoogleCredential.objects.select_for_update().filter(name="drive").first()
                if existing and existing.email_hash and existing.email_hash != digest:
                    raise ReconnectError("that is a different Google account from the one used for backups; nothing saved")
                client_key = client_for(connection)[0]
                GoogleCredential.objects.update_or_create(
                    name="drive", defaults={"token_encrypted": encrypt(creds.to_json()), "client": client_key,
                                            "email_hash": digest, "connected_at": now})
                write_backup_token(client_key, creds)
                label = f"Gmail ({account.tag}) and Google Drive backups"
            else:
                label = f"Gmail ({account.tag})"
        else:
            existing = GoogleCredential.objects.filter(name="drive").first()
            if existing and existing.email_hash and existing.email_hash != digest:
                raise ReconnectError("that is a different Google account from the one used for backups; nothing saved")
            client_key = client_for("drive")[0]
            GoogleCredential.objects.update_or_create(
                name="drive", defaults={"token_encrypted": encrypt(creds.to_json()), "client": client_key,
                                        "email_hash": digest, "connected_at": now})
            write_backup_token(client_key, creds)
            label = "Google Drive (backups)"
        link.used_at = now
        link.save(update_fields=["used_at"])
        invalidated = [connection]
        if combined_tag:
            invalidated.extend([f"gmail:{combined_tag}", "drive"])
        ReconnectLink.objects.filter(connection__in=invalidated, used_at__isnull=True).update(used_at=now)
    return label
