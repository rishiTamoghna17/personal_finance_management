# Deployment guide (M7)

How to run the finance agent on an always-on server (Oracle Cloud Always Free, Arm), reach it privately from the
phone with Tailscale, and keep encrypted backups in Google Drive. Everything here is free. If any step asks for
money, stop: nothing in this project needs a paid plan.

Steps marked **(you)** need your own accounts or sign-ins; nothing else does.

## 0. Before you move anything (on the Mac)

1. **Back up and test the backup.**
   ```bash
   sh scripts/gdrive-connect.sh
   ```
   ```bash
   docker compose up -d --build backup && docker compose exec backup backup.sh maintain
   ```
   ```bash
   sh scripts/restore-drill.sh
   ```
   The drill must end with `RESTORE DRILL PASSED`.
2. **Export the secrets** (one encrypted file; you type a passphrase):
   ```bash
   sh scripts/export-secrets.sh
   ```
   Put `finance-secrets-YYYYMMDD.enc` and its passphrase in your password manager, then delete the file from the Mac.
   Without it, the backups and the stored Gmail tokens and statement passwords cannot be read.
3. **(you) Google sign-in apps to production.** In Google Cloud Console, for *both* projects: APIs & Services >
   OAuth consent screen > Audience > **Publish app**. Google will show "Google hasn't verified this app" at sign-in;
   that is expected for a personal app. This stops Gmail and Drive tokens from expiring every 7 days. Then reconnect
   each mailbox once (`gmail_connect`, see README) and run `scripts/gdrive-connect.sh` again.

## 1. (you) Create the Oracle server

1. Sign up at cloud.oracle.com (card needed for identity only). Choose a home region close to India (Mumbai or
   Hyderabad); it cannot be changed later.
2. Compute > Instances > Create: image **Ubuntu 24.04 (aarch64)**, shape **VM.Standard.A1.Flex, 2 OCPU, 12 GB**
   (the whole Always Free Arm allowance). If it says "out of capacity", try another availability domain or later.
3. Keep the boot volume at 50-100 GB (Always Free covers 200 GB in total). Add your SSH public key.
4. Networking: leave only SSH (22) open in the security list. Nothing else is opened, ever: the phone and you reach
   the server through Tailscale. After step 2 below you can close 22 as well and use Tailscale SSH.
5. Optional: Billing > Budgets: a budget of ₹1 with an email alert, so any charge is noticed at once.

## 2. Server setup (over SSH)

```bash
sudo apt-get update && sudo apt-get -y upgrade
```
```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker ubuntu
```
```bash
curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up --ssh --hostname finance-admin
```
(Host Tailscale is only for your SSH access. The bridge has its own Tailscale container, as on the Mac.)
Log out and in again (for the docker group), then:
```bash
git clone https://github.com/rishiTamoghna17/personal_finance_management.git finance && cd finance
```
Copy `finance-secrets-YYYYMMDD.enc` to the server (for example with `scp` over Tailscale) and unpack it:
```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in finance-secrets-YYYYMMDD.enc | tar -xzf -
```
In `.env` on the server: remove the `COMPOSE_FILE` and `BRIDGE_LAN_IP` lines (no Wi-Fi binding on a server), and
set `FIREFLY_APP_URL` as in step 4.

## 3. Restore the data from the latest backup

```bash
docker compose up -d postgres
```
```bash
docker compose run --rm --no-deps -v finance-restore:/restore --entrypoint restic backup restore latest --host finance-server --target /restore
```
```bash
docker run --rm --network finance_internal -v finance-restore:/restore:ro -e PGPASSWORD="$(grep ^POSTGRES_PASSWORD= .env | cut -d= -f2)" postgres:17-alpine sh -c 'for db in firefly bridge; do pg_restore -h postgres -U postgres -d $db --clean --if-exists /restore/tmp/backup-work/$db.dump; done'
```
The bridge files (statements as received) and the categoriser settings are under `/restore/backup/`; copy them into
the `bridge_data` and `categorizer_data` volumes the same way. Then start everything:
```bash
docker compose up -d --build
```
The model is downloaded once (the `ai` network has no internet, so attach it for the download only):
```bash
docker network connect finance_internal finance-ollama-1 && docker compose exec ollama ollama pull qwen2.5:3b && docker network disconnect finance_internal finance-ollama-1
```

## 4. Private HTTPS with Tailscale

The `tailscale` service in docker-compose gives the bridge `https://finance.<tailnet>.ts.net` (and the test chat page on
`:8443`), visible only to your own Tailscale devices. On the Mac it is already logged in; its login lives in the
`tailscale_state` volume. On the new server:
1. **(you)** In the Tailscale admin console, remove the old `finance` machine (the Mac's container) so the name is free,
   and generate a new auth key (Settings > Keys; not reusable, not ephemeral).
2. `sh scripts/set-secret.sh TS_AUTHKEY`, then `docker compose up -d tailscale`. Remove `TS_AUTHKEY` from `.env` after
   the first start.
3. `PUBLIC_BASE_URL` stays `https://finance.<tailnet>.ts.net`, so the phone forwarder URL and the Google web clients'
   redirect URI do not change.

## 5. (you) Phone

1. Install Tailscale on the phone and sign in with the same account. Allow it to run in the background (battery:
   unrestricted).
2. The SMS forwarder already posts to `https://finance.<tailnet>.ts.net/api/v1/ingest/sms` (set on 2026-11-15);
   nothing changes when the server moves. Press Test after the move: it must answer 202.
3. Messages that failed while moving are kept by the forwarder; use its resend.

## 6. Check it

- `docker compose ps`: every service up.
- `https://<server>.ts.net/api/v1/health` with the token: 200.
- `GET /api/v1/alerts`: no `job_stopped`, `backup_*` or `sms_quiet` alerts after a day.
- Next morning the backup container log shows `backup: ok`.

## Everyday

| Task | Command |
| --- | --- |
| Update after a `git pull` | `docker compose up -d --build` |
| Backup now | `docker compose exec backup backup.sh maintain` |
| List backups | `docker compose run --rm --entrypoint restic backup snapshots` |
| Restore drill | `sh scripts/restore-drill.sh` |

## Idle reclamation (Oracle)

Oracle stops (does not delete) an Always Free instance only if CPU, network **and** memory all stay low for 7 days.
The model is kept loaded (`OLLAMA_KEEP_ALIVE=-1`, about a quarter of the memory), so the server is not idle in
normal use. If it is ever stopped, start it again in the console; the data is on its disk and in the backups.
