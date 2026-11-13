"""Read-only Gmail access. Only the gmail.readonly scope is ever requested."""
import json
import time

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.crypto import decrypt

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailError(Exception):
    pass


def service_for(account):
    info = json.loads(decrypt(account.token_encrypted))
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if set(creds.scopes or SCOPES) - set(SCOPES):
        raise GmailError("token has more than read-only access; reconnect the account")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def call(request, retries=6):
    """Execute a Gmail request, backing off on rate limits (Gmail allows a few hundred calls a minute)."""
    for attempt in range(retries):
        try:
            return request.execute()
        except HttpError as exc:
            if exc.resp.status in (403, 429, 500, 503) and attempt < retries - 1:
                time.sleep(min(60, 5 * 2**attempt))
                continue
            raise GmailError(f"Gmail API error {exc.resp.status}") from None


def list_ids(service, query):
    ids, page = [], None
    while True:
        result = call(service.users().messages().list(userId="me", q=query, maxResults=500, pageToken=page))
        ids += [m["id"] for m in result.get("messages", [])]
        page = result.get("nextPageToken")
        if not page:
            return ids


def get_message(service, message_id):
    time.sleep(settings.GMAIL_REQUEST_PAUSE_SECONDS)
    return call(service.users().messages().get(userId="me", id=message_id, format="full"))
