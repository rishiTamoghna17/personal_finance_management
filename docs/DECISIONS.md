# Decisions

Add one entry whenever a design choice is made or the spec changes. Newest first. Never delete entries.

Format: date · decision · why · who approved

- 2026-11-13 · AI services (ollama, categoriser) run only on a Docker network with no internet route (`ai`, internal: true); the categoriser page is published through a local-only nginx forwarder on 127.0.0.1:3010 · after the categoriser sent requests to OpenAI despite OPENAI_BASE_URL (upstream bug), isolation must not depend on configuration · Claude, reported to owner

- 2026-11-13 · Ollama runs as a Docker service (internal network only), not on the Mac; model qwen2.5:3b · owner asked not to install software on the PC; Docker's 7.7 GB memory and CPU-only inference suit a 3B model; the 7B needs more Docker memory · owner
- 2026-11-13 · Categoriser settings page on 127.0.0.1:3010 (3000 is used by another program on this Mac) · local-only, no login · Claude

- 2026-11-13 · M4 uses a local model through Ollama on this Mac, not Google Cloud's $300 trial · the trial credit does not cover the AI Studio Gemini key, Vertex coverage is uncertain and short-lived, the categoriser cannot use Vertex tokens, and local keeps payee names on the Mac · owner

- 2026-11-13 · SBI NEO card added; SBI Card payment SMS without card digits go to review instead of defaulting to one card · two SBI cards make a default a guess · Claude, after the owner named the second card

- 2026-11-13 · Federal Bank / Fi is not forwarded from the phone (profile kept for old messages) · owner no longer uses Federal Bank · owner
- 2026-11-13 · Accounts tracked: ICICI, HDFC, HSBC (salary), SBI, Cash, two Axis cards, SBI SimplyCLICK and SBI NEO cards; bike loan planned. Digits kept only in accounts.yaml · owner's instruction · owner
- 2026-11-13 · seed_firefly also corrects last-4 and opening balance of existing accounts · lets the owner fill balances later and re-run · owner (asked to add balances later)

- 2026-11-13 · Federal Bank (FEDBNK, and Fi as FEDFIB) added as a bank profile · found in the owner's SMS backup with ~700 transactions · owner (supplied the backup)
- 2026-11-13 · Banks whose SMS name no account use BRIDGE_DEFAULT_ACCOUNTS (profile=last4) in .env · SBI Card payment-received and most Federal UPI SMS carry no account digits · Claude, within the approved M2 plan

- 2026-11-13 · Phone reaches the bridge over home Wi-Fi (bridge bound to the Mac's LAN address via docker-compose.lan.yml; Firefly stays local) · simplest for now; plain HTTP on the LAN, Tailscale or M7 HTTPS later · owner
- 2026-11-12 · SMS forwarder until Phase 2: "Incoming SMS to URL forwarder" (MIT), bearer token + HMAC signature · open source, retries, signs requests · owner (M2 approval)
- 2026-11-12 · Credit cards are Firefly asset accounts with the credit-card role · Firefly's own convention; net worth is unchanged · owner
- 2026-11-12 · Firefly III is the ledger; Django bridge handles ingestion, reconciliation and the advisor · avoids rebuilding accounting · owner
- 2026-11-12 · No Account Aggregator; data comes from SMS, email, statements, CAS and credit report · AA needs a regulated entity · owner
- 2026-11-12 · AI categoriser runs on the internal Docker network only · it has no built-in authentication · owner
- 2026-11-12 · Separate PostgreSQL databases and credentials for Firefly and the bridge · keeps Django migrations away from Firefly's schema · owner
- 2026-11-12 · No LLM container in M1; LLM deferred to M4 · free VM is too small to run a model beside the stack · owner
- 2026-11-12 · Pckt and indian-bank-sms-parser are references only · GPL-3.0 and very small projects · owner
