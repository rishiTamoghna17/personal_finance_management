# Progress

Update this file at the start and end of every milestone. It is how a new session knows where things stand.

## Now
- M6 finished 2026-11-14; M7 finished 2026-11-20. Oracle remains on the owner's limited/free tier; no paid upgrade was made. Backups go to Google Drive. P2 (Kotlin/Jetpack Compose) and the feedback-learning spec change were approved 2026-11-20; implementation is in progress.
- M7 close checks (2026-11-20): all Compose services running; Django system check passes; sweep, Gmail and statement heartbeats current; two Gmail accounts enabled; SMS, email and PDF messages arrived in the last 24 hours. Owner confirmed the advisor page works on the phone over Tailscale; SMS records are arriving and the latest is parsed. The alert builder produced six category questions and three Google reconnect alerts. Latest encrypted Drive backup: `3041c41b` (2026-11-20 13:49 UTC). Restore drill on Oracle passed: live/restored bridge counts 126 messages and 38 entries; Firefly 31 journals and 32 accounts; 133 bridge files restored. Temporary drill resources were removed.
- Security drift review: bridge, Firefly and both Nginx UIs bind host ports only to `127.0.0.1`; the AI Docker network reports `internal: true`; `.env` is gitignored and account/goal/secret files are not tracked; OTP filtering precedes storage/logging/queueing; raw message bodies are encrypted at rest; Celery ingestion tasks take row IDs; advisor is read-only. Tailscale Serve provides private HTTPS to bridge, advisor and Firefly. SSH remains restricted by the OCI ingress rule to the owner's home IP; keep it that way and keep application ports closed publicly.
- Follow-up, not an M7 deployment blocker: 29 review items remain open (16 unparsed, 7 post failures, 6 category questions, 1 unpaired transfer, 1 unknown sender). Do not dismiss or resolve them without the owner's review. Opening balances and payee categorization are also owner data tasks. The app's push notifications and native SMS handling belong to P2.
- P2 implementation started (2026-11-20): added authenticated feedback labels linked to encrypted raw messages, label correction with explicit review reopening, and masked same-sender examples for local Ollama fallback.
- P2.2 implementation (2026-11-20): Compose app now has Home, Activity, Plans, Ask and Review tabs, HTTPS bridge configuration with encrypted credential storage, and an authenticated read-only Firefly transaction-list endpoint. Code is pushed at `c03b22a` and deployed to Oracle. Django system check passed; live `GET /api/v1/transactions` returned HTTP 200 and a valid paginated response. Python modules pass syntax compilation; Android debug APK compiles successfully using the Docker builder. Phone installation/flow verification is still pending; no test suite was run. APK: `android-app/dist/my-finance-p2.2-debug.apk` (gitignored build artifact), application id `com.tamoghna.myfinance`, min SDK 28, target SDK 36.
- P2.3 category review UI (2026-11-20): Review now loads the existing `category_needed` alerts, displays payment details and suggestions, allows choosing a Firefly category, and optionally requests a payee rule through the existing category endpoint. Category records/rules are unchanged until the owner taps Save. Android debug APK compiles; no test suite was run. APK: `android-app/dist/my-finance-p2.3-debug.apk` (gitignored build artifact). This stage still needs installation and owner phone/API flow verification; remaining P2.3 feedback-learning and correction work is tracked below.
- P2.3.1 phone UI fixes (2026-11-20): Removed the Home account-list cap (server has 11 active accounts, including four credit cards), added a same-server-validated **Reconnect Google** button for existing one-time links, and made request timeouts explain the Tailscale/Refresh step. Review and alerts endpoints responded successfully in under one second from the Oracle bridge container; the owner's phone timeout could not be reproduced there. Android debug APK compiles; phone verification is still pending. No ledger/bridge data changed and no tests were run.
- P2.3.2 wallet card presentation (2026-11-20): Home separates four credit cards into a layered, tappable stack with bank-colored faces; tapping cycles the front card. Non-card accounts remain listed individually. The visual preview uses sample data, and the Android debug APK compiles. Phone verification is pending; no ledger/bridge data changed and no tests were run.
- P2.3.3 system theme (2026-11-20): Compose now selects accessible light or dark Material colors from Android's system night mode and updates status/navigation bar icon contrast. No manual override or extra dependency was added. Android debug APK compiled and uploaded to the existing Drive APK folder; phone verification is pending. APK: https://drive.google.com/file/d/1s68Xr9qLRiyL1Xb6Kc6sFJeHkTYXdgIE/view?usp=drivesdk
- P2.3.4 card-stack swipe (2026-11-20): Replaced the front card's edge-tap cycle with left/right horizontal swipes and an on-card position hint. No data/API/dependency changes. Android debug APK compiled and uploaded; phone verification is pending. APK: https://drive.google.com/file/d/1rlYPaKqGwf1MGRcfGuXgCOp8-GZwT0Px/view?usp=drivesdk
- P2 Google reconnect consolidation (2026-11-20): Owner confirmed Drive backups and Gmail acct1 use the same Google identity. Gmail acct1's `gmail.readonly` and Drive's `drive.file` scopes now renew in one consent flow. Root cause of failed Drive reconnect was `/backup-secrets` being root-owned while the bridge runs as UID 10001; a one-shot Compose initializer now sets the directory to owner-only mode for the bridge, and a write/remove check passed. Deployed to Oracle; Django system check passed and all services are running. A single combined Gmail acct1 + Drive reminder and one-time link are ready; owner consent on the phone is still required. No ledger data changed.
- Owner says current transaction/category data is for testing and intends to clear it after the app is built and start fresh. Preserve it during development; no data has been cleared. Before the future reset, confirm backup/export needs and explicitly verify which ledger and bridge records to purge.
- Remaining P2 work: install on the phone and verify user flows; finish feedback-learning/correction UX and learning-quality review; SMS permissions and on-device OTP filtering; offline queue/retry/dedupe; notifications; biometrics; signed release.

## Milestones
| ID | Scope | Status | Approved on | Finished on |
| --- | --- | --- | --- | --- |
| M1 | Docker stack, Firefly, bridge skeleton, accounts | Finished | 2026-11-12 | 2026-11-12 |
| M2 | SMS ingestion, OTP filter, profiles, reconciliation | Finished | 2026-11-12 | 2026-11-13 |
| M3 | Gmail alerts, statement PDFs | Finished | 2026-11-13 | 2026-11-13 |
| M4 | AI categoriser, LLM fallback | Finished | 2026-11-13 | 2026-11-14 |
| M5 | Goals, EMI, net worth, CAS, credit report | Finished (Experian reader left out) | 2026-11-14 | 2026-11-14 |
| M6 | Advisor API (chat, digest, alerts) + temporary test chat | Finished | 2026-11-14 | 2026-11-14 |
| M7 | Deployment, backups, HTTPS | Finished | 2026-11-14 | 2026-11-20 |
| P2 | Kotlin Android APK and feedback learning | In progress | 2026-11-20 | |

## P2 plan (approved 2026-11-20; implementation in progress)

**Status:** approved for implementation in Kotlin with Jetpack Compose. M7 is closed. Keep the account on its limited/free tier and do not add paid services.

### Goal and scope
- Build a personal, sideloaded Android APK that connects to the existing Oracle-hosted, versioned `/api/v1/` bridge over the owner's private Tailscale network. The Oracle account stays limited/free; do not add paid hosting or enable billing.
- Screens: finance dashboard; transactions and review queue; goals; net worth; advisor chat; category questions for uncategorized payments. Reuse Firefly and bridge data rather than rebuilding ledger, budgets or reports in the app.
- **Local feedback learning:** when an SMS/email cannot be parsed by an existing profile, let the owner correct its type (for example transaction alert, promotion, card bill payment, failed payment, reversal/refund, reminder, or other) and any structured fields. Save the label against the already encrypted raw-message record, not a second plaintext copy; if a normalized example is needed for later matching, mask account/card numbers, names, VPAs, references and amounts before saving it, and encrypt it at rest. OTP/PIN/CVV/password messages are filtered before this flow and never become examples. Apply learned examples only to later ambiguous/unparsed messages, with the current local Ollama model on the internal-only network. Existing bank profiles remain first; the model suggests a type, while deterministic parsing and reconciliation validate amounts/accounts and decide ledger posting. Low-confidence cases remain in review. Promotions receive an explicit ignored reason, never silent deletion. Owner feedback on a transaction's Firefly category remains the separate existing category-learning path.
- **Transaction analysis:** use the structured Firefly ledger and existing advisor fact tools for totals and trends; do not train on or ask the model to calculate authoritative balances. Any future fine-tuning of model weights is outside this proposal and requires a separate cost/resource and privacy review. Initial feedback learning must add no paid service and no training dependency.
- Notifications: weekly digest, alerts, Google reconnect reminders, and a notification for each `category_needed` item with category choices. A category action submits the existing `POST /api/v1/review/<id>/category` route; allow “use this category for this payee” only where the API supports it. Keep money and payee details out of lock-screen notification text; fetch details after the owner opens the app.
- Replace the temporary SMS-forwarder workflow only after the APK's on-device SMS permission, OTP/PIN/CVV/password filtering, encrypted local queue, retry and duplicate handling are verified. OTP-like messages must be discarded on-device before they are stored, logged, queued or sent. Preserve read-only behavior and never add a payment, transfer or mandate action.
- Protect app access with biometric lock and store the bridge credential using Android Keystore. Use Tailscale for private connectivity; do not expose API or UI ports publicly.

### Proposed work stages and exit checks
1. **P2.1 — App foundation:** select Kotlin/Compose (or owner-selected Flutter), create app shell, secure configuration and API client. Verify authenticated requests to `/api/v1/health` over Tailscale; handle disconnected/offline state without exposing credentials.
2. **P2.2 — Dashboard and finance views:** dashboard, transactions, goals, net worth and advisor chat using existing read-only APIs. Check INR/paise rendering, empty/stale data, API errors and responsive phone layouts.
3. **P2.3 — Review and feedback learning:** list open reviews; show `category_needed` details and category choices; submit a choice and refresh state. For unparsed messages, add the owner correction flow for message type and checked fields, store only the masked/encrypted learning record, and retrieve a few relevant examples locally for future ambiguous messages. Regex/profile parsing stays first, LLM use stays restricted to messages profiles cannot parse, and no model suggestion alone may post a ledger transaction. Add a review fallback and a way to correct prior labels.
4. **P2.4 — Notifications:** deliver digest, alerts, reconnect links and category questions. Prefer Firebase Cloud Messaging if it can be configured without paid services; its Cloud Messaging product is listed as no-cost, but any setup requiring billing or a paid product must be brought to the owner first. Use generic notification text and require an authenticated in-app fetch for financial details. Verify tap-through and expired/single-use reconnect links.
5. **P2.5 — Device SMS and release:** request only required Android permissions; filter secrets on-device before persistence; test offline queue, retry, duplicate delivery and app restart; sideload a signed APK. Verify end-to-end SMS ingestion, review, notifications and biometric lock on the owner's phone before retiring the existing SMS forwarder.
6. **P2.6 — Learning quality and privacy check:** evaluate against a held-out set of owner-labelled, masked samples covering transactions, promotions, card payments, reversals/refunds and failed payments. Report per-type precision/recall and the confusion cases; keep automatic treatment limited to validated, high-confidence non-ledger classifications. Confirm examples contain no OTPs or unmasked financial identifiers, are encrypted/backed up, and can be corrected or deleted. Ask for real masked bank samples where profile coverage is missing; never invent formats.

### P2 acceptance checklist
- Dashboard, transactions, goals, net worth and advisor chat load from the Oracle bridge over Tailscale.
- Category-needed notifications ask the owner to categorize an uncategorized payment; chosen category is reflected in Firefly and the app.
- Correcting an unparsed message improves later local classification through masked/encrypted examples; regression evaluation shows the labeled classes and identifies uncertain cases that still require review.
- Message classification never invents a balance or authoritatively determines amount/account; ledger entries still require the deterministic parser/reconciliation and existing duplicate protections.
- Digest, health/reconnect alerts and notification tap-through work without exposing finance details on the lock screen.
- Secret-bearing SMS is dropped locally before any storage/logging/queue/network step; ordinary SMS is queued offline and delivered once connectivity returns.
- Authentication material is protected by Android Keystore; biometric lock works; no payment/transfer/mandate capability exists.
- APK is sideloadable, documented and verified without adding paid cloud costs or making the Oracle app ports public.

**Approval:** owner replied `change the spec; approved, Kotlin` on 2026-11-20. P2 is active.

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
- ~~Write `accounts.yaml` and run `seed_firefly`~~ Done 2026-11-13, then extended the same day to all accounts (ICICI, HDFC, HSBC, SBI, Cash, Axis and Axis Amex cards, SBI SimplyCLICK and SBI NEO cards; bike loan planned). Digits live only in the gitignored `accounts.yaml`. The seed now also handles renames (matches by digits) and corrects digits and opening balances. Earlier: "ICICI Bank" (savings, last4 5000) and "Axis Credit Card" (last4 0000, ₹10,000 outstanding) created. Other banks not listed yet. Firefly's first-run screen had created three accounts again (ICICI ₹5,000, ICICI savings account ₹4,000, Cash wallet; opening balances only); deleted 2026-11-13 at the owner's request.
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

## M2 result (finished 2026-11-13)

### Done and checked
- `POST /api/v1/ingest/sms` (bearer token + HMAC `X-Signature`), review queue API, `bank_balance` and confirmed/stale/calculated on `/api/v1/accounts`.
- OTP/PIN/CVV/password filter in memory before storage; drops counted per sender per day (`DropTally`), content never kept.
- YAML bank profiles with validation (card profiles may not capture a balance). `bridge/ingest/profiles/` is empty: no real bank format has been written.
- Reconciliation: reference, then account + amount + 30-minute window, then transfers between own accounts; ambiguous → review; 10-minute settle window before posting; reversals cancel an unposted debit.
- Celery: `process_raw(id)` and `post_entry(id)` take ids only; `sweep` runs every minute from beat.
- 275 tests pass (pipeline + 86 real-profile fixtures, every real pattern covered), using a fictional "Test Bank" and "Test Card" (`bridge/tests/ingest/profiles/`, clearly marked as not real formats).
- Live run on a throwaway Firefly 6.7.9 with test profiles: OTP dropped and absent from the bridge database and logs; re-delivery stored once; a UPI debit posted once; an own transfer posted as one transfer; a card spend reported by two messages posted once; a card bill payment posted as a transfer to the card; an unknown sender went to review; Firefly's balances, spend (₹1,749.50) and net worth (₹8,250.50) matched hand calculation; the bank-reported balance matched Firefly's. Throwaway instance deleted.
- Phone setup guide: docs/sms-forwarder.md.

### Profiles from the owner's samples (2026-11-13)
Built from screenshots and from the owner's full SMS backup (19,922 SMS; analysed locally, never copied into the project).

| Profile | Senders | Reads |
| --- | --- | --- |
| hdfc | HDFCBK, HDFCBN | UPI sent, UPI credit; notices ignored |
| hsbc | HSBCIN | paid from account, UPI credit, account credit with balance (no year in date); AutoPay notices ignored |
| icici | ICICIT | UPI debit, IMPS credit, NEFT/other credit with balance, UPI reversal; "unable to confirm" goes to review on purpose |
| axis-card | AXISBK | spend (two wordings, with time), payment received; notices ignored |
| sbi | SBIUPI, SBIPSG, ATMSBI, CBSSBI, SBIINB | UPI debit and credit, IMPS credit, ATM withdrawal, NACH credit, net-banking payment to SBI Card; mandate/AutoPay notices ignored |
| sbi-card | SBICRD, MYSBIC | spend, spend via UPI, e-mandate debit (two wordings), payment received/processed (no card digits: with two SBI cards these go to review); promotions and notices ignored |
| federal (not forwarded: owner no longer uses Federal Bank) | FEDBNK, FEDFIB | UPI debit/sent/debited, mandate and debit-card e-mandate debits, Fi NEFT credit, spend, ATM, interest, sent, received |

Backup check, bank senders only: 1,530 SMS become transactions, 287 ignored with a reason, 411 dropped as OTP/PIN (all checked by shape: no transaction among them), 208 still unread (account-opening, KYC, promotions and similar one-offs; live, these go to review). No parsed date was more than 3 days from the SMS date and no amount was zero.

Every pattern has a masked fixture (`bridge/tests/ingest/fixtures/`); a test enforces it.

### Not done
- More samples still useful: a bank-side card bill payment (e.g. SBI or ICICI paying the Axis or SBI card), SBI and HDFC credits, an HDFC debit, a refund, a failed payment, a balance alert.
- Opening balances: owner is filling them in `accounts.yaml` (Cash and one Axis card done); re-run `seed_firefly` after each change.
- Account digits (2026-11-13): bank accounts use the account digits their SMS show (owner's choice; debit-card endings kept as comments in `accounts.yaml`). Checked: every SMS ending (ICICI's three-digit one included) resolves to the right Firefly account, for all four banks and four cards.
- ~~Phone setup~~ Done 2026-11-13: Galaxy S23 FE (Android 16), forwarder 2.4.0 with SMS permission and battery unrestricted; rule imported from a generated file (deleted from phone and Mac afterwards). The app's Test reached the bridge (202, token and HMAC accepted); test messages closed in review. First test failed only because Docker Desktop had stopped; turn on "start at login".
- First live SMS (2026-11-13): owner's ₹1 UPI payment from HSBC arrived via the phone, parsed by hsbc/paid-from-account, matched to HSBC Bank. A live SBI Card survey SMS went to review as unparsed; an ignore pattern was added and the message re-parsed from the review queue.
- Tests with the owner's real samples (SPEC: unit tests for every bank profile).

### Design notes
- The OTP filter keeps alerts that only warn "never share your OTP/PIN", unless a code-like number sits within 15 characters of the keyword. When unsure it drops; the daily count shows if real alerts are being lost.
- Two same-amount payments on different own accounts with different references are not treated as a transfer. Pairing without a shared reference happens only when a profile marks the message as a card payment or own transfer.
- A transfer half that arrives after the other half was already posted goes to review as `transfer_already_posted`; Firefly is not edited automatically.
- Raw message bodies are stored unencrypted in the bridge database (OTP messages never are). Revisit in M7 with disk encryption and backups.

### Closing check (2026-11-13, by hand: /drift-review is not installed)
- Rule 2: endpoints are health, accounts, ingest/sms, review; none moves money.
- Rule 3: OTP filter runs before storage; logs carry ids and sender headers only; Celery tasks take row ids only.
- Rule 4: no float in money code; amounts go to Firefly as decimal strings.
- Rule 10: no code from pckt or indian-bank-sms-parser.
- Secrets: `.env`, `accounts.yaml`, the SMS backup and the phone rule file are not in git.
- Left for the owner, not code: opening balances in `accounts.yaml`.

## M3 closing check (2026-11-13, by hand: /drift-review is not installed)
- Rule 2: endpoints are health, accounts, ingest/sms, ingest/email, review; none moves money. Gmail access requests only `gmail.readonly`; a write attempt was refused by Google in testing.
- Rule 3: SMS and email secret filters run before storage; logs carry ids and headers only; Celery tasks take ids only. Gmail tokens and statement passwords are stored only encrypted (checked in the database: no plain token or short password value).
- Rule 4: no float in money code.
- Statement PDFs stay locked on disk (checked: all 17 statements need a password; only HSBC's 3 information leaflets are unlocked); they are opened only in memory.
- Found and fixed at closing: SBI Card and ICICI put a full card number or long customer ID in the PDF file name; file names are now masked to the last 4 digits when recorded, and the 11 existing records and files were renamed.
- Secrets in git: none (`.env`, `accounts.yaml`, `secrets/`, client files, PDFs, mail cache all ignored).
- Left for the owner: opening balances. Left for later: comparing statement closing balances with Firefly once balances are set; parsers for HSBC's first statement and the Axis EMI letter.

## M3 plan (presented and approved 2026-11-13)

### Goal
Bank alert emails and monthly statement PDFs feed the same pipeline as SMS, so one real payment is still one transaction (rule 6), and statements confirm balances and catch anything SMS missed.

### A. Gmail alert emails
- A Celery beat task every 10 minutes reads new mail from bank senders only (a Gmail search on sender addresses), newest first, read-only.
- Each email: subject and text body (HTML turned into text with the standard library), OTP filter in memory first, then stored as a raw message with source `email`, then parsed and reconciled exactly like SMS. An email and an SMS for the same payment merge by reference, or by account, amount and time.
- Email profiles: YAML per bank in `bridge/ingest/profiles/email/`, keyed by sender address. Written only from real emails (rule 9): the first poll sends everything to review as unknown sender, and profiles are written from those, with masked fixtures, the same way as the SMS backup.
- `POST /api/v1/ingest/email` (SPEC) with token and HMAC, same pipeline, for later use.

### B. Statement PDFs
- Statement emails are recognised per bank (sender plus subject). The PDF attachment is saved as received (it is already password-protected), unlocked into a temporary file, read, and the unlocked copy is deleted in a `finally` block.
- Statement passwords: entered once per bank with a management command that prompts for it (never typed in chat or on the command line), encrypted with a key kept only in `.env` (`STATEMENT_KEY`, Fernet), stored encrypted in the bridge database, decrypted only in memory inside the task, never in Celery arguments or logs.
- One Python parser per bank statement layout, written from the owner's real statements, with masked fixtures.
- Each statement line goes through the same reconciliation: already recorded → linked to its statement line; not recorded → new transaction (source `pdf`); same reference but different amount → review.
- The closing balance becomes a confirmed bank balance. If it differs from Firefly's balance for that date, a review item shows the difference.

### C. Tests
- Cross-source dedup: SMS + email + PDF for one payment = one transaction; PDF-only line = one new transaction.
- OTP emails dropped; password never in logs, Celery arguments or the database in plain form; unlocked PDF deleted after success and after failure.
- Every email profile and statement parser against masked fixtures.

### New dependencies (checked 2026-11-13; all free)
| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| google-api-python-client | 2.202.0 | Apache-2.0 | Gmail API |
| google-auth-oauthlib | 1.5.0 | Apache-2.0 | one-time Google sign-in |
| pikepdf | 10.18.1 | MPL-2.0 | unlock password-protected PDFs |
| pdfplumber | 0.11.10 | MIT | read text and tables from PDFs |
| cryptography | current | Apache-2.0 / BSD | encrypt statement passwords and the Gmail token |

### File layout
```
bridge/mail/            # Gmail client, poll task, email-to-text
bridge/statements/      # password store, unlock, parsers/<bank>.py, reconciliation
bridge/ingest/profiles/email/*.yaml
bridge/tests/mail/, bridge/tests/statements/ (+ masked fixtures)
docs/gmail-setup.md     # owner's one-time Google setup
```

### Left out of M3
- CSV import and the Firefly data-importer: the data-importer writes straight into Firefly and would bypass the bridge's dedup, so the same payment could be counted twice (rule 6). Proposed: skip, or later add CSV as one more bridge source.
- LLM fallback (M4).

### Owner's answers (2026-11-13)
- Gmail access: Gmail API, read-only. Bank mail arrives in **two** Gmail accounts; both will be connected.
- Statement passwords: the owner knows them; the bank emails state each format. They are typed into the prompt, never sent in chat. Nothing is ever guessed or brute-forced.
- Email formats and statement layouts: learned from a Google Takeout export (.mbox) of a "bank" label in each account, analysed locally like the SMS backup, never committed.
- CSV / data-importer: left out of M3 (agreed).
- Gmail API checked for account 1 (2026-11-13): OAuth client (Desktop app) in `secrets/gmail_client.json` (git-ignored); sign-in granted only `gmail.readonly` and a refresh token; a write attempt was refused (403). The test kept the token in memory only. The `bank` label held only ~64 messages, so it was probably applied to one page of results rather than to every match.
- Still needed: account 2's Google setup (same steps), the two exports, and the owner's "approved" for M3.

### What the two mailboxes contain (analysed 2026-11-13, read-only API, digits masked; cache kept only in the private scratch folder)
Account 1: 2,483 bank/investment emails (3 years). Account 2: 340.

| Source | Transaction alert emails | Statement PDFs | Password rule stated in the email |
| --- | --- | --- | --- |
| HDFC (hdfcbank.bank.in) | Yes, ~114 UPI debit alerts ("Rs.x is debited from your account ending … towards VPA … UPI transaction reference no.") | "Email Account Statement" (no PDF attachment seen) | none seen |
| ICICI (icicibank.com, icici.bank.in) | Yes: transaction alerts, salary/NEFT credits ("payment of Rs … on behalf of <employer>") | Monthly PDF | first letters of the account title + DDMM of birth, lowercase |
| HSBC (notification.hsbc.*) | No | Monthly PDF per customer ID | DOB (DDMMYY) + some digits of the Customer ID |
| Axis cards (axis.bank.in, account 2) | Yes, every card purchase | Monthly PDF per card; EMI letter PDF | first 4 letters of name (CAPS) + DOB DDMM, or + last 4 card digits |
| SBI Card (sbicard.com) | Yes, "Transaction Alert from SBI Card" (~222) | Monthly PDF (SimplyCLICK) | says a new rule is "below", but it is not in the email text (probably an image): owner to confirm |
| Fi / Federal (fi.money) | Yes (credits) | Monthly PDF | first 4 letters of name (CAPS) + DDMM; Federal is no longer used |
| Mutual funds (CAMS, KFintech) | SIP / redemption confirmations | CAS-style PDFs | PAN in capitals |
| NSDL / CDSL | e-voting notices only | AGM / ballot notices (not statements) | n/a |
| Experian / CIBIL | credit-enquiry alerts | Experian credit report PDF | not checked yet |

Investments (found 2026-11-13, account 1, for M5):
- **CDSL CAS** monthly from `cdslstatement.com` ("Consolidated Account Statement across Mutual Funds and Depositories"), every month since 2024: one PDF with all demat stocks and mutual funds, whichever app was used. Password: PAN in capitals (stated in the email). This is the main source for M5 holdings.
- **Groww** (747 emails, 2026): SIP and lump-sum allotments, redemptions, monthly "Transaction and Holding Statement" PDF and "Statement of account of securities" PDF; both open with PAN in capitals.
- Folio statements and SIP confirmations from CAMS and KFintech (PAN in capitals); NSDL sends AGM/e-voting notices only.

Important for the build: the SMS secret filter, applied to emails, flags far too much (733 of 2,483 in account 1), including all ~222 SBI Card transaction alerts and several ICICI transaction alerts and statements, because email footers warn about OTP/PIN next to numbers. M3 needs an email-specific filter (ignore standard disclaimer footers, look for the code itself) tested against these emails before email goes live.

### M3 part A result (2026-11-13): bank alert emails, live
- Both Gmail accounts connected read-only (`gmail_connect`); tokens stored encrypted with `BRIDGE_ENCRYPTION_KEY` (only in `.env`). Beat polls every 10 minutes, only exact bank alert domains from the email profiles; marketing sub-domains are skipped.
- Email-specific secret filter (`contains_secret_email`): on all 2,823 cached emails it flagged every real OTP email (171) and no transaction alert or statement email.
- Email profiles (`bridge/ingest/profiles/email/`): HDFC UPI debit/credit, ICICI e-payment (salary) credit, interest credit, debit-card purchase, SBI Card spend and e-mandate debit, Axis card spend; statements, notices, initiated payments and upcoming mandates ignored with reasons; Axis foreign-currency spends go to review (new `type: review`). On the cache: 393 emails become transactions, none fall to review by accident.
- `POST /api/v1/ingest/email` (token + HMAC). Statement PDFs attached to bank emails are recorded as `StatementAttachment` (pending) for part B.
- First live poll (mail since 2026-11-01): 40 emails, 11 transactions; Firefly now holds 12 transactions (11 from email, 1 from SMS), all withdrawals, ₹2,832.69. One Axis USD spend is in review.
- 320 tests pass. Not committed yet.

### M3 part B result (2026-11-13): statement PDFs
- Passwords: `statement_password setup` asks once per bank in a hidden prompt, tests each password on that bank's downloaded statements and saves it (encrypted) only if it opens them. HSBC, ICICI, Axis and SBI Card saved; all their statements open. (A first version asked twice; the terminal mangled the repeat entry, so it was replaced.) The owner asked to give DOB/card/account numbers in chat instead; refused, since passwords and full numbers are never handled in plain text.
- PDFs are downloaded as sent (still locked) to the `bridge_data` volume and unlocked only in memory (pikepdf to memory, pdfplumber); a test checks no unlocked copy is written.
- Parsers (`bridge/statements/parsers/`), each refusing a statement that does not add up: HSBC and ICICI follow the running balance (page "Total:" / carried-forward lines handled, closing balance checked); SBI Card checks rows against its account summary (undated GST rows read; under Rs 1 rounding allowed); Axis reads rows and the payment summary.
- 13 statements (6 months) parsed. Every line is before 2026-11-01, so nothing new was posted; each closing balance is stored as a confirmed bank balance. Latest: ICICI 30 Sep, HSBC 29 Oct, SBI SimplyCLICK 17 Oct, Axis 13 Oct, Axis Amex 10 Nov.
- Statement lines from the ledger start are matched to SMS/email payments by account, amount, direction and +/-2 days (reference first); unmatched lines become new transactions; ambiguous ones go to review. Hourly beat task processes new statement PDFs from the Gmail poll.
- Not parsed (need a parser later): HSBC's first statement (August, before the ledger start) and the Axis EMI letter (for M5).
- Not done: comparing a statement's closing balance with Firefly's balance on that date (meaningful once opening balances are filled in).
- 334 tests pass.

### Questions for the owner (as asked)
1. Gmail access: Gmail API with read-only permission (recommended: it can only read; needs a free Google Cloud project and a one-time sign-in), or IMAP with an app password (simpler, but that password unlocks the whole mailbox and could also send mail)?
2. Which banks and cards email you monthly statements, and do you know each statement's password format? (Do not send passwords in chat; the command will ask for them.)
3. Do any of your banks send transaction alert emails, or only SMS?
4. OK to leave CSV / data-importer out of M3?

## M4 plan (presented and approved 2026-11-13)

### Checked before planning (2026-11-13)
- FireflyIII-AI-Categorizer: AGPL-3.0, last commit 2026-10-18, 24 stars, no tagged releases (image `latest` only, so it will be pinned by digest). Classifies **withdrawals only**, into the owner's existing Firefly categories, with three outcomes (classified / assumed / needs review) and a Review page; reuses past categories for repeat merchants without calling the LLM. It sends the transaction **description, payee name and amount** (plus past examples) to the LLM, unmasked, and it has no login.
- Our descriptions contain people's names and UPI IDs (e.g. a UPI payment to a person), so a cloud LLM would receive them.
- This Mac: Apple M4, 16 GB RAM, 48 GB free disk. Ollama is not installed. A 7-8B model (about 5 GB) runs comfortably here with the Mac's GPU when Ollama runs natively (not inside Docker).

### Scope
1. **Categories.** A `categories.yaml` (owner-editable) seeded into Firefly by a command: Food & dining, Groceries, Shopping, Transport, Fuel, Bills & utilities, Mobile & internet, Subscriptions, Rent, EMI & loans, Investments (SIP), Insurance, Health, Education, Travel, Entertainment, Family & friends, Cash, Fees & charges, Salary, Interest, Refunds, Other. Deposits the bridge already understands (salary credit, interest, refund) get their category from the bridge when posted; the categoriser handles withdrawals.
2. **Categoriser.** Run FireflyIII-AI-Categorizer in Docker on the internal network; its settings page on `127.0.0.1:3000` only (never the Wi-Fi address, never the internet). A Firefly webhook "transaction stored" → `http://categorizer:3000/webhook`, created by a bridge command. Its own Firefly token (separate, revocable). It points at the chosen LLM. Low-confidence results stay in its Review page (and later Telegram, M6).
3. **LLM fallback parser** (bridge, provider pluggable: `ollama` | `gemini` | `groq`). Only for messages from known bank senders that no profile reads (now in review as "unparsed").
   - Masking before anything is sent, whatever the provider: long numbers (references, phone numbers) and UPI IDs become placeholders (`<REF1>`, `<VPA1>`) that are put back locally after the answer; account/card digits are already masked by the bank (`XX1234`) and stay; for cloud providers, runs of capitalised words that look like names are also replaced.
   - The model returns structured JSON (is it a transaction, amount, debit/credit, account digits, date, payee, reference). The bridge checks it against the original text: the amount and the account digits must appear in the message, the date must be within 7 days of the message; anything else is rejected.
   - A checked result becomes a **suggestion on the review item** (one action to accept it), not a posted transaction. Each accepted message is also kept as a sample for writing a proper profile pattern later (rule 9).
4. Tests: masking (no long number, UPI ID or name reaches the request), validation rejects invented amounts/accounts, provider switch, webhook creation, category seeding. LLM calls are mocked in tests; one live run at the end.

### Left out of M4
- Telegram review buttons (M6). Statement balance comparison (after opening balances).

### Owner's answers (2026-11-13)
- Provider: the owner asked whether Google Cloud's $300 trial credit could pay for the model until M7. Findings (secondary sources, not confirmed in Google's terms): the credit does not cover the Gemini API key from AI Studio; it may cover Gemini on Vertex AI, but one report says that stops for trials started or upgraded from 2026-11-16; the trial lasts about 90 days; Vertex needs short-lived OAuth tokens, which the categoriser cannot use. Decision, as the owner said: **use Ollama on this Mac**.

### Questions for the owner (as asked)
1. **LLM provider.** Recommended: **Ollama on this Mac** (free, nothing leaves the Mac; needs installing Ollama and downloading a ~5 GB model; only works while the Mac is on). Alternatives: **Gemini** free tier or **Groq** free tier (free API keys, rate-limited; payee names and UPI IDs from the categoriser would leave the Mac; Google's free tier may use requests to improve its products). For M7 on a small cloud VM, a local model may be too slow, so the provider stays switchable.
2. **Fallback parser:** suggestion only, you accept each one (recommended), or post automatically when the checks pass?
3. **Categories:** is the list above right, or what would you add or remove?

### M4 progress (2026-11-13)
- Ollama was first installed on the Mac with Homebrew; the owner asked for Docker instead, so it was stopped and uninstalled, its model files and `~/.ollama` deleted, and python@3.15 (pulled in by that install) removed; `python3` was re-linked to the owner's Homebrew Python 3.14.7 as before. Ollama now runs as the `ollama` service (image 0.40.16, internal network, model volume), model qwen2.5:3b.
- 23 categories seeded into Firefly from `categories.yaml`, with notes for the categoriser. Bridge-known categories: ICICI salary credits (Salary), interest credits (Interest), ATM withdrawals (Cash), refunds (Refunds).
- Categoriser running (image pinned by digest), its own Firefly token in `.env`, settings page on 127.0.0.1:3010 only (checked: not reachable on the Wi-Fi address). Firefly's stored `allow_webhooks` setting switched on; webhook "AI categoriser (internal)" -> http://categorizer:3000/webhook created.
- LLM fallback: masking (UPI IDs and long numbers always; names too for cloud providers), checks against the original text, suggestion stored on the review item, `POST /api/v1/review/<id>/accept`. Only messages from known bank senders. 353 tests pass.

### M4 incident (2026-11-13): categoriser called OpenAI
- On the first batch run the categoriser sent 12 requests to api.openai.com instead of the local model. Each request carried one existing transaction's description, payee name and amount (and category names). OpenAI rejected all 12 with 401 (the placeholder key "ollama" is not a valid key). The categoriser was stopped immediately.
- Cause: an upstream bug. `ApplyStored` in the categoriser's `internal/config/config.go` always overwrites `OPENAI_BASE_URL` from the environment with the settings file's value; with no settings file it becomes empty, and an empty base URL means OpenAI's public endpoint.
- Fixes: (1) the settings file now holds the local address (`http://ollama:11434/v1`); (2) the categoriser and Ollama now sit only on the `ai` Docker network, which has no internet route (checked: api.openai.com cannot even be resolved from it), so a wrong setting can no longer send data out; (3) the categoriser page is published through a local-only nginx forwarder.
- After the fix: batch of 12 ran locally, no errors, no OpenAI calls in the log; all 12 marked needs-review (no history yet; local shops and people). The owner's categories in the review page will be reused for repeat payees.
- LLM fallback live check (made-up messages, nothing stored): debit and credit read correctly with account digits and reference; offer and declined payment rejected; 3-10 s per message after the model is loaded (the first load took ~95 s).

### M4 closing check (2026-11-14, by hand: /drift-review is not installed)
- Rule 2: endpoints are health, accounts, ingest/sms, ingest/email, review (+ accept); none moves money. The categoriser only writes categories and tags on existing Firefly transactions.
- Rule 3: the fallback reader sees only stored messages, which already passed the secret filter; its log line carries the review id and status only. Celery tasks take ids only.
- Rule 4: no float in money code (the only `float(` is the Gmail request pause).
- Isolation: ollama and the categoriser are only on the `ai` network; checked again: api.openai.com does not resolve from either, and the categoriser log has no OpenAI call since the fix.
- Secrets in git: none (`.env`, `accounts.yaml`, `secrets/`, the categoriser `config.json` lives in a Docker volume).
- 353 tests pass.
- Left for the owner: categorise payees in the categoriser's Review page (repeat payees then get categories without the model); opening balances.
- Upstream bug (categoriser ignores `OPENAI_BASE_URL` when its settings file is empty) not reported; reporting it is a public post, so only if the owner wants.

## M5 plan (presented 2026-11-14, not approved)

### Inputs found (2026-11-14)
- **Holdings:** CDSL CAS monthly (all demat stocks and mutual funds, PAN as password); Groww holding statement; CAMS/KFintech folio statements and SIP confirmations. Shares seen in notices: IRB, Star Cement, Amara Raja, Ajmera Realty (from e-voting mail only, not a valuation).
- **Credit report:** Experian report via Paisabazaar (7 emails, the email states a password rule); CIBIL sends enquiry alerts only, no report.
- **EMIs:** Axis "EMI Letter with Monthly EMI Details" (PDF), SBI Card "Merchant EMI booked" emails (3); bike loan still planned.
- **Card due dates:** already inside the statements M3 reads (due date, total and minimum due).

### Scope
1. **Investments in the ledger.** One Firefly asset account per holding place (e.g. "Mutual funds (CAS)", "Stocks (CAS)"), created by `seed_firefly` from `accounts.yaml`. A SIP or purchase debit from a bank becomes a **transfer** to that account (not an expense). After each CAS, the account is set to the CAS value by one transaction tagged `valuation` against a "Market value change" revenue/expense account, so Firefly's net worth includes investments and spending reports stay clean.
2. **CAS parser** (CDSL first, then Groww if it adds anything): holdings with units, NAV/price and value **as stated in the statement, with its date** (rule 9: no prices fetched or guessed). Holdings stored in the bridge (`Holding`, `HoldingSnapshot`). Totals must match the statement's own total or the statement goes to review.
3. **Credit report parser** (Experian): score, report date, open accounts with lender, type, sanctioned amount, outstanding, overdue, enquiries. Stored in the bridge only; used to cross-check that every loan and card in the report exists in `accounts.yaml` (missing ones go to review). Names, PAN, address and full account numbers are not stored.
4. **EMI schedule.** `Loan` and `EmiSchedule` in the bridge from the Axis EMI letter and SBI Card merchant-EMI emails (principal, rate, tenure, monthly EMI, remaining months), plus the bike loan from `accounts.yaml` once active. Each EMI and each card due date is also created as a Firefly **bill** (subscription), so Firefly shows what is due and matches payments to it.
5. **Card dues** from statements: due date, total and minimum due stored when a card statement is parsed; a review item if a due date passes with no payment seen.
6. **Goals** as Firefly piggy banks, defined in a gitignored `goals.yaml` (name, target, date, linked account), seeded by a command. Emergency fund target can be written as "N months of average spend"; the bridge computes the rupee amount from Firefly's last 6 months.
7. **Net worth snapshots.** Beat task on the 1st (and on demand) stores assets, liabilities, net worth and each account's balance with its status (confirmed / calculated / stale). Credit limits never count (rule 8).
8. **Read-only API** for M6: `GET /api/v1/networth` (latest + history), `GET /api/v1/upcoming` (EMIs and card dues in the next N days), `GET /api/v1/goals` (progress from Firefly), `GET /api/v1/holdings`.
9. **Tests** with masked fixtures for every new parser; valuation keeps net worth equal to assets minus liabilities; SIP debit becomes a transfer not an expense; EMI schedule maths in paise; snapshot idempotent per month.

### No new dependencies; no cost.

### Left out of M5
- Live NAV or share prices (not an allowed data source; see question 2). Telegram alerts for dues (M6). HSBC's first statement (before the ledger start; not needed).

### Questions for the owner
1. **Goals:** which goals do you want first, with target and date (e.g. emergency fund = 6 months of spend, bike down-payment, an investment target)? They go in `goals.yaml`, not chat, if you prefer.
2. **Valuation between statements:** use only the monthly CAS value (recommended, within the spec), or allow the free public AMFI daily NAV file for mutual funds (a spec change: new data source)?
3. **Investments in Firefly:** OK to record them as asset accounts with a monthly `valuation` adjustment (recommended), or keep them only in the bridge and add them to net worth there?
4. **Credit report:** do you download the Experian report from Paisabazaar regularly, and do you also get a CIBIL report PDF?
5. **Bike loan:** still not disbursed?

### Owner's answers (2026-11-14)
1. Goals: later. The goals command and `goals.yaml` are built in M5; the owner fills goals whenever ready.
2. Valuation: monthly CAS value only (no AMFI NAV).
3. Investments in Firefly: asset accounts with a monthly `valuation` adjustment (approved with M5).
- Goal (2026-11-14): Bike down-payment (Meteor 350), Rs 2,50,000 by 15 Dec 2026, money kept in HSBC Bank.
4. Credit report: not downloaded regularly. Experian reports that arrive by email are parsed; nothing is required.
5. Bike loan: planned for December 2026; owner changes it to `active` in `accounts.yaml` when disbursed.
- Groww API checked and not used: trading API, demat stocks only (no mutual funds), no current value without the paid plan, tokens expire daily and can also place orders.

### M5 progress (2026-11-14)
- New `wealth` app. Read-only endpoints: `/api/v1/networth`, `/upcoming`, `/goals`, `/holdings`.
- **EMIs:** Axis EMI letter parser (schedule must add up to the converted amount, within the letter's whole-rupee rounding). The owner's Flipkart EMI (6 x Rs 3,507, Nov 2026 to Apr 2027) is stored with its schedule and created as a Firefly bill.
- **Card dues:** due date, total and minimum (Axis) recorded from card statements; 7 recorded. A daily task marks a due paid when payments on the card since the statement reach the minimum (each payment counted once), otherwise raises a `card_due_unpaid` review item. Statements from before the ledger start are not judged.
- **Goals:** `goals.yaml` (gitignored, example in `goals.example.yaml`) -> Firefly piggy banks via `seed_goals`; progress = positive balance of the linked accounts, capped at the target, refreshed daily. Emergency fund can be `months_of_spend: N` (average of the last 6 whole months, CAS revaluations left out). Bike goal created.
- **Net worth:** `networth_snapshot` command and beat on the 1st (06:00 IST) for the month just ended. Negative balances count as liabilities; credit limits are never read. Today it shows negative net worth because opening balances are still placeholders.
- **Investments:** CAS documents create "Mutual funds (CAS)" and "Demat stocks (CAS)" asset accounts and revalue them to the CAS value on the statement date (one `valuation`-tagged transaction against "Market value change"); an older CAS never overrides a newer one. Debits to `MUTUAL FUNDS` (wording from the owner's SMS) are posted as transfers into the mutual funds account once it exists.
- **Statement import:** a parser that finds figures that do not add up now marks the PDF `needs_parser` with the reason instead of failing the task.
- Senders added: CDSL CAS (`cdslstatement.com`) and Experian as document-only email profiles (they can only ignore or review, never create transactions). 3 CAS PDFs downloaded (Jul-Sep 2026), still locked.
- 377 tests pass.
- **CDSL CAS reader** (2026-11-14, from the owner's real statements): holdings tables only; refused unless each row's units x price matches its value, each demat account matches its "Portfolio Value" and the total matches the "Grand Total". Owner's PAN saved through the hidden prompt (opens all 3). Jul, Aug, Sep 2026 imported oldest first: Firefly now has "Mutual funds (CAS)" and "Demat stocks (CAS)" at the CAS values as on 30 Sep 2026 (funds and an ETF held in demat via two brokers, plus a few stocks; values kept out of this public file). The October CAS (expected mid-November) is read automatically.
- The CAS says "No MF Folios for this PAN pattern": funds held outside demat (CAMS/KFintech folios, e.g. folio SIPs seen in old SMS) are not in it. If any are still held, a CAMS/KFintech CAS would be needed (not in M5 scope yet).
- Valuation adjustments before 1 Nov 2026 include purchases made before the ledger started; from 1 Nov, SIP debits are transfers and adjustments are market movement only.
- 382 tests pass.
- Not done: **Experian:** each report's password arrives by SMS (dropped by the OTP filter) and the owner does not download reports regularly, so no parser yet; one can be written from a report the owner chooses to open.

### M5 closing check (2026-11-14, by hand: /drift-review is not installed)
- Rule 2: new endpoints (networth, upcoming, goals, holdings) are GET only; the bridge writes only ledger records to Firefly (accounts, valuation transactions, bills, piggy banks).
- Rule 3: the PAN was typed into the hidden prompt only; stored Fernet-encrypted (checked in the database), not in logs (checked). Celery tasks take ids or nothing.
- Rule 4: no float in money code; units and prices kept as decimal strings; one display float in statement line text replaced.
- Rule 8: credit limits never read; negative balances count as liabilities.
- Rule 9: CAS values exactly as stated; no prices fetched; EMI and CAS readers written from the owner's real documents and refuse figures that do not add up.
- Secrets in git: none (`goals.yaml`, `accounts.yaml`, `.env`, PDFs ignored).
- Left out by the owner's decision: Experian reader. Left for later: CAMS/KFintech CAS if non-demat funds are held.
- 382 tests pass.

## M6 plan (presented and approved 2026-11-14)

### Checked before planning (2026-11-14)
- qwen2.5:3b (the Ollama container) supports tool calls: 1-7 s per answer once loaded, ~55 s for the first answer after the model loads. It does **not** reliably decide to look data up (asked "am I on track for my bike goal?" it answered without calling the goal tool). So the bridge must not rely on the model to fetch numbers.
- Firefly gives spending per category and per payee for any date range (`insight/expense/category`, `insight/expense/expense`).

### Scope
1. **Summaries** (bridge code, read-only, integer paise): spending by category and top payees for a date range, this month vs last month, upcoming EMIs and card dues, goals, net worth now and by month, holdings, open review items. Computed by code, never by the model.
2. **`POST /api/v1/chat`** `{message, history}` -> `{answer, facts_used}`.
   - Every question gets a compact fact sheet (this month's spend by category vs last month, upcoming 30 days, goals, net worth, holdings date) chosen by simple keyword matching, plus tools the model may call for anything else (another month or date range, one category, one payee).
   - **Number check:** every rupee amount in the answer must appear in, or be a simple sum/difference of, the facts given; otherwise the bridge asks the model once more, and if it still fails, answers with the facts themselves. Same idea as the M4 fallback check.
   - Only summaries reach the model: never raw SMS/email text, account or card numbers, or references. Local model only (Ollama, no internet); if a cloud provider is ever chosen, payee names are left out.
   - The bridge keeps no chat history; the client sends the last few turns.
   - Advice only: it can never move money (rule 2), and it says it is not a licensed adviser when asked about specific investments.
3. **`GET /api/v1/digest?week=YYYY-Www`**: the weekly digest as data (spend vs same days last month, top categories, upcoming dues, goal progress, net worth change) plus a short text written from those numbers by code; the model only rephrases, and its text passes the same number check.
4. **`GET /api/v1/alerts`**: computed by rules, no model: card due unpaid; card due or EMI in the next 3 days; a category this month above 1.5x its 3-month average; a goal behind its needed pace; open review items; CAS older than 45 days.
5. **Temporary test chat page** (until the APK): one static page served by a small `advisor-ui` nginx container on **127.0.0.1:3020 only**, which forwards only `/api/v1/chat`, `/digest` and `/alerts` to the bridge and adds the API token itself (the token is never in the page). Removed when the app exists.
6. **Tests:** summaries against the fake Firefly; the number check rejects invented amounts; no account digits, references or message text in what is sent to the model; alert rules; endpoints need the token and are read-only. One live run with the real model.

### No new Python dependencies. One new container (nginx, already used). No cost.

### Left out of M6
- Phone notifications for digest and alerts (Phase 2 app).
- Any cloud model.

### Questions for the owner
1. **Model:** keep qwen2.5:3b (fast, small, weaker answers), or try qwen2.5:7b (better at reasoning and tool use, ~2-3x slower on the CPU, needs Docker's memory raised from 7.7 GB to about 10 GB in Docker Desktop settings)?
2. **Alerts:** are the rules in item 4 the ones you want? Add a low-balance alert (and at what amount)?
3. **Digest day:** which day of the week should the digest cover (e.g. Monday to Sunday)?

### Owner's answers (2026-11-14)
- "Approved" without answering the three questions, so the defaults in the plan are used: qwen2.5:3b kept; the alert rules as listed, no low-balance alert; digest weeks Monday to Sunday. Each can be changed later.

### M6 progress (2026-11-14)
- New `advisor` app. `POST /api/v1/chat`, `GET /api/v1/digest`, `GET /api/v1/alerts` (token, read-only).
- Facts computed by code from Firefly insight (spending by category and payee, income) and the M5 data; CAS revaluations left out of spending. Only names and totals reach the model; a test checks no account digits or message text do.
- Chat: fact sheet in the prompt plus two tools (`spending_between`, `income_between`); local model only (`providers.chat` refuses cloud providers). Number check: every rupee amount (₹, Rs, INR, rupees, lakh, crore) must match a fact, or a sum or difference of two, within Rs 1 (0.5% for rounded lakh figures); one retry, then the plain facts.
- Digest: Monday-Sunday, numbers **and** wording from code (the plan had the model rephrase it; dropped, as code text cannot be wrong and the 3B model adds nothing). Alerts: unpaid card due, due within 3 days, category above 1.5x its 3-month average (only once 3 whole months exist after the ledger start), goal behind pace, review items waiting, CAS older than 45 days.
- Test page: `advisor-ui` (nginx) on 127.0.0.1:3020 only; adds the token itself; passes only chat, digest and alerts (checked: other routes 404, not reachable on the Wi-Fi address, token not in the page).
- Found in the live run and fixed: the 3B model left the EMI out of "what do I need to pay" (so answers about dues, goals and net worth now end with "From your records:" and the complete list from code); it said "you spent ₹0 in September" (periods before the ledger start are now reported as not tracked, in chat and digest); it gave the total of all funds as one fund's value (each holding's value is now in the facts). The number check cannot catch a real figure used for the wrong thing, so answers should be read as help, not as statements.
- Bridge gunicorn now 3 workers with a 180 s timeout (a chat answer can take up to a minute when the model has just loaded).
- 405 tests pass. Live re-run after the fixes: dues answer lists both items, September reported as not tracked, a question about one fund gives that fund's own value.

### M6 closing check (2026-11-14, by hand: /drift-review is not installed)
- Rule 2: advisor endpoints only read; `POST /chat` changes nothing. The model is told it cannot move money and has no tool that could.
- Rule 3 and privacy: the model receives only names and totals (test-checked: no account digits or message text); chat text is not logged (checked) or stored; the AI containers still have no internet (api.openai.com does not resolve); chat refuses any cloud provider.
- Rule 4: no float in advisor or wealth code; amounts are paise, shown as ₹ by code.
- Rule 9: amounts in answers must match the facts; periods before the ledger start are "not tracked", never zero.
- Ports: the test page is on 127.0.0.1:3020 only; the token is added by nginx and is not in the page.
- Secrets in git: none.
- 405 tests pass.

## M7 plan (presented and approved 2026-11-14)

### Checked before planning (2026-11-14)
- **Oracle Always Free** (secondary sources, not Oracle's page): the free Arm allowance was halved in 2026 to **2 OCPU / 12 GB RAM** in total (enforcement date reported as June or 18 Aug 2026); Arm capacity is very often unavailable; sign-up needs a card; idle accounts may be reclaimed. The stack fits in 12 GB, but the 3B model would answer slower on 2 cores.
- **Tailscale** free Personal plan: reported as up to 6 users with unlimited devices since April 2026, non-commercial use (to confirm on tailscale.com/pricing). Gives the phone a private, encrypted link to the server from anywhere, with a free HTTPS certificate (`tailscale serve`), and nothing published on the internet.
- **Gmail tokens:** the Google sign-in apps are in "Testing", so refresh tokens expire every 7 days. Switching the consent screen to "In production" removes the 7-day limit (Google then shows an "unverified app" warning at sign-in, which the owner clicks through once); tokens then last while they are used.
- **This Mac:** FileVault on (disk encrypted); Docker has 10 CPUs and 7.7 GB; the data is small (bridge files 10 MB).
- **Other free hosting** (owner asked, 2026-11-14; comparison blogs, not providers' pages): Google Cloud e2-micro (1 GB RAM, 0.25 vCPU, US regions only) and AWS free tier (1 GB, 12-month or ended for new accounts) are too small for Firefly + Postgres + the bridge, let alone the model (the stack needs ~4-6 GB). Render, Koyeb, Railway and Fly.io have no always-on free container with a persistent disk (they sleep, expire databases after 30 days, or are short trials). Only Oracle Always Free can hold the whole stack for free; otherwise a machine at home (this Mac, an old laptop, a mini PC).

### Scope
1. **Where it runs** (owner's choice, question 1). Same Docker Compose stack either way; a `docs/deployment.md` guide for a fresh machine: install Docker, copy the repo, restore `.env` and a backup, start, check.
2. **Remote access and HTTPS:** Tailscale on the server and on the phone. The bridge is served at `https://<machine>.<tailnet>.ts.net` with Tailscale's certificate; the SMS forwarder and the future app use that address. The plain-HTTP Wi-Fi port (`docker-compose.lan.yml`, 192.168.0.106:8000) is removed. Firefly, the categoriser page and the test chat page stay on 127.0.0.1 (reachable from other own devices only through Tailscale, if wanted).
3. **Backups:** nightly at 02:30 IST, a `backup` container runs `pg_dump` of both databases plus the bridge files (statements as received) and the categoriser settings, encrypts them with **restic** (BSD-2, free) into a repository **outside the server** (question 3), keeps 14 daily, 8 weekly and 12 monthly copies, and checks the repository weekly. The backup password lives only in `.env` and in the owner's password manager. A restore drill is done once on a scratch stack and the steps are written down.
4. **Secrets kept safe outside the server:** `.env` (with `BRIDGE_ENCRYPTION_KEY`, without which Gmail tokens and statement passwords cannot be read) is exported once, encrypted, for the owner to keep in a password manager. Not in git, not in the backup repository in plain form.
5. **Raw message bodies encrypted at rest** (the M2 note): SMS and email bodies stored by the bridge are encrypted with `BRIDGE_ENCRYPTION_KEY`, decrypted only when parsed or shown in review; existing rows migrated. Disk encryption stays on (FileVault, or the VM's encrypted volume).
6. **Gmail sign-in to production** for both Google projects (owner clicks in Google Cloud Console; one new sign-in each, read-only scope unchanged).
7. **Keeping it healthy:** Docker log size limits; `restart: unless-stopped` already set; a health alert in `/api/v1/alerts` when the Gmail poll, the statement task or the last backup is older than expected, or the SMS forwarder has sent nothing for 2 days.
8. **Tests:** body encryption round trip and migration; backup script on a test stack (dump, encrypt, restore, compare counts); new health alerts.

### Cost
All free (Tailscale Personal, restic, Oracle Always Free or a home machine). Nothing added that costs money; if Oracle asks for an upgrade, stop and ask.

### Left out of M7
- A public internet address (Cloudflare Tunnel or open ports): not needed with Tailscale, and it would expose the bridge to the internet.
- The Android app (Phase 2).

### Owner's answers (2026-11-14)
- Approved: Oracle Always Free with AI; Tailscale; encrypted backups to this Mac; both Google sign-in apps to "In production". Every image already runs as arm64 on this Mac (checked), so the same stack runs on Oracle's Arm machines.
- **Where:** Oracle Always Free (Arm, about 2 OCPU / 12 GB), AI kept (slower chat is fine). Measured on this Mac: the stack without AI uses ~0.75 GB; with the 3B model loaded ~4-4.5 GB at peak, so it fits.
- Looked at and rejected: Hugging Face Spaces (sleeps, no safe persistent database, public app), Kaggle as a model backend (against its purpose, sends data out), splitting Oracle into two VMs (not needed).
- **Idle reclamation** (owner's concern): Oracle stops (does not delete) an Always Free instance only if, over 7 days, CPU, network **and** memory (Arm shapes) are all below a threshold (reported 10-20%, 95th percentile; to confirm on Oracle's page). Plan: keep the model loaded permanently (`OLLAMA_KEEP_ALIVE=-1`, ~3 GB of 12 GB, about 25%), which keeps memory above the threshold for real use and removes the slow first answer; plus a health alert if the instance was stopped. No CPU-burning "keep busy" scripts. Optional, owner's choice: converting the account to Pay As You Go removes idle reclamation; Always Free resources stay free, but a card is then on file for anything beyond them, so a budget alert at Rs 1 would be set.

### Questions for the owner
1. **Where should it run?** (a) **This Mac, always on** (recommended for now: free, already works, fast enough for the model; the Mac must stay on and awake, and the phone reaches it through Tailscale when away from home); (b) **Oracle Always Free** (free if you can get Arm capacity; 2 cores make chat slower; needs a card at sign-up); (c) another always-on machine at home.
2. **Tailscale** on the Mac and phone for access from anywhere? (Recommended. Without it the phone only reaches the bridge on home Wi-Fi, over plain HTTP.)
3. **Where should encrypted backups go?** (a) an external drive plugged into the Mac; (b) a folder in iCloud Drive or Google Drive synced by the Mac (encrypted before it leaves); (c) Oracle Object Storage (if the server is on Oracle, backups would go to the Mac instead).
4. OK to switch both Google sign-in apps to **"In production"** (one-time "unverified app" warning, no more weekly expiry)?

### M7 progress (2026-11-14)
- **Backups go to Google Drive** (owner's change during the build; the Mac backup store was started, never used, and removed). `backup` container: restic + rclone, Drive access `drive.file` only (sees only the files it creates). Nightly 02:30 IST plus hourly catch-up if the last success is older than 26 h; keeps 14 daily / 8 weekly / 12 monthly; weekly `restic check`. Encrypted before upload (`RESTIC_PASSWORD`, only in `.env`). One-time sign-in: `scripts/gdrive-connect.sh` (puts the token into `.env` without showing it). Owner enabled the Drive API and signed in (2026-11-14). First backup: snapshot ee2b5c6e, 10 MB, in the Drive folder `personal-finance-backups` (rclone lists only that folder: the token sees nothing else). **Restore drill passed**: latest snapshot restored from Drive into a throwaway PostgreSQL; bridge 72 messages / 13 entries and Firefly 21 transactions / 25 accounts match the live system; 24 bridge files restored; drill containers, volume and network removed afterwards.
- **Message bodies encrypted at rest:** `EncryptedTextField` (Fernet, `BRIDGE_ENCRYPTION_KEY`), migration re-saved all 71 stored bodies (checked: 71 of 71 start with `enc1:`; review queue still reads them). A temporary pre-migration dump was deleted after the check.
- **Bug found and fixed:** bridge, worker and beat each had their own image and only the bridge's was rebuilt, so the worker and beat ran 20-hour-old code and the M5 tasks (card dues, monthly net worth) were not registered. They now share one image (`personal-finance-bridge:local`); checked registered tasks; nothing was mis-posted meanwhile (1 entry posted, no investment payee).
- **Health alerts** (`/api/v1/alerts`): background job stopped (posting 10 min, Gmail 60 min, statements 3 h, from `Heartbeat` rows), no SMS for 48 h, backup missing, failed or older than 36 h.
- Docker logs capped (10 MB x 3 per service); Ollama keeps the model loaded (`OLLAMA_KEEP_ALIVE=-1`).
- `scripts/export-secrets.sh` (one passphrase-encrypted file of `.env`, `accounts.yaml`, `goals.yaml`, `secrets/`), `scripts/restore-drill.sh` (latest backup into a throwaway PostgreSQL, counts compared, then deleted), `docs/deployment.md` (Oracle, Tailscale, restore, phone, checks).
- Seen meanwhile: the Mac's Wi-Fi briefly dropped, so the bridge could not bind 192.168.0.106 for a few minutes; back on the same address. Tailscale on the server removes this dependence. The Wi-Fi binding stays on the Mac until the move.
- 412 tests pass.
- **Google apps stay in "Testing"** (owner's choice, 2026-11-14): publishing needs a public home page and privacy policy URL. Instead, `/api/v1/alerts` reminds from day 3 after each sign-in (medium; high on the last day and once expired), so reconnecting every 3-4 days keeps Gmail and Drive working; `scripts/google-reconnect.sh` renews all three sign-ins. Sign-in dates: `GmailAccount.connected_at` (backfilled from the first connection, 13 Nov), `GDRIVE_CONNECTED_AT` in `.env`. **Phase 2 note:** the app must show these alerts as phone notifications. `GOOGLE_OAUTH_TESTING=0` turns the reminders off if the apps are ever published.
- **Review queue on the test page** (owner's request): "Review" lists open items in plain words with the message text and buttons (accept checked AI reading, pick the matching payment or "new payment", post as it is, read again, ignore / "I paid it"). The nginx forwarder passes only the review list and its four actions; other bridge routes stay blocked (checked: 404). Review items now carry `candidate_details` (amount, date, payee of each candidate).
- **Tailscale in Docker** (`tailscale` service, image v1.104.7, userspace mode, state in a volume): `https://finance.<tailnet>.ts.net` -> bridge, `:8443` -> test chat page; serve only (never funnel). Nothing installed on the Mac. Live 2026-11-14: `https://finance.<tailnet>.ts.net` (certificate issued, tailnet only). The SMS phone (Tailscale app) now posts there; its Test arrived through the Tailscale container. The Wi-Fi binding (`docker-compose.lan.yml`, `COMPOSE_FILE`/`BRIDGE_LAN_IP`) is removed from `.env`: the bridge listens only on 127.0.0.1 and Tailscale (checked: 192.168.0.106:8000 closed). The single-use auth key was removed from `.env` after login.
- **Tap-to-reconnect, server side** (owner's request): daily 08:00 Celery task makes a one-time link (24 h, single use, stored encrypted + hashed) for each Google sign-in 3+ days old; the reconnect alert carries it (`data.link`) for the app's notification. `/api/v1/google/connect/<token>` -> Google sign-in (PKCE, `prompt=consent`, same scopes only) -> `/api/v1/google/callback` saves the token encrypted, refuses a different Google account (SHA-256 of the address; stored now for both mailboxes) or wider scopes. A Drive reconnect is handed to the backup job through an owner-only file in the `backup_secrets` volume. Works only with an `https://` `PUBLIC_BASE_URL` (Tailscale) and a "Web application" OAuth client per Google project (redirect URI `<PUBLIC_BASE_URL>/api/v1/google/callback`). Live 2026-11-15: owner created both web clients (entered through hidden prompts); a test link for Gmail acct1 opened on the phone over Tailscale -> Google -> "Connected"; the renewed token then polled Gmail successfully. `reconnect_link <connection>` makes a link on demand.
- 423 tests pass.
- **Category questions** (owner's request, approved 2026-11-15): every 5 minutes a Celery task looks at posted withdrawals; one still without a category 10 minutes after posting (the AI categoriser had its chance) becomes a `category_needed` review item, asked once (ignored ones are not asked again; one categorised elsewhere is closed automatically). `/api/v1/alerts` has one `category_needed` alert per question with the payment, the owner's categories (`choices`) and the payee's past categories (`suggested`; the categoriser has no API for its own guesses). Answer: `POST /api/v1/review/<id>/category {"category", "always"}` sets the category in Firefly (removes `ai:needs-review`, adds `category-by-owner`); `always` also creates or updates one Firefly rule per payee (group "Payee categories (bridge)") and answers the payee's other open questions. Test page: category buttons on the Review cards. Checked live: Firefly accepted the rule format (throwaway rule deleted), the update call works, the 2 uncategorised payments are now questions. **Phase 2 note:** each `category_needed` alert is a phone notification with category buttons. Not checked: whether the AI categoriser overwrites a category set by a rule on new payments (watch the first one).
- Test fixes: test encryption keys are generated per run (GitGuardian had flagged the old made-up keys in the public repo; they were never real); the reconnect test no longer uses a fixed date.
- 432 tests pass.
- Earlier M7 plans targeted Oracle (capacity failures) and then the Acer laptop. The owner returned to Oracle after the Acer proved too noisy; see `docs/deployment.md`.
- **M7 Oracle restore and staging (2026-11-18):** Oracle Hyderabad VM, Ubuntu 24.04 ARM64, A1 Flex 2 OCPU/12 GB and 100 GB boot volume. Created without upgrading the account from the free/limited tier. Temporary SSH access is restricted to the current home IP; application ports remain loopback-only and are not open in the OCI security list. The project and owner-only configuration were copied over SSH. Snapshot `ac4afbd9` restored the PostgreSQL databases and bridge/categoriser data. Because the restore did not include Firefly Passport signing keys, the key pair was securely copied from the paused Mac Firefly container; bridge health then returned 200 and Firefly 6.7.9 validated. The keys are now in a persistent `firefly_storage` volume and the encrypted Drive backup includes that volume. Snapshot `b180312e` verified the updated backup and both OAuth key files. `qwen2.5:3b` was downloaded to Ollama; Ollama and categoriser are only on `finance_ai` (`internal: true`). Firefly, bridge, local Nginx UIs, categoriser, Firefly cron and backup scheduler are running. Worker and beat are stopped. Tailscale was not enabled and no auth key was created; the owner wants to use it only if needed. Phone, Gmail, and reconnect cutover remain pending until an HTTPS route is chosen. The Mac app remains paused for rollback.
- **M7 finish record (2026-11-20):** the owner-selected Tailscale route is live; `PUBLIC_BASE_URL` and the Google OAuth redirect URI match it; worker and beat run. The phone's advisor route works, SMS messages arrive at the Oracle bridge, category and Google reconnect alerts are generated, and Gmail/statement/sweep heartbeats are current. A fresh encrypted Drive snapshot (`3041c41b`) restored on Oracle to a throwaway PostgreSQL with matching row counts (126 raw messages / 38 entries; 31 Firefly journals / 32 accounts) and 133 bridge files. Host app ports are loopback-only, the AI network is internal, and the Docker check is clean. Public SSH remains restricted to the owner's home IP. The open review queue is recorded above for owner action; nothing was silently dismissed. No tests were run as part of this closure.

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
