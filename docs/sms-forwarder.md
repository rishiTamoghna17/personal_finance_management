# Phone setup: forwarding bank SMS to the bridge

Until the Phase 2 app exists, an Android app forwards bank SMS to
`POST /api/v1/ingest/sms`.

App: **Incoming SMS to URL forwarder** (MIT licence), from
[F-Droid](https://f-droid.org/packages/tech.bogomolov.incomingsmsgateway/) or its
[GitHub releases](https://github.com/bogkonstantin/android_income_sms_gateway_webhook/releases).
It is not on the Play Store, because Google does not allow SMS-forwarding apps there.
Play Protect may warn when you install it; that is expected for this kind of app.

## 1. Let the phone reach the bridge

The bridge runs on the Oracle server. Tailscale Serve provides private HTTPS at
`https://finance.tail1cee0a.ts.net`; the phone and server must be connected to the
same Tailscale network. The Mac does not need to stay on, and no app port is exposed
to the public internet.

- Keep Tailscale connected on the phone. The forwarder can retry messages when the
  phone is offline; they should send once it reconnects.
- Use the HTTPS bridge URL below. Do not enable **Local network mode** for this
  Tailscale route.
- Traffic is encrypted by HTTPS inside the private tailnet. Keep the bearer token and
  HMAC secret private.

## 2. Turn off RCS

Google Messages can deliver messages over RCS, which the forwarder cannot see.
Google Messages → Settings → RCS chats → turn off.

## 3. Create one forwarding rule

| Field | Value |
| --- | --- |
| Sender | `(?i)-(HDFCBK\|HDFCBN\|HSBCIN\|AXISBK\|SBIUPI\|SBIPSG\|ATMSBI\|CBSSBI\|SBIINB\|ICICIT\|SBICRD\|MYSBIC)(-[A-Z])?$` with **Sender is a regular expression** ticked. It matches every bank sender found in your SMS backup, whatever the operator prefix (`JM-`, `AX-`, …). Add a new bank's 6-letter ID inside the brackets. Left out on purpose: `FEDBNK`/`FEDFIB` (Federal Bank / Fi, no longer used), `TNBPAY` (Tata Neu reminders), `SBIBNK` and `SBYONO` (SBI promotions), `FIMONY` (Fi app offers). Do not use `*`: it would send personal SMS to the bridge. |
| Text filter | `(?si)^(?!.*(is your otp\|otp is\|otp for\|one.?time.?pass\|verification code))` drops obvious OTPs on the phone. The bridge filters again, more strictly. |
| URL | `https://finance.tail1cee0a.ts.net/api/v1/ingest/sms` |
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
