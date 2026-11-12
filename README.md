# Personal finance agent (India)

Private, self-hosted, single-user. Firefly III is the ledger; a small Django
service ("bridge") will ingest bank messages and feed it. Rules: [CLAUDE.md](CLAUDE.md).
Spec: [docs/SPEC.md](docs/SPEC.md). Status: [docs/PROGRESS.md](docs/PROGRESS.md).

## What runs (M1 + M2)

| Service | What it is | Reachable at |
| --- | --- | --- |
| `firefly` | Firefly III 6.7.9, the ledger | http://localhost:8080 |
| `firefly-cron` | Firefly's daily job (03:00 IST) | internal only |
| `postgres` | One server, two databases (`firefly`, `bridge`), two roles that cannot read each other | internal only |
| `redis` | Celery broker and bridge cache | internal only |
| `bridge` | Django REST API | http://localhost:8000 |
| `worker`, `beat` | Celery: parses stored SMS, and every minute posts settled transactions to Firefly | internal only |

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

Every request needs `Authorization: Bearer <BRIDGE_API_TOKEN>`. Nothing in the API can move money; it only records what your banks report.

| Endpoint | Returns |
| --- | --- |
| `GET /api/v1/health` | Status of the database, cache and Firefly connection. 503 if any is down. |
| `GET /api/v1/accounts` | Your accounts, cards and loans from Firefly. Balances are integer paise. `balance_status` is `confirmed` when the bank reported a balance in the last 72 hours, `stale` when that report is older, and `calculated` when only Firefly's ledger sum is known. Account numbers are cut to `last4`. |
| `POST /api/v1/ingest/sms` | Bank SMS from the phone. Also needs an `X-Signature` HMAC header. See [docs/sms-forwarder.md](docs/sms-forwarder.md). |
| `GET /api/v1/review` | Messages and payments that need you: unknown sender, unparsed, unknown account, ambiguous match, unpaired transfer, failed post. `?status=all` shows closed items too. |
| `POST /api/v1/review/<id>/ignore` | Close an item; its message is kept, marked ignored. |
| `POST /api/v1/review/<id>/reparse` | Parse the message again, e.g. after a bank profile was added. |
| `POST /api/v1/review/<id>/resolve` | Ambiguous match: `{"entry_id": <candidate>}` to merge or `{"entry_id": null}` for a new payment. Unpaired transfer or failed post: `{"post": true}` to post as it is. |

Limits: 120 requests a minute with a token, 20 without, 256 KiB per request.

## How an SMS becomes a transaction

1. Anything holding an OTP, PIN, CVV, password or code is dropped in memory; only a per-sender daily count is kept.
2. The message is stored as received. The same message arriving twice is stored once.
3. The bank's profile (`bridge/ingest/profiles/*.yaml`) parses it. No profile or no match → review queue.
4. The last four digits pick the Firefly account. No match → review queue.
5. Reconciliation: same reference → same payment; else same account, amount and direction within 30 minutes → same payment (a second message of the *same* type is a second payment); more than one candidate → review. A debit and credit on two own accounts with one reference become one transfer; card bill payments become a transfer to the card.
6. After a 10-minute settle window the payment is posted to Firefly with an `external_id` and the ids of its raw messages.

Bank profiles are written only from your real, masked SMS. None exist yet.

## Tests

```bash
docker compose run --rm --no-deps -v "$PWD/accounts.example.yaml:/accounts.example.yaml:ro" -e BRIDGE_DB_HOST= -e REDIS_URL= bridge pytest -q
```

The tests use a fake Firefly and a fictional "Test Bank" profile, and need no running stack.

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
