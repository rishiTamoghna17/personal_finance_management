#!/bin/sh
# Creates .env from .env.example, replacing each __GENERATE__ with its own
# random 32-character secret. Refuses to overwrite an existing .env.
set -eu
cd "$(dirname "$0")/.."

if [ -e .env ]; then
  echo ".env already exists; not touching it." >&2
  exit 1
fi

umask 077
: > .env
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    *=__GENERATE_FERNET__)
      # A Fernet key: 32 random bytes, URL-safe base64.
      secret=$(head -c 32 /dev/urandom | base64 | tr '+/' '-_')
      printf '%s=%s\n' "${line%%=*}" "$secret" >> .env
      ;;
    *=__GENERATE__)
      secret=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)
      printf '%s=%s\n' "${line%%=*}" "$secret" >> .env
      ;;
    *) printf '%s\n' "$line" >> .env ;;
  esac
done < .env.example
echo "Wrote .env with generated secrets (values not shown)."
