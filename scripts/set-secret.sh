#!/bin/sh
# Put one secret into .env from a hidden prompt (never on the command line, never shown).
#   sh scripts/set-secret.sh TS_AUTHKEY
set -eu
cd "$(dirname "$0")/.."
name="${1:?which setting? e.g. TS_AUTHKEY}"
case "$name" in *[!A-Z0-9_]*) echo "bad name" >&2; exit 1;; esac
printf "Paste %s (hidden), then Enter: " "$name"
stty -echo; IFS= read -r value; stty echo; echo
[ -n "$value" ] || { echo "nothing entered; .env unchanged" >&2; exit 1; }
umask 077
tmp=$(mktemp)
grep -v "^$name=" .env > "$tmp" || true
printf '%s=%s\n' "$name" "$value" >> "$tmp"
cat "$tmp" > .env && rm -f "$tmp"
echo "$name saved in .env (${#value} characters)."
