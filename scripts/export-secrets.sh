#!/bin/sh
# Pack the files a new server needs and that are never in git (.env, accounts.yaml, goals.yaml, secrets/)
# into ONE file encrypted with a passphrase you type (hidden). Keep that file and the passphrase in your password
# manager. Without .env (BRIDGE_ENCRYPTION_KEY, RESTIC_PASSWORD) the database secrets and the backups cannot be read.
#   sh scripts/export-secrets.sh            -> finance-secrets-YYYYMMDD.enc in this folder (gitignored)
# Restore on the new machine:
#   openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in finance-secrets-YYYYMMDD.enc | tar -xzf -
set -eu
cd "$(dirname "$0")/.."
out="finance-secrets-$(date +%Y%m%d).enc"
files=".env"
for f in accounts.yaml goals.yaml secrets; do [ -e "$f" ] && files="$files $f"; done
umask 077
tar -czf - $files | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -out "$out"
echo "Wrote $out (encrypted). Move it into your password manager, then delete it here."
