# My Finance Android app

Native Android app in Kotlin and Jetpack Compose. The current P2.3 slice provides Home, Activity, Plans, Ask and Review screens, including category questions backed by your existing Firefly categories and optional payee rules. The app connects to the private bridge and keeps the API token encrypted with Android Keystore. It does not create or post ledger entries.

## Design direction

- Use Firefly III's green-ledger visual language and clear account/category hierarchy.
- Use Waterfly III's Material 3 dashboard cards and compact transaction-list patterns as visual inspiration only: <https://github.com/dreautall/waterfly-iii>.
- FireflyMobile is another Kotlin client reference, but this app remains a separate client for the versioned bridge API: <https://github.com/emansih/FireflyMobile>.
- No source code or assets are copied from those projects.

## Build in Docker

The Android SDK and Gradle are isolated in a separate Docker image; this does not install Java or Android tooling on the host or touch the finance service containers. From the repository root:

```sh
docker build --platform linux/amd64 -t my-finance-android-builder ./android-app
mkdir -p ./android-app/dist
docker run --rm --platform linux/amd64 \
  -v "$PWD/android-app/dist:/out" \
  -v "$HOME/.gradle:/root/.gradle" \
  my-finance-android-builder \
  sh -c 'gradle --no-daemon --no-watch-fs assembleDebug && cp app/build/outputs/apk/debug/app-debug.apk /out/my-finance-p2.3-debug.apk'
```

The first build downloads the pinned Android command-line tools, Android API 37 platform/build tools, Gradle dependencies, and compiles the debug APK. Output: `android-app/dist/my-finance-p2.3-debug.apk`. This debug APK is for personal sideloading; it is not a signed release build.

The app connects to `https://finance.tail1cee0a.ts.net` by default. The phone needs access to the owner's Tailscale network. Paste the existing bridge API token into the app once; the app stores the token encrypted with a key held by Android Keystore.
