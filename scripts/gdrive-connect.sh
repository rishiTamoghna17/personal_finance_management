#!/bin/sh
# One-time: connect Google Drive for encrypted backups. Puts GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET and GDRIVE_TOKEN
# into .env without printing them. Needs the Drive API enabled in the Google Cloud project of the client file.
#   sh scripts/gdrive-connect.sh [secrets/gmail_client.json]
set -eu
cd "$(dirname "$0")/.."
CLIENT="${1:-secrets/gmail_client.json}"
[ -f .env ] && [ -f "$CLIENT" ] || { echo "need .env and $CLIENT" >&2; exit 1; }
umask 077
token=$(docker compose run --rm -T -p 127.0.0.1:8766:8766 -v "$PWD/secrets:/app/secrets:ro" bridge python manage.py gdrive_connect --client "$CLIENT" --port 8766)
[ -n "$token" ] || { echo "no token received; nothing changed" >&2; exit 1; }
id=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(next(iter(d.values()))["client_id"])' "$CLIENT")
secret=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(next(iter(d.values()))["client_secret"])' "$CLIENT")
tmp=$(mktemp)
grep -v -E '^GDRIVE_(CLIENT_ID|CLIENT_SECRET|TOKEN|CONNECTED_AT)=' .env > "$tmp" || true
printf "GDRIVE_CLIENT_ID=%s\nGDRIVE_CLIENT_SECRET=%s\nGDRIVE_TOKEN='%s'\nGDRIVE_CONNECTED_AT=%s\n" "$id" "$secret" "$token" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$tmp"
cat "$tmp" > .env && rm -f "$tmp"
echo "Google Drive connected for backups (drive.file only). Saved in .env."
docker compose up -d backup bridge worker beat >/dev/null 2>&1 && echo "Backup and bridge restarted with the new sign-in."
