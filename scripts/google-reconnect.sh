#!/bin/sh
# Reconnect every Google sign-in in one go (needed every few days while the Google apps stay in "Testing";
# the advisor's alerts remind you from day 3). For each step a link is printed: open it, sign in, allow.
#   sh scripts/google-reconnect.sh
set -eu
cd "$(dirname "$0")/.."
echo "== Gmail account 1"
docker compose run --rm -p 127.0.0.1:8765:8765 -v "$PWD/secrets:/app/secrets:ro" bridge \
  python manage.py gmail_connect acct1 --client secrets/gmail_client.json
echo "== Gmail account 2"
docker compose run --rm -p 127.0.0.1:8765:8765 -v "$PWD/secrets:/app/secrets:ro" bridge \
  python manage.py gmail_connect acct2 --client secrets/gmail_client_2.json
echo "== Google Drive (backups)"
sh scripts/gdrive-connect.sh
echo "All Google sign-ins renewed. The next reminder comes in 3 days."
