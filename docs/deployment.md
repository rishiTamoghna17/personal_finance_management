# Deployment guide (M7)

## Target

The current target is the Oracle Cloud VM `finance-server` in Hyderabad: Ubuntu 24.04 ARM64, VM.Standard.A1.Flex (2 OCPU, 12 GB RAM), with a 100 GB boot volume. It was created as an Always Free eligible configuration. The Oracle account has not been upgraded to Pay As You Go. The budget amount is 1 in OCI billing units; it is an email alert, not a spending cap.

For a replacement VM, keep the same ARM shape and boot volume within the remaining Always Free allowance. Leave router forwarding off and open only the SSH rule needed for setup. Do not accept a paid upgrade or add resources outside the free allowance. Oracle's budget notifications warn about spend; they do not block it.

## Current deployment state (last verified 2026-11-20)

- The project is cloned at `~/finance` on the VM. The `.env`, `accounts.yaml`, `goals.yaml`, Google client files, and Firefly OAuth signing keys were transferred over SSH; file permissions are restricted to the VM account.
- The latest Drive snapshot `ac4afbd9` was restored to both PostgreSQL databases and the bridge and categoriser data volumes. The restored ledger has 29 Firefly journals and the bridge has 104 raw messages and 29 ledger entries.
- Docker Compose is installed. Firefly 6.7.9, PostgreSQL, Redis, bridge, both Nginx UIs, categoriser, Ollama, Firefly cron, and the Drive backup scheduler are running. Django system check and authenticated bridge health pass.
- `qwen2.5:3b` is stored in the Ollama volume. Ollama and the categoriser are attached to `finance_ai` (`internal: true`); the model was downloaded during setup and Ollama was detached from the ordinary network afterwards.
- The first encrypted Oracle-to-Drive backup succeeded: snapshot `b180312e`. Firefly OAuth signing keys are now persisted in a named volume and included in subsequent encrypted backups.
- Compose publishes Firefly, bridge, and the two UIs only on `127.0.0.1` (ports 8080, 8000, 3010, and 3020). The Oracle security list has temporary SSH ingress limited to the current home public IP. No app ports are open to the internet.
- The owner selected Tailscale for private HTTPS. `PUBLIC_BASE_URL` is set to `https://finance.tail1cee0a.ts.net`, and the Celery worker and beat are running. Oracle joined the tailnet as `finance`; Tailscale Serve routes the bridge at HTTPS port 443, the advisor test page at port 8443, and Firefly at port 8444. The one-use auth key was removed from both `.env` files after joining. Phone SMS was accepted with HTTP 202 and the advisor page was confirmed working from the phone. Keep the Mac deployment paused as rollback; do not run ingestion on two hosts at once.
- **M7 close verification (2026-11-20):** all Compose services were running and `manage.py check` passed. The latest Drive snapshot `3041c41b` was restored to a throwaway PostgreSQL on Oracle: bridge 126 raw messages / 38 entries and Firefly 31 journals / 32 accounts matched live counts; 133 bridge files restored. Temporary restore resources were removed. Fifteen SMS records, two email records and four PDF records arrived in the prior 24 hours; the latest SMS was parsed. The alert builder produced six category questions and three Google reconnect alerts. All three background-job heartbeats were current. Host app ports remained loopback-only and the AI network remained internal-only. Twenty-nine review items remain open for owner action; none were auto-dismissed as part of deployment closure.
- **P2.2 app API deployment (2026-11-20):** commit `c03b22a` was deployed with `git pull --ff-only` and `docker compose up -d --build`. Django system check passed. Authenticated read-only `GET /api/v1/transactions?start=2026-11-01&end=2026-11-20&page=1&limit=1` returned HTTP 200 with the expected pagination fields. No ledger or bridge records were modified.

## Rebuild and restore

On a replacement Ubuntu 24.04 ARM VM, install Docker Engine and Compose from Docker's official Ubuntu repository, clone the project into `~/finance`, and transfer `.env`, `accounts.yaml`, `goals.yaml`, and `secrets/` over SSH. Keep those files owner-only; never commit them. `scripts/export-secrets.sh` can create a passphrase-encrypted archive for a later disaster recovery. Type the archive passphrase only into its hidden prompt.

Restore the latest encrypted restic snapshot from Google Drive. It contains the Firefly and bridge database dumps, PostgreSQL roles, the Firefly storage volume (including OAuth signing keys), bridge statement files, and categoriser settings. Restore the two database dumps and all three data volumes before enabling bridge background jobs. Use `scripts/restore-drill.sh` on a disposable local environment to rehearse and compare row counts. Then check `docker compose exec bridge python manage.py check`, `migrate --check`, and authenticated `GET /api/v1/health`.

Download the model only during setup. `finance_ai` is `internal: true`; temporarily connect Ollama to `finance_internal` to run `ollama pull qwen2.5:3b`, then disconnect it. Verify `docker network inspect finance_ai --format '{{.Internal}}'` prints `true`.

## Local administration through SSH

From the Mac, open a tunnel:

```bash
ssh -N -L 8080:127.0.0.1:8080 -L 3010:127.0.0.1:3010 -L 3020:127.0.0.1:3020 ubuntu@<Oracle-public-IP>
```

Then open Firefly at `http://127.0.0.1:8080`, categoriser at `http://127.0.0.1:3010`, or the advisor test page at `http://127.0.0.1:3020`. Keep the SSH tunnel running while using them. SSH is currently allowed only from the home network address entered in the OCI security list.

For phone access, Tailscale Serve is configured in Compose and the selected route is `https://finance.tail1cee0a.ts.net`. Do not publish or bind ports 8000, 8080, 3010, or 3020 to a public interface. The worker and beat are running; SMS cutover waits until the Oracle VM is joined to Tailscale and the phone forwarder is updated.

## Backup and restore

The `backup` container stores encrypted restic snapshots in Google Drive (`personal-finance-backups`). It backs up both PostgreSQL databases and roles, the Firefly storage volume (including its OAuth signing keys), bridge statement files, and categoriser settings. It runs nightly at 02:30 IST with hourly catch-up; weekly retention maintenance also checks the repository.

Check backups and service state:

```bash
cd ~/finance
docker compose ps
docker compose exec backup cat /status/last.json
docker compose exec backup restic snapshots
```

After code updates, fetch the reviewed source and rebuild the services:

```bash
cd ~/finance
git pull
docker compose up -d --build
```

Keep the Mac copy until the chosen HTTPS route, phone SMS forwarder, Gmail polling, and Drive backup have all been verified on Oracle.

## Phone and scheduled jobs

The private phone routes are `https://finance.tail1cee0a.ts.net` (bridge API), `https://finance.tail1cee0a.ts.net:8443/` (advisor test page), and `https://finance.tail1cee0a.ts.net:8444/` (Firefly ledger). `PUBLIC_BASE_URL` is set to the bridge URL. The phone forwarder uses `/api/v1/ingest/sms`; a test message was accepted with HTTP 202 and sent to review because its sender was unknown. Keep app ports loopback-only.

Tailscale Serve runs in Compose and gives private HTTPS without opening the app ports. Oracle joined as `finance`; the persistent node identity is stored in the `tailscale_state` volume. The temporary auth key has been removed from `.env` on the Mac and Oracle.

## Oracle idle policy

Keep Ollama's configured `OLLAMA_KEEP_ALIVE=-1` so the model stays loaded for actual use; do not run a CPU-burning keepalive task. If Oracle stops an Always Free instance, start it again in the console and verify it from SSH. The Drive backups remain the recovery copy.
