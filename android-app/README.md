# My Finance Android app

Native Android app in Kotlin and Jetpack Compose. The first slice connects to the private bridge, keeps the API token encrypted with Android Keystore, and lets the owner review and label unparsed messages. It does not post ledger entries.

## Design direction

- Use Firefly III's green-ledger visual language and clear account/category hierarchy.
- Use Waterfly III's Material 3 dashboard cards and compact transaction-list patterns as visual inspiration only: <https://github.com/dreautall/waterfly-iii>.
- FireflyMobile is another Kotlin client reference, but this app remains a separate client for the versioned bridge API: <https://github.com/emansih/FireflyMobile>.
- No source code or assets are copied from those projects.

## Build

Open this `android-app` directory in Android Studio and allow Gradle sync. A JDK and Android SDK are required; neither is installed in the current development environment, so an APK has not yet been built here.

The app connects to `https://finance.tail1cee0a.ts.net` by default. The phone needs access to the owner's Tailscale network. Paste the existing bridge API token into the app once; the app stores the token encrypted with a key held by Android Keystore.
