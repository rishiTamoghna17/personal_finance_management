#!/bin/sh
# Restore drill: take the latest backup from Google Drive, load both databases into a THROWAWAY PostgreSQL
# (nothing live is touched), and compare row counts with the running system. Then delete everything it made.
#   sh scripts/restore-drill.sh
set -eu
cd "$(dirname "$0")/.."
NET=finance-drill-net; PG=finance-drill-pg
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker volume rm -f finance-drill-restore >/dev/null 2>&1 || true;
            docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker volume create finance-drill-restore >/dev/null
echo "1/4 restoring the latest snapshot from Google Drive (decrypted only inside a container)"
docker compose run --rm -T --no-deps -v finance-drill-restore:/restore --entrypoint restic backup \
  restore latest --host finance-server --target /restore --quiet
echo "2/4 starting a throwaway PostgreSQL"
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=drill -v finance-drill-restore:/restore:ro \
  postgres:17-alpine >/dev/null
until docker exec "$PG" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
sleep 2
echo "3/4 loading roles and both databases"
docker exec "$PG" sh -c 'psql -q -U postgres -f /restore/tmp/backup-work/roles.sql >/dev/null 2>&1 || true
  for db in firefly bridge; do createdb -U postgres $db 2>/dev/null || true;
    pg_restore -U postgres -d $db --no-owner /restore/tmp/backup-work/$db.dump; done'
echo "4/4 comparing with the live system"
q_bridge="select count(*) from ingest_rawmessage; select count(*) from ingest_ledgerentry;"
q_firefly="select count(*) from transaction_journals where deleted_at is null; select count(*) from accounts where deleted_at is null;"
live_b=$(docker compose exec -T postgres psql -U postgres -d bridge -tAc "$q_bridge" | tr '\n' ' ')
drill_b=$(docker exec "$PG" psql -U postgres -d bridge -tAc "$q_bridge" | tr '\n' ' ')
live_f=$(docker compose exec -T postgres psql -U postgres -d firefly -tAc "$q_firefly" | tr '\n' ' ')
drill_f=$(docker exec "$PG" psql -U postgres -d firefly -tAc "$q_firefly" | tr '\n' ' ')
files=$(docker run --rm -v finance-drill-restore:/r alpine:3.22 sh -c 'find /r/backup -type f | wc -l')
echo "bridge  messages, entries   live: $live_b  restored: $drill_b"
echo "firefly transactions, accts live: $live_f  restored: $drill_f"
echo "bridge files restored: $files"
[ "$live_b" = "$drill_b" ] && [ "$live_f" = "$drill_f" ] && echo "RESTORE DRILL PASSED" || { echo "RESTORE DRILL: counts differ (new data since the backup is normal; investigate otherwise)"; exit 1; }
