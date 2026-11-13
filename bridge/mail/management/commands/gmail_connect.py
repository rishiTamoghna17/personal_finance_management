"""Connect a Gmail account with read-only access and store its token encrypted.

Sign in (opens nothing by itself; prints a link to open on this Mac):
  docker compose run --rm -p 127.0.0.1:8765:8765 bridge python manage.py gmail_connect acct1 --client secrets/gmail_client.json
Or import a token already obtained with the same read-only scope:
  docker compose run --rm -T bridge python manage.py gmail_connect acct1 --token-stdin < token.json
"""
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from core.crypto import encrypt
from mail.gmail import SCOPES
from mail.models import GmailAccount


class Command(BaseCommand):
    help = "Connect a Gmail account (read-only) and store its OAuth token encrypted."

    def add_arguments(self, parser):
        parser.add_argument("tag", help="short name, e.g. acct1")
        parser.add_argument("--client", help="path to the OAuth client JSON (Desktop app)")
        parser.add_argument("--port", type=int, default=8765)
        parser.add_argument("--token-stdin", action="store_true", help="read an existing token JSON from stdin")

    def handle(self, *args, tag, client, port, token_stdin, **options):
        if token_stdin:
            info = json.loads(sys.stdin.read())
        elif client:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(client, SCOPES)
            creds = flow.run_local_server(host="localhost", bind_addr="0.0.0.0", port=port, open_browser=False,
                                          authorization_prompt_message="Open this link in your browser:\n{url}\n",
                                          success_message="Connected. You can close this tab.")
            info = json.loads(creds.to_json())
        else:
            raise CommandError("give --client <file> to sign in, or --token-stdin to import a token")
        scopes = set(info.get("scopes") or [])
        if scopes - set(SCOPES):
            raise CommandError("refusing a token with more than read-only Gmail access")
        if not info.get("refresh_token"):
            raise CommandError("token has no refresh token; sign in again")
        from mail.gmail import service_for

        account, _ = GmailAccount.objects.update_or_create(tag=tag, defaults={"token_encrypted": encrypt(json.dumps(info))})
        address = service_for(account).users().getProfile(userId="me").execute()["emailAddress"]
        account.address_hint = address[:3] + "***@" + address.split("@")[1]
        account.save(update_fields=["address_hint"])
        self.stdout.write(self.style.SUCCESS(f"connected {tag} ({account.address_hint}), read-only"))
