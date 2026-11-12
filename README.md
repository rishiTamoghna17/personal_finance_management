# Personal finance agent (India)

Private, self-hosted, single-user. Firefly III is the ledger; a small Django
service ("bridge") will ingest bank messages and feed it. Rules: [CLAUDE.md](CLAUDE.md).
Spec: [docs/SPEC.md](docs/SPEC.md). Status: [docs/PROGRESS.md](docs/PROGRESS.md).

## What M1 gives you

| Service | What it is | Reachable at |
| --- | --- | --- |
| `firefly` | Firefly III 6.7.9, the ledger | http://localhost:8080 |
| `firefly-cron` | Firefly's daily job (03:00 IST) | internal only |
| `postgres` | One server, two databases (`firefly`, `bridge`), two roles that cannot read each other | internal only |
| `redis` | Celery broker and bridge cache | internal only |
| `bridge` | Django REST API | http://localhost:8000 |
| `worker`, `beat` | Celery (no tasks yet; they start in M2/M3) | internal only |

Published ports are bound to `127.0.0.1`. Nothing is reachable from the network until M7 adds HTTPS.

## First-time setup

1. Create `.env` with generated secrets:
   ```bash
   sh scripts/init-env.sh
   ```
2. Start the stack:
   ```bash
   docker compose up -d --build
   ```
3. Open http://localhost:8080 and register. The first user becomes the owner.
   This is the one step that cannot be automated.
4. In Firefly: Options > Profile > OAuth > Personal Access Tokens > Create new token.
   Paste it into `.env` as `FIREFLY_ACCESS_TOKEN=...`, then reload the bridge:
   ```bash
   docker compose up -d bridge worker beat
   ```
5. Describe your accounts. Copy the example and edit it; `accounts.yaml` is gitignored.
   ```bash
   cp accounts.example.yaml accounts.yaml
   ```
   Amounts are quoted strings (`"12345.67"`). Use `last4` only, never a full account or card number.
6. Check the file, then create the accounts. Both commands are safe to re-run.
   ```bash
   docker compose run --rm -T bridge python manage.py seed_firefly --dry-run - < accounts.yaml
   ```
   ```bash
   docker compose run --rm -T bridge python manage.py seed_firefly - < accounts.yaml
   ```
   This also enables INR and makes it Firefly's primary currency.

How accounts map to Firefly:

| `kind` in accounts.yaml | Firefly account | Opening balance |
| --- | --- | --- |
| `bank` | Asset account (savings or default role) | Positive |
| `credit_card` | Asset account with the credit-card role | Negative (what you owe); the credit limit is not recorded |
| `loan`, `status: active` | Liability account, type loan | What you owe |
| `loan`, `status: planned` | Not created until you change it to `active` | - |

## Bridge API (v1)

Every request needs `Authorization: Bearer <BRIDGE_API_TOKEN>`. The API is read-only.

| Endpoint | Returns |
| --- | --- |
| `GET /api/v1/health` | Status of the database, cache and Firefly connection. 503 if any is down. |
| `GET /api/v1/accounts` | Your accounts, cards and loans from Firefly. Balances are integer paise, marked `calculated`. Account numbers are cut to `last4`. |

Limits: 120 requests a minute with a token, 20 without, 256 KiB per request.

## Tests

```bash
docker compose run --rm --no-deps -v "$PWD/accounts.example.yaml:/accounts.example.yaml:ro" -e BRIDGE_DB_HOST= -e REDIS_URL= bridge pytest -q
```

The tests use a fake Firefly and need no running stack.

## Everyday commands

```bash
docker compose ps
```
```bash
docker compose logs -f bridge
```
```bash
docker compose down
```

`docker compose down -v` also deletes the database volume, which means the whole ledger. Do not use it unless you mean to start over.

## Licences of what this runs

Firefly III is AGPL-3.0 and runs here as an unmodified image. The bridge only calls its REST API.
