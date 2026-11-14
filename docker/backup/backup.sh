#!/bin/sh
# Encrypted backup of everything needed to rebuild the ledger:
#   both PostgreSQL databases (Firefly and bridge) + roles, the bridge files (statements as received),
#   the categoriser's settings. restic encrypts on this machine before anything goes to Google Drive (via rclone),
#   so Google only ever holds encrypted blobs.
# Never prints secrets. Writes /status/last.json for the bridge's health alert.
set -eu
MODE="${1:-nightly}"
STATUS=/status/last.json
WORK=/tmp/backup-work
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
status() { printf '{"ok": %s, "at": "%s", "detail": "%s"}\n' "$1" "$(now)" "$2" > "$STATUS.tmp" && mv "$STATUS.tmp" "$STATUS"; }

if [ "$MODE" = "if-missed" ] && [ -f "$STATUS" ]; then
  if grep -q '"ok": true' "$STATUS" && [ -n "$(find "$STATUS" -mmin -1560)" ]; then exit 0; fi
fi

# A Drive sign-in renewed from the phone (bridge, tap-to-reconnect) replaces the one from .env.
if [ -s /secrets/gdrive.env ]; then set -a; . /secrets/gdrive.env; set +a; fi

trap 'rm -rf "$WORK"; [ "${done_ok:-0}" = 1 ] || status false "backup failed; see the backup container log"' EXIT
rm -rf "$WORK"; mkdir -p "$WORK"; chmod 700 "$WORK"
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dumpall -h postgres -U postgres --globals-only > "$WORK/roles.sql"
pg_dump -h postgres -U postgres -Fc -f "$WORK/firefly.dump" "${FIREFLY_DB_NAME:-firefly}"
pg_dump -h postgres -U postgres -Fc -f "$WORK/bridge.dump" "${BRIDGE_DB_NAME:-bridge}"
unset PGPASSWORD

restic cat config >/dev/null 2>&1 || restic init
restic backup --quiet --tag "$MODE" --host finance-server "$WORK" /backup
if [ "$(date +%u)" = "7" ] || [ "$MODE" = "maintain" ]; then
  restic forget --quiet --host finance-server --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune
  restic check --quiet
fi
snapshot=$(restic snapshots --latest 1 --json --host finance-server | sed -n 's/.*"short_id":"\([0-9a-f]*\)".*/\1/p' | tail -1)
done_ok=1
status true "snapshot ${snapshot:-unknown}"
echo "backup: ok $(now) snapshot ${snapshot:-unknown}"
