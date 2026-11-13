# Progress

Update this file at the start and end of every milestone. It is how a new session knows where things stand.

## Now
- Approved milestone: none. M6 finished 2026-11-14. Next in the spec: M7 (deployment, backups, HTTPS); Phase 2 (APK) still needs the owner's approval.
- Status: M1-M6 running: SMS from the phone, bank emails from two Gmail accounts, statement PDFs, local AI categoriser and checked fallback reader.
- Next step: plan M7 when the owner asks; owner also fills 1 Nov opening balances in `accounts.yaml` and categorises payees on http://127.0.0.1:3010 (neither blocking).

## Milestones
| ID | Scope | Status | Approved on | Finished on |
| --- | --- | --- | --- | --- |
| M1 | Docker stack, Firefly, bridge skeleton, accounts | Finished | 2026-11-12 | 2026-11-12 |
| M2 | SMS ingestion, OTP filter, profiles, reconciliation | Finished | 2026-11-12 | 2026-11-13 |
| M3 | Gmail alerts, statement PDFs | Finished | 2026-11-13 | 2026-11-13 |
| M4 | AI categoriser, LLM fallback | Finished | 2026-11-13 | 2026-11-14 |
| M5 | Goals, EMI, net worth, CAS, credit report | Finished (Experian reader left out) | 2026-11-14 | 2026-11-14 |
| M6 | Advisor API (chat, digest, alerts) + temporary test chat | Finished | 2026-11-14 | 2026-11-14 |
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
