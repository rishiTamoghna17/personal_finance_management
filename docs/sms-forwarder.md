# Phone setup: forwarding bank SMS to the bridge

Until the Phase 2 app exists, an Android app forwards bank SMS to
`POST /api/v1/ingest/sms`.

App: **Incoming SMS to URL forwarder** (MIT licence), from
[F-Droid](https://f-droid.org/packages/tech.bogomolov.incomingsmsgateway/) or its
[GitHub releases](https://github.com/bogkonstantin/android_income_sms_gateway_webhook/releases).
It is not on the Play Store, because Google does not allow SMS-forwarding apps there.
Play Protect may warn when you install it; that is expected for this kind of app.

## 1. Let the phone reach the bridge

Chosen for now (2026-11-13): **home Wi-Fi**. The bridge also listens on the Mac's
Wi-Fi address, set by `BRIDGE_LAN_IP` in `.env` (currently `192.168.0.106`), through
`docker-compose.lan.yml`. Firefly stays on `127.0.0.1`.

- The phone must be on the same Wi-Fi as the Mac. On mobile data, messages wait on
  the phone ("Store failed messages for retry") and go through once it is back home.
- In the forwarder rule, turn on **Local network mode** (advanced parameters), so it
  does not wait for a validated internet connection.
- Reserve the Mac's address in your router (DHCP reservation). If the address changes,
  update `BRIDGE_LAN_IP` and run `docker compose up -d bridge`; until then the bridge
  will not start on the new address.
- Traffic is plain HTTP on your Wi-Fi. The token and HMAC signature stop others from
  sending fake messages, but anyone on the same Wi-Fi who captures traffic can read
  the bank SMS. Tailscale (encrypted, free) removes this; M7 adds HTTPS.
- To go back to local-only, delete the `COMPOSE_FILE` and `BRIDGE_LAN_IP` lines from
  `.env` and run `docker compose up -d bridge`.

## 2. Turn off RCS

Google Messages can deliver messages over RCS, which the forwarder cannot see.
Google Messages → Settings → RCS chats → turn off.

## 3. Create one forwarding rule

| Field | Value |
| --- | --- |
| Sender | `(?i)-(HDFCBK\|HDFCBN\|HSBCIN\|AXISBK\|SBIUPI\|SBIPSG\|ATMSBI\|CBSSBI\|SBIINB\|ICICIT\|SBICRD\|MYSBIC)(-[A-Z])?$` with **Sender is a regular expression** ticked. It matches every bank sender found in your SMS backup, whatever the operator prefix (`JM-`, `AX-`, …). Add a new bank's 6-letter ID inside the brackets. Left out on purpose: `FEDBNK`/`FEDFIB` (Federal Bank / Fi, no longer used), `TNBPAY` (Tata Neu reminders), `SBIBNK` and `SBYONO` (SBI promotions), `FIMONY` (Fi app offers). Do not use `*`: it would send personal SMS to the bridge. |
| Text filter | `(?si)^(?!.*(is your otp\|otp is\|otp for\|one.?time.?pass\|verification code))` drops obvious OTPs on the phone. The bridge filters again, more strictly. |
| URL | `http://192.168.0.106:8000/api/v1/ingest/sms` (your `BRIDGE_LAN_IP`) |
| Headers | `{"Authorization": "Bearer <BRIDGE_API_TOKEN from .env>"}` |
| Sign with HMAC-SHA-256 | On. Secret: `BRIDGE_SMS_HMAC_SECRET` from `.env`. |
| Store failed messages for retry | On |
| JSON template | below |

```json
{
  "from": "%from%",
  "text": "%text%",
  "sentStamp": %sentStamp%,
  "receivedStamp": %receivedStamp%
}
```

Keep the rule export file private: it contains the token and the HMAC secret in plain text.

## 4. Keep the app alive

Allow autostart and turn off battery optimisation for the app. Xiaomi, Samsung and
other brands often kill background apps; the "F" icon in the status bar shows the
app is listening.

## What the bridge answers

| Response | Meaning |
| --- | --- |
| `202 accepted` | Stored; it will be parsed and posted. |
| `200 dropped` | It held an OTP, PIN, CVV, password or code. Nothing was stored. |
| `200 duplicate` | The same message was already received. |
| `401` | Wrong token or signature. The app will retry; fix the rule. |
| `400` | The JSON template is wrong. |
