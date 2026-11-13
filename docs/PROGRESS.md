# Progress

Update this file at the start and end of every milestone. It is how a new session knows where things stand.

## Now
- Approved milestone: M3 (approved 2026-11-13)
- Status: M3 in progress. Part A (Gmail alert emails) is live. Part B (statement PDFs) next: needs the owner to enter statement passwords in a hidden prompt.
- Next step: owner answers the M3 questions; owner also fills opening balances in `accounts.yaml` and re-runs `seed_firefly` (not blocking M3).

## Milestones
| ID | Scope | Status | Approved on | Finished on |
| --- | --- | --- | --- | --- |
| M1 | Docker stack, Firefly, bridge skeleton, accounts | Finished | 2026-11-12 | 2026-11-12 |
| M2 | SMS ingestion, OTP filter, profiles, reconciliation | Finished | 2026-11-12 | 2026-11-13 |
| M3 | Gmail alerts, statement PDFs | In progress | 2026-11-13 | |
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

### Questions for the owner (as asked)
1. Gmail access: Gmail API with read-only permission (recommended: it can only read; needs a free Google Cloud project and a one-time sign-in), or IMAP with an app password (simpler, but that password unlocks the whole mailbox and could also send mail)?
2. Which banks and cards email you monthly statements, and do you know each statement's password format? (Do not send passwords in chat; the command will ask for them.)
3. Do any of your banks send transaction alert emails, or only SMS?
4. OK to leave CSV / data-importer out of M3?

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
