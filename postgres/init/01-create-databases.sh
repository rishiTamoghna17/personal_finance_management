#!/bin/sh
# Runs once, when the postgres data volume is first created.
# Creates one role and one database each for Firefly III and the bridge,
# and stops either role from connecting to the other's database.
set -eu

create_role_and_db() {
  db="$1"; role="$2"; password="$3"
  psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres \
    -v db="$db" -v role="$role" -v password="$password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role', :'password') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'role') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db') \gexec
SQL
}

create_role_and_db "$FIREFLY_DB_NAME" "$FIREFLY_DB_USER" "$FIREFLY_DB_PASSWORD"
create_role_and_db "$BRIDGE_DB_NAME" "$BRIDGE_DB_USER" "$BRIDGE_DB_PASSWORD"
