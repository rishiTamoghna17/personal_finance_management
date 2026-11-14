"""One-time Google Drive sign-in for the encrypted backups. Asks only for `drive.file`: the bridge can see and
change only the files it creates itself (the backup folder), nothing else in your Drive.

Run through scripts/gdrive-connect.sh, which puts the result into .env without showing it.
"""
import datetime as dt
import json
import sys

from django.core.management.base import BaseCommand, CommandError

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class Command(BaseCommand):
    help = "Sign in to Google Drive (drive.file only) and print an rclone token to stdout."

    def add_arguments(self, parser):
        parser.add_argument("--client", required=True, help="OAuth client JSON (Desktop app)")
        parser.add_argument("--port", type=int, default=8766)

    def handle(self, *args, client, port, **options):
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(client, SCOPES)
        real_stdout, sys.stdout = sys.stdout, sys.stderr  # the sign-in link goes to the screen; stdout carries only the token
        try:
            creds = flow.run_local_server(
                host="localhost", bind_addr="0.0.0.0", port=port, open_browser=False,
                authorization_prompt_message="Open this link in your browser and sign in to the Google account whose "
                                             "Drive should hold the backups:\n{url}\n",
            success_message="Connected. You can close this tab.")
        finally:
            sys.stdout = real_stdout
        if set(creds.scopes or SCOPES) - set(SCOPES):
            raise CommandError("refusing a token with more than drive.file access")
        if not creds.refresh_token:
            raise CommandError("no refresh token was returned; sign in again")
        expiry = (creds.expiry or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        token = {"access_token": creds.token, "token_type": "Bearer", "refresh_token": creds.refresh_token,
                 "expiry": expiry}
        sys.stderr.write("Signed in. Saving the token to .env (not shown).\n")
        sys.stdout.write(json.dumps(token, separators=(",", ":")) + "\n")
