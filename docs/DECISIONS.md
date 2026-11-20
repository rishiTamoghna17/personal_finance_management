# Decisions

- 2026-11-21 · Bind-mount the live Android project into the Docker builder and persist its debug signing key on the host · prevent stale APKs from the builder image's COPY snapshot and keep update signatures stable across builds · implementation decision
- 2026-11-21 · Display app version name and build number in the Home header and increment Android versionCode for each installable update · make it obvious which APK is installed during phone verification · owner
- 2026-11-20 · Use a custom adaptive wallet icon in the app's green/mint palette, with a monochrome layer for themed Android icons · make My Finance recognizable in the launcher without adding an icon dependency · owner
- 2026-11-20 · Show each card's masked last four digits and expiry on the wallet face; when expiry is unavailable, label it as not set rather than guessing · the owner wants every card face to show these familiar details, while card data remains minimal · owner
- 2026-11-20 · P2 wallet scanner: use the Android system camera and on-device OCR only to suggest issuer, nickname/cardholder, last four, and expiry; save only those fields plus chosen color and manually entered display balance in encrypted phone-local storage · never retain/send a card image, full card number, CVV or OCR text; manual wallet balances do not alter Firefly or net worth · owner
- 2026-11-20 · Saved card appearance may link to an existing Firefly credit-card account by account ID; linked cards display the Firefly ledger balance and latest bank-reported statement balance separately, while unlinked manual cards remain local-only. Credit limit/available limit are informational metadata and must retain issuer-wide scope when messages say they cover multiple cards; never count limits as assets or net worth · owner

- 2026-11-20 · When Gmail acct1 and Drive backups use the same Google identity and OAuth client, renew their existing `gmail.readonly` and `drive.file` permissions in one consent flow · avoid asking the owner to sign in twice; do not add scopes, and continue validating the same Google account · owner
- 2026-11-20 · Start P2 in Kotlin with Jetpack Compose and add owner-feedback learning for unparsed bank messages · the owner approved the spec change and Kotlin; feedback is stored against encrypted source messages and may guide only masked local examples, never transaction posting · owner
- 2026-11-20 · Use Waterfly III's Material 3 dashboard/list patterns and Firefly III's green ledger hierarchy as visual references for the native Kotlin APK; do not copy source or assets · Waterfly is Flutter and FireflyMobile is an older Kotlin client, while this app needs the bridge's review/feedback flow · implementation choice
- 2026-11-20 · Add authenticated read-only `GET /api/v1/transactions` with bounded pagination and structured INR ledger rows for the P2 app · P2.2 includes a transactions screen, but the bridge had no transaction-list endpoint; Firefly remains the ledger and all amounts stay integer paise · owner-approved P2 scope
- 2026-11-20 · Treat current categorized finance records as test data that the owner intends to clear after the app is built and begin fresh tracking · retain the records through development; before any purge, confirm scope and backup/export needs with the owner · owner

- 2026-11-19 · Show the Firefly interface as “My Finance” · a friendlier name for the owner's personal ledger · owner

- 2026-11-19 · Serve the Firefly ledger on the private Tailscale HTTPS port 8444 with the external APP_URL set accordingly · the owner wants the ledger dashboard usable directly from the phone/server, without an SSH tunnel; app ports remain loopback-only · owner

- 2026-11-19 · Use Tailscale Serve for private HTTPS from the phone; Oracle's app ports stay loopback-only · the owner has Tailscale on the phone and requested it for this deployment · owner

Add one entry whenever a design choice is made or the spec changes. Newest first. Never delete entries.

Format: date · decision · why · who approved

- 2026-11-18 · M7 deployment target returned to the Oracle Always Free eligible VM (A1 Flex 2 OCPU/12 GB, 100 GB boot volume); account remains on its limited/free tier. Tailscale is not enabled while the owner decides whether it is needed for secure phone access · the Acer spare laptop's fan noise made it unsuitable; app ports remain private until a secure HTTPS route is selected · owner
- 2026-11-18 · Persist Firefly OAuth signing keys in a named Docker volume and include that volume in encrypted restic backups · the first Oracle restore showed that container-local keys are required to keep the existing Firefly API token valid after restore/recreation · implementation during M7
- 2026-11-17 · M7 hosting target changed from Oracle Always Free to the Acer home server; Ubuntu Server 26.04.1 x86_64 with Lubuntu minimal, Docker Compose, and Tailscale · Oracle VM creation repeatedly failed for lack of capacity; the owner chose to use the spare laptop · owner
- 2026-11-17 · Keep the Acer system disk unencrypted for M7 · the owner chose to continue without LUKS; this accepts physical-access risk and avoids a boot-time unlock step · owner

- 2026-11-15 · Payments without a category become questions to the owner (alert now, phone notification in Phase 2); "always for this payee" creates a Firefly rule, so Firefly stays the place where categorisation lives · owner wants to be asked after each uncategorised payment · owner ("Approved")

- 2026-11-14 · Google sign-in apps stay in "Testing"; reconnect reminders from day 3 through /api/v1/alerts (to become phone notifications in the Phase 2 app) · publishing needs a public home page and privacy policy, which the owner did not want · owner

- 2026-11-14 · Backups: restic, encrypted on the server, stored in Google Drive with `drive.file` access only · owner wants them in Drive; Drive only sees encrypted data and only the backup folder · owner
- 2026-11-14 · Stored SMS/email bodies encrypted at rest with BRIDGE_ENCRYPTION_KEY · a database copy or backup should not reveal message text (M2 note) · Claude, within M7
- 2026-11-14 · M7 hosting: Oracle Always Free Arm with the local AI kept loaded; Tailscale for private HTTPS · free, always on; keeping the model loaded is real use and keeps the instance from being reclaimed as idle · owner

- 2026-11-14 · Spec change: no Telegram. The advisor (chat, digest, alerts) is a bridge API used by the Phase 2 app's chat screen; a temporary local test chat page is used until then. M6 renamed "Advisor API" · owner wants one chatbot in the APK, not Telegram · owner ("yes" to the proposed spec change)

- 2026-11-14 · Investments are Firefly asset accounts revalued to the monthly CAS value (tag `valuation`, counterparty "Market value change"); SIP debits are transfers into them · keeps Firefly's net worth complete without inventing prices (rule 9); no AMFI NAV feed · owner
- 2026-11-14 · Groww Trade API not used · trading API (keys can place orders), stocks only, no current value on the free tier, daily token expiry · owner
- 2026-11-14 · Card dues and EMI schedules live in the bridge; EMIs are also Firefly bills; card dues are not bills (amount changes monthly) · fixed EMI amounts suit bills, card dues do not · Claude, within M5
- 2026-11-14 · Goal progress = money in the goal's linked accounts, refreshed daily · no manual piggy-bank entries to forget · Claude, within M5

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
