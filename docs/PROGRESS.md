# Progress

Update this file at the start and end of every milestone. It is how a new session knows where things stand.

## Now
- Approved milestone: M2 (approved 2026-11-12)
- Status: M2 pipeline built and tested; bank profiles not written yet (waiting for samples, rule 9). Not committed.
- Next step: owner sends masked SMS samples (ICICI bank and Axis card first) and installs the forwarder on the phone. Then: write one profile per bank and card, with the samples as fixtures.

## Milestones
| ID | Scope | Status | Approved on | Finished on |
| --- | --- | --- | --- | --- |
| M1 | Docker stack, Firefly, bridge skeleton, accounts | Finished | 2026-11-12 | 2026-11-12 |
| M2 | SMS ingestion, OTP filter, profiles, reconciliation | In progress | 2026-11-12 | |
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
- ~~Register in Firefly and create a Personal Access Token~~ Done 2026-11-12. Firefly 6.7.9 needed its personal access client created by hand (`php artisan passport:client --personal`); the token page is under the user menu → OAuth (`/profile/oauth`), not the profile tabs.
- ~~Firefly's first-run screen created three accounts~~ Deleted 2026-11-12 at the owner's request (ICICI with a ₹500 opening balance, ICICI savings account, Cash wallet). Firefly now has no accounts and no transactions.
- ~~Write `accounts.yaml` and run `seed_firefly`~~ Done 2026-11-13: "ICICI Bank" (savings, last4 5000) and "Axis Credit Card" (last4 0000, ₹10,000 outstanding) created. Other banks not listed yet. Firefly's first-run screen had created three accounts again (ICICI ₹5,000, ICICI savings account ₹4,000, Cash wallet; opening balances only); deleted 2026-11-13 at the owner's request.
- The Meteor 350 loan stays `status: planned` until disbursed.

### Small differences from the plan
- `bridge/requirements.txt` and `requirements-dev.txt` hold dependencies; `pyproject.toml` holds only pytest settings.
- Added `scripts/init-env.sh` to generate `.env` secrets.
- The skills `/drift-review` and `/milestone finish` are not installed, so the rule check was done by hand.

## M2 plan (presented and approved 2026-11-12)

### Inputs checked
- SMS forwarder for until Phase 2: "Incoming SMS to URL forwarder" (github.com/bogkonstantin/android_income_sms_gateway_webhook), MIT, v2.4.0 (June 2026), on F-Droid. Posts JSON `{from, text, sentStamp, receivedStamp, sim}` (stamps in epoch ms), custom headers, optional HMAC-SHA-256 `X-Signature`, retries with backoff, keeps failed messages for re-send, can exclude text by regex on the phone. SMS only: RCS messages are not forwarded.
- Not chosen: capcom6/android-sms-gateway (Apache-2.0, very active) also sends SMS, which this project never needs.
- No new Python dependency.

### Scope
- `POST /api/v1/ingest/sms`: bearer token plus HMAC `X-Signature` check. Fixed order:
  1. OTP / PIN / CVV / password filter, in memory. A match returns 200 `{"status":"dropped"}` so the phone stops retrying; nothing stored, logged or queued.
  2. Store the raw message. A SHA-256 of sender + body makes re-delivery idempotent.
  3. Parse with the profile for that sender (by DLT header, e.g. the `HDFCBK` in `VM-HDFCBK`).
  4. Map bank + last4 to a Firefly account. Unknown account → review.
  5. Reconcile, then post to Firefly from a Celery task whose only argument is a row id.
- Per-bank profiles as YAML files (`hdfc`, `sbi`, `icici`, `hsbc`, `axis`, plus one per card), each pattern with named groups and a test fixture. Written only from the owner's masked samples.
- Parsed fields: amount (paise), debit/credit, channel (UPI, IMPS, NEFT, NACH, card, ATM, other), account last4, counterparty or VPA, reference, time, available balance if present.
- Messages that are not transactions (failed payments, mandate notices, due reminders, promos) are kept with status `ignored` and a reason.
- Reconciliation, in this order:
  1. Same UPI / IMPS / NEFT reference → same payment.
  2. Same account, amount and direction within a time window → same payment, if exactly one candidate.
  3. More than one candidate → review queue.
- Own-account transfers: a debit on one own account and a credit on another, matched by reference or by amount and time → one Firefly transfer, not an expense plus income.
- Card bill payments: bank-side debit to a card + card-side "payment received" → one transfer to the card account.
- Firefly posting: withdrawal, deposit or transfer with a decimal-string amount, an `external_id`, a link to the raw message, and Firefly's duplicate-hash check on.
- Balances: an SMS "available balance" is stored as a confirmed balance with its time. `/api/v1/accounts` then reports `confirmed` (recent), `stale` (old) or `calculated` (none).
- Review queue API: `GET /api/v1/review`, and actions to ignore, re-parse after a profile is added, or resolve an ambiguous match.
- Tests: every profile against its fixtures, OTP filter, idempotent re-delivery, reference and time-window dedup, ambiguous match to review, own transfer, card bill payment, refund, reversal, failed payment, unknown sender, unknown account.

### File layout
```
bridge/ingest/
  models.py        # RawMessage, ParsedTransaction, LedgerEntry, BalanceObservation, ReviewItem
  otp.py           # in-memory drop filter
  profiles/        # one YAML per bank or card
  parser.py        # loads profiles, returns a parsed transaction or a reason
  accounts.py      # bank + last4 -> Firefly account id
  reconcile.py
  tasks.py         # post_to_firefly(row_id)
  views.py         # ingest and review endpoints
bridge/tests/ingest/fixtures/<bank>/*.yaml   # owner's masked samples
docs/sms-forwarder.md                        # phone setup
```

### Left out of M2
- `/ingest/email`, Gmail, PDFs and CSV import (M3). LLM fallback for unparsed messages (M4).

### Blockers before M2 code
- Masked SMS samples from the owner (rule 9).
- Real accounts seeded into Firefly (needed to map last4 to accounts).
- How the phone reaches the bridge, which listens only on 127.0.0.1 today.

## M2 result so far (2026-11-12)

### Done and checked
- `POST /api/v1/ingest/sms` (bearer token + HMAC `X-Signature`), review queue API, `bank_balance` and confirmed/stale/calculated on `/api/v1/accounts`.
- OTP/PIN/CVV/password filter in memory before storage; drops counted per sender per day (`DropTally`), content never kept.
- YAML bank profiles with validation (card profiles may not capture a balance). `bridge/ingest/profiles/` is empty: no real bank format has been written.
- Reconciliation: reference, then account + amount + 30-minute window, then transfers between own accounts; ambiguous → review; 10-minute settle window before posting; reversals cancel an unposted debit.
- Celery: `process_raw(id)` and `post_entry(id)` take ids only; `sweep` runs every minute from beat.
- 210 tests pass (pipeline + 26 real-profile fixtures), using a fictional "Test Bank" and "Test Card" (`bridge/tests/ingest/profiles/`, clearly marked as not real formats).
- Live run on a throwaway Firefly 6.7.9 with test profiles: OTP dropped and absent from the bridge database and logs; re-delivery stored once; a UPI debit posted once; an own transfer posted as one transfer; a card spend reported by two messages posted once; a card bill payment posted as a transfer to the card; an unknown sender went to review; Firefly's balances, spend (₹1,749.50) and net worth (₹8,250.50) matched hand calculation; the bank-reported balance matched Firefly's. Throwaway instance deleted.
- Phone setup guide: docs/sms-forwarder.md.

### Profiles from the owner's samples (2026-11-13)
| Profile | Patterns | Sender ID |
| --- | --- | --- |
| hdfc | UPI credit; average balance notice (ignored, not recorded as a balance) | HDFCBK (JM-HDFCBK-S) |
| hsbc | "is paid from HSBC account" debit; UPI credit | HSBCIN (JM-HSBCIN-S) |
| axis-card | spend (with time); payment received (card side of a bill payment); statement generated, bill due reminder, declined (all ignored); OTP sample confirmed dropped | AXISBK (JD-AXISBK-S) |
| sbi | UPI debit; UPI mandate created / cancelled (ignored); MPIN OTP confirmed dropped | SBIUPI (JX-SBIUPI-S) |
| icici | UPI debit; IMPS credit; informational notice (ignored). Shows only 3 account digits | ICICIT (AX-ICICIT-S) |
| sbi-card | spend; recurring e-mandate debit (with time); credit limit alert (ignored, limit never read as balance) | SBICRD (JD-SBICRD-S) |

Fixtures in `bridge/tests/ingest/fixtures/`, masked again (digits, UPI IDs, references, links and the OTP code changed). Real sender IDs set 2026-11-13. Accounts shown with only three digits (ICICI) match Firefly accounts whose last four end with them; two such accounts → review. Tata Neu (TNBPAY) SBI Card reminders are not forwarded. AXISBK may also carry Axis bank-account SMS; those patterns would go in the same profile.

Added with these samples:
- Parser reads a `time` group (Axis spends carry HH:MM:SS).
- `BRIDGE_OWN_VPAS` in `.env`: money to or from the owner's own UPI IDs is an own transfer (waits for its other half; unpaired → review), never income or spend. Two IDs from the samples are set.

### Not done
- More samples still useful: a bank-side card bill payment (e.g. SBI or ICICI paying the Axis or SBI card), SBI and HDFC credits, an HDFC debit, a refund, a failed payment, a balance alert.
- Firefly accounts (owner will add all accounts when the build is finished; until then SMS for missing accounts go to review as `unknown_account` and can be re-parsed): the samples show HDFC XX1151, HSBC XX9006, SBI X3727, ICICI XX378 (last 3 only), Axis cards XX1233 and XX9315, and SBI Card 5173, but Firefly has ICICI Bank (5000, which does not end in 378) and one Axis card as 0000. HDFC, HSBC and the second Axis card need adding with 2026-11-01 balances, and the Axis card's last4 needs correcting.
- Phone setup: reachability decided (home Wi-Fi, bridge on 192.168.0.106:8000, checked from the LAN address 2026-11-13). Sender IDs still come from the samples.
- Tests with the owner's real samples (SPEC: unit tests for every bank profile).

### Design notes
- The OTP filter keeps alerts that only warn "never share your OTP/PIN", unless a code-like number sits within 15 characters of the keyword. When unsure it drops; the daily count shows if real alerts are being lost.
- Two same-amount payments on different own accounts with different references are not treated as a transfer. Pairing without a shared reference happens only when a profile marks the message as a card payment or own transfer.
- A transfer half that arrives after the other half was already posted goes to review as `transfer_already_posted`; Firefly is not edited automatically.
- Raw message bodies are stored unencrypted in the bridge database (OTP messages never are). Revisit in M7 with disk encryption and backups.

## Open questions for the owner
- How many accounts at each bank (HDFC, SBI, ICICI, HSBC, AXIS), and savings, salary or current?
- Which AXIS and ICICI credit card products?
- Has the Meteor 350 bike loan been disbursed? Who is the lender, and which account will the EMI be debited from? Until disbursal it is recorded as planned, with no balance in Firefly.
- Investments held, if any?
- Which Android phone and Android version? (Needed for the SMS forwarder in M2.)
- Is the Axis card's last4 really 0000? Card SMS are matched to the account by these digits.

## Known limitations
- The kit's `.claude/skills` folder (milestone, spec-check, drift-review) is not in the project folder, so those slash commands do not work yet.
- AI categoriser (for M4): only a `latest` image; keeps the Firefly token and LLM key in its own data volume rather than `.env`; sends transaction descriptions to the LLM unmasked; only categorises withdrawals.
- Oracle Always Free sign-up from India often fails at card verification or ARM capacity (for M7).
- A Google OAuth app in "testing" mode expires its refresh token every 7 days (for M3).
