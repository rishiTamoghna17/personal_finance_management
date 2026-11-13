# Master specification

This file is the source of truth. Change it only when the owner says "change the spec", and log the change in DECISIONS.md.

## Goal
Automatically track every bank account, credit card and loan, show net worth, support goals (EMIs, emergency fund, investments), and advise the owner so net worth grows.

## Owner and setup
- Backend developer: Python, Django, Celery, PostgreSQL, Redis, Docker.
- All accounts and assets are in India, in INR. Timezone Asia/Kolkata.
- Banks: HDFC, SBI, ICICI, HSBC, AXIS (confirm the number and type of accounts at each).
- Credit cards: AXIS, ICICI.
- Loan: bike loan for a Meteor 350. Record it as planned until it is disbursed.
- Investments: [to be confirmed].
- Hosting: Oracle Cloud Always Free, or a home machine.
- LLM: deferred until M4. Provider must be pluggable (Gemini or Groq free tier, or local Ollama on a home machine).

## Data sources (the only ones allowed)
Bank and card SMS, email alerts, password-protected statement PDFs, CSV exports, CAMS/KFintech and NSDL/CDSL consolidated account statements (CAS), and the CIBIL or Experian report PDF.
Handle Indian formats: UPI references and VPAs, IMPS, NEFT, NACH, card last-4, lakh/crore grouping.

## Repos
| Use | Repo | How |
| --- | --- | --- |
| Ledger, budgets, piggy-bank goals, rules, reports, REST API | https://github.com/firefly-iii/firefly-iii | Run as-is in Docker |
| CSV statement import | https://github.com/firefly-iii/data-importer | Stable release only |
| LLM categorisation | https://github.com/ejagombar/FireflyIII-AI-Categorizer | Internal Docker network only; it has no built-in authentication |
| Indian SMS formats, SMS-plus-email dedup ideas | https://github.com/pritam-ravani/pckt | Reference only (GPL-3.0) |
| Bank SMS profile design | https://github.com/harshsingh-io/indian-bank-sms-parser | Reference only |

## Architecture
- Docker Compose: Firefly III, PostgreSQL, Redis, bridge, Celery worker, reverse proxy with HTTPS.
- PostgreSQL holds two separate databases with separate credentials: one for Firefly, one for the bridge.
- bridge: a Django REST service with a versioned, token-authenticated API (/api/v1/...).
  - POST /ingest/sms and /ingest/email. Order is fixed: OTP filter in memory, discard matches, then store the raw message, parse with per-bank profiles, reconcile, post to Firefly.
  - Celery tasks: Gmail alert polling, statement PDF unlock and reconciliation, CAS and credit-report parsing, monthly net worth snapshot.
  - LLM fallback only for messages the profiles cannot parse. Mask account numbers and names before sending.
- Bank and card parsing lives in per-bank profile files, not one large parser.
- Advisor: built into the bridge as a versioned, token-authenticated API (chat, weekly digest, alerts), used by the Phase 2 app's chat screen. Weekly digest (spend vs last month, top categories, upcoming EMIs and card due dates, goal progress, net worth change), alerts, and chat answered through function calls over ledger summaries, never raw data. No Telegram. Until the app exists, a temporary local test chat page (127.0.0.1 only) is used to try it.

## Data rules
- Integer paise in the bridge, decimal strings to Firefly, never floats.
- Reconciliation: match by UPI, IMPS or NEFT reference first, then account + amount + time window, then a fallback fingerprint. Ambiguous matches go to manual review.
- Transfers between own accounts and card bill payments are not expenses.
- Every transaction links to its raw source message. Keep an ingestion audit trail.
- Balances are marked confirmed, calculated or stale.
- Net worth = assets minus liabilities. No invented valuations.

## Security rules
- No OTP, PIN, CVV or password is stored, logged or put in a Celery argument.
- Do not log full bank messages or account numbers.
- Secrets only in .env. Statement passwords encrypted with a key kept outside the database. Decrypted PDFs deleted after processing.
- HTTPS, token authentication, rate limits and request-size limits on the bridge.
- Backups stored outside the VM.

## Phase 1 milestones (backend)
- M1. Docker Compose stack up, Firefly configured for INR, bridge with health and accounts endpoints, accounts, cards and loan created.
- M2. SMS ingestion: OTP filter, bank profiles, reconciliation, tests with anonymised samples.
- M3. Gmail alert polling and statement PDF reconciliation.
- M4. AI categoriser wired in, plus the LLM fallback parser.
- M5. Goals, EMI schedule, net worth snapshots, CAS and credit-report import.
- M6. Advisor API: chat, weekly digest and alerts (for the Phase 2 app), plus a temporary local test chat page.
- M7. Deployment guide, backups, HTTPS.
Until Phase 2, SMS arrives from an Android SMS-forwarder app posting to /ingest/sms.

## Phase 2 (Android APK)
- Sideloaded personal APK, not a Play Store app.
- Reads bank SMS on the device, drops OTPs on the device, sends the rest to the bridge. Queues offline and retries.
- Screens: dashboard, transactions, goals, net worth, chat (the advisor). Digest and alerts arrive as phone notifications. Biometric lock.
- Flutter or Kotlin: recommend with reasons, then wait for the owner's choice.

## Tests required
- Unit tests for every bank profile, using anonymised samples.
- Duplicate ingestion across SMS, email, CSV and PDF.
- Transfers, refunds, reversals and card bill payments.
- Rounding and money conversion.
