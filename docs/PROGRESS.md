# Progress

Update this file at the start and end of every milestone. It is how a new session knows where things stand.

## Now
- Approved milestone: M1 (approved 2026-11-12, with health and accounts endpoints)
- Status: M1 built and tested; waiting for the owner's review and the owner-only steps below
- Next step: owner reviews M1, does the steps under "M1 result", then says whether M1 is finished. Not committed to git yet.

## Milestones
| ID | Scope | Status | Approved on | Finished on |
| --- | --- | --- | --- | --- |
| M1 | Docker stack, Firefly, bridge skeleton, accounts | Built, awaiting owner review | 2026-11-12 | |
| M2 | SMS ingestion, OTP filter, profiles, reconciliation | Not started | | |
| M3 | Gmail alerts, statement PDFs | Not started | | |
| M4 | AI categoriser, LLM fallback | Not started | | |
| M5 | Goals, EMI, net worth, CAS, credit report | Not started | | |
| M6 | Telegram advisor | Not started | | |
| M7 | Deployment, backups, HTTPS | Not started | | |
| P2 | Android APK | Not approved | | |

## M1 plan (presented 2026-11-12)

### Repo check done before planning (2026-11-12)
| Repo | Licence | State | Use |
| --- | --- | --- | --- |
| firefly-iii | AGPL-3.0 | v6.7.9, active | Unmodified Docker image, REST API |
| data-importer | AGPL-3.0 | v2.3.5, active | Added in M3, stable release only |
| FireflyIII-AI-Categorizer | AGPL-3.0 | 24 stars, last commit 2026-10-18, no tagged releases | M4, pinned by image digest, internal network only |
| pckt | GPL-3.0 | v1.0.1, 10 stars | Reference only |
| indian-bank-sms-parser | MIT | 1 star, no release | Reference only (rule 10: no code copied, MIT or not) |

### Scope
- Docker Compose services: Firefly III, Firefly daily cron, PostgreSQL, Redis, bridge (Django REST + gunicorn), Celery worker, Celery beat.
- PostgreSQL init script creates two databases and two roles (Firefly, bridge).
- One internal Docker network. Only Firefly and the bridge publish ports, bound to 127.0.0.1.
- Firefly configured with `DB_CONNECTION=pgsql`, INR as primary currency, timezone Asia/Kolkata. Check lakh/crore grouping under `en_IN` and report the result.
- Bridge endpoints, both token-authenticated and read-only:
  - `GET /api/v1/health`
  - `GET /api/v1/accounts` (required by SPEC.md M1; the first plan listed health only)
- Bridge code: Firefly API client, paise-to-decimal-string money helpers (no floats).
- `seed_firefly` management command reads a gitignored `accounts.yaml` and creates accounts through the Firefly API; safe to re-run.
- Tests: money conversion and rounding, token auth, Firefly client against mocked responses, seed idempotency, accounts endpoint.
- Short README covering setup and the one manual step.

### File layout
```
docker-compose.yml
.env.example              # .env is gitignored
.gitignore
README.md
postgres/init/01-create-databases.sh
accounts.example.yaml     # owner copies to accounts.yaml and fills in locally
bridge/
  Dockerfile
  pyproject.toml
  manage.py
  config/                 # settings, urls, celery
  core/                   # money helpers, token auth, health view
  firefly/                # API client, accounts view, seed_firefly command
  tests/
```

### Agreed with the owner (2026-11-12)
- Credit cards (AXIS, ICICI) are Firefly asset accounts with the credit-card role. Balance is negative, bill payments are transfers, net worth is unaffected by the choice.
- Opening balances are taken as of 2026-11-01.
- `git init` in the project root; one reviewable commit per milestone.
- This Mac is the development machine. Deployment waits for M7.
- Full account and card numbers are never pasted in chat; last-4 goes in the local `accounts.yaml`.

### Left out of M1 on purpose
- Reverse proxy with HTTPS: listed in the SPEC.md architecture, built in M7. Local ports are bound to 127.0.0.1 until then.
- data-importer (M3), AI categoriser and any LLM container (M4).
- Ingestion endpoints (M2).

### Manual step the owner must do
- Register in the Firefly UI and create a Personal Access Token, then put it in `.env`. Firefly has no way to automate this.

## M1 result (2026-11-12)

### Done and checked
- Stack runs on this Mac: firefly (healthy), firefly-cron, postgres, redis, bridge, worker, beat. Ports bound to 127.0.0.1 only.
- Two databases, two roles. Checked: each role is refused a connection to the other's database.
- Bridge: `GET /api/v1/health` and `GET /api/v1/accounts`, bearer-token auth, read-only, rate and size limits.
- 91 tests pass (money, auth, Firefly client, views, seed).
- `seed_firefly` was run twice against a separate throwaway Firefly 6.7.9 with made-up accounts: created a savings account, a salary account, a card and an active loan; skipped a planned loan; second run created nothing. INR became primary. Firefly's net worth matched assets minus liabilities. The throwaway instance was deleted afterwards.
- That run found one bug the mocked tests missed (Firefly rejects a POST with no Content-Type). Fixed, and the fake now behaves the same way.
- `en_IN` locale gives lakh/crore grouping in the Firefly image (₹1,23,45,678.90).

### Not done: needs the owner
- Register in Firefly at http://localhost:8080 and create a Personal Access Token; put it in `.env`.
- Write `accounts.yaml` with the real accounts and run `seed_firefly`. No real account, card or loan exists in Firefly yet.
- The Meteor 350 loan stays `status: planned` until disbursed.

### Small differences from the plan
- `bridge/requirements.txt` and `requirements-dev.txt` hold dependencies; `pyproject.toml` holds only pytest settings.
- Added `scripts/init-env.sh` to generate `.env` secrets.
- The skills `/drift-review` and `/milestone finish` are not installed, so the rule check was done by hand.

## Open questions for the owner
- How many accounts at each bank (HDFC, SBI, ICICI, HSBC, AXIS), and savings, salary or current?
- Which AXIS and ICICI credit card products?
- Has the Meteor 350 bike loan been disbursed? Who is the lender, and which account will the EMI be debited from? Until disbursal it is recorded as planned, with no balance in Firefly.
- Investments held, if any?
- Which Android phone and Android version? (Needed for the SMS forwarder in M2.)

## Known limitations
- The kit's `.claude/skills` folder (milestone, spec-check, drift-review) is not in the project folder, so those slash commands do not work yet.
- AI categoriser (for M4): only a `latest` image; keeps the Firefly token and LLM key in its own data volume rather than `.env`; sends transaction descriptions to the LLM unmasked; only categorises withdrawals.
- Oracle Always Free sign-up from India often fails at card verification or ARM capacity (for M7).
- A Google OAuth app in "testing" mode expires its refresh token every 7 days (for M3).
