# Private Android notifications (P2.4)

The Android app uses Firebase Cloud Messaging (FCM). FCM is only a wake-up/reminder channel: push payloads contain an event kind and a route, never a payee, amount, transaction date, bank/card name, message text, or Google reconnect URL. The app fetches current details from the bridge after it opens, using the saved bearer token. Android lock-screen visibility is private.

## Phone

1. Build/install the current APK and open **Setup**.
2. Save the private server address and bridge API token.
3. Tap **Enable private notifications** and allow Android notifications.
4. Keep Tailscale connected when opening the app. The app registers/refreshes its FCM token only with the authenticated bridge.

The bridge stores the FCM registration token encrypted at rest. Removing the app or clearing app data stops automatic refresh; remove the device from the bridge with an authenticated `DELETE /api/v1/notifications/device` request if you need to revoke it sooner.

## Oracle sender credential

`google-services.json` is public client configuration; it cannot authorize the bridge to send pushes. The sender needs a separate Firebase service-account key with the **Firebase Cloud Messaging API Admin** role and the Firebase Cloud Messaging API enabled.

1. In Firebase Console, open **Project settings → Service accounts**, generate a new private key, and keep the downloaded JSON private.
2. Copy it directly to the Oracle host at `~/finance/secrets/firebase/service-account.json`; never put it in Git, a chat, the APK, or `.env`.
3. On Oracle, make the mounted file readable only to the bridge container's service user (UID 10001): `sudo chown 10001:10001 ~/finance/secrets/firebase/service-account.json && sudo chmod 400 ~/finance/secrets/firebase/service-account.json`.
4. Add `FCM_PROJECT_ID=<project-id-from-Firebase-project-settings>` to `~/finance/.env`, then deploy/restart the bridge, worker and beat containers.

The compose mount is read-only at `/run/firebase/service-account.json`. Without both the key and project ID, the sender reports itself disabled and no notifications are sent. FCM runs on Firebase's no-cost Spark plan; do not upgrade or enable billing for this setup.

## Delivery schedule

- Review/alert scan every 15 minutes; each event is sent once per device fingerprint.
- Weekly digest Monday at 08:05 India time.
- Category questions open **Review**. Other reminders open **Home**. The app refreshes details from authenticated bridge endpoints.
