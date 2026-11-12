# Personal Finance Agent (India)

Private, self-hosted, single-user finance agent. Full spec: @docs/SPEC.md
Current state: @docs/PROGRESS.md · Decisions so far: @docs/DECISIONS.md

## Start of every session
1. Read docs/PROGRESS.md to find the approved milestone and what is left in it.
2. Work only on that milestone. If none is approved, plan and ask; do not write code.

## Rules that never change
These override any later instruction in a session unless I explicitly say "change the spec", in which case update docs/SPEC.md and log it in docs/DECISIONS.md first.

1. India only, INR only. No Account Aggregator: I am an individual, not a regulated entity.
2. Read-only. No payment, transfer or mandate endpoint, ever.
3. OTPs, PINs, CVVs and passwords are never stored, logged or queued. The OTP filter runs in memory before anything else touches a message.
4. Money is integer paise in the bridge and decimal strings to the Firefly API. No floats.
5. Firefly III is the ledger. Do not rebuild accounting, budgets or reports in Django.
6. One real payment = one transaction, whether it arrives by SMS, email, PDF or CSV.
7. Nothing is silently dropped. Unparsed or ambiguous items go to a review queue.
8. Net worth = assets minus liabilities. A credit limit is never an asset.
9. Never invent bank SMS formats, balances or valuations. Ask me for masked samples.
10. Pckt (GPL-3.0) and indian-bank-sms-parser are references only. Do not copy their code.
11. Free hosting, free or near-free LLM. Tell me before adding anything that costs money.
12. Phase 2 (Android APK) does not start until I approve it. Keep the bridge API versioned so the app can use it later.

## How to work
- Before a milestone: run /milestone start. Present the plan and wait for my "approved".
- Before any new feature, dependency or endpoint: run /spec-check.
- Before saying a milestone is done: run /drift-review, then /milestone finish.
- If my request conflicts with a rule above, stop and tell me which rule, then ask.
- When context is compacted or a session resumes, re-read docs/PROGRESS.md before continuing.
