# Decisions

Add one entry whenever a design choice is made or the spec changes. Newest first. Never delete entries.

Format: date · decision · why · who approved

- 2026-11-13 · Phone reaches the bridge over home Wi-Fi (bridge bound to the Mac's LAN address via docker-compose.lan.yml; Firefly stays local) · simplest for now; plain HTTP on the LAN, Tailscale or M7 HTTPS later · owner
- 2026-11-12 · SMS forwarder until Phase 2: "Incoming SMS to URL forwarder" (MIT), bearer token + HMAC signature · open source, retries, signs requests · owner (M2 approval)
- 2026-11-12 · Credit cards are Firefly asset accounts with the credit-card role · Firefly's own convention; net worth is unchanged · owner
- 2026-11-12 · Firefly III is the ledger; Django bridge handles ingestion, reconciliation and the advisor · avoids rebuilding accounting · owner
- 2026-11-12 · No Account Aggregator; data comes from SMS, email, statements, CAS and credit report · AA needs a regulated entity · owner
- 2026-11-12 · AI categoriser runs on the internal Docker network only · it has no built-in authentication · owner
- 2026-11-12 · Separate PostgreSQL databases and credentials for Firefly and the bridge · keeps Django migrations away from Firefly's schema · owner
- 2026-11-12 · No LLM container in M1; LLM deferred to M4 · free VM is too small to run a model beside the stack · owner
- 2026-11-12 · Pckt and indian-bank-sms-parser are references only · GPL-3.0 and very small projects · owner
