# Push notifications (owner request, 2026-11-18)

Yondo sends a short push when an in-app notification is created (booking request, accepted, declined, cancelled,
payment confirmed, new chat message, review reminder, gift order updates). It arrives while the app or site is closed.

- **Lock-screen text has no personal data:** title "Yondo", body like "Yangi bildirishnoma: bron qabul qilindi" (in the
  user's saved language: Uzbek 1995 / 2026 alphabet, Russian or English). A tap opens the booking, or the
  notifications list.
- **Permission is asked only after a tap:** web = the "Push bildirishnomalar" switch in Settings; Android = a one-time
  card after sign-in ("Yoqish" / "Keyinroq") and the same switch in Settings. Never on page load.
- **Sign-out** removes this device from the account. **Account deletion** removes all of the user's devices.

| Platform | Status | What it needs |
|---|---|---|
| Web (Chrome, Edge, Firefox, Android browsers, desktop Safari) | Works with no owner setup: the server makes its own Web Push (VAPID) keys once and keeps them in the database | nothing |
| iPhone / iPad, web | Only after "Add to Home Screen" (iOS 16.4+); the Settings switch explains this | nothing |
| Android app (APK) | Off until the owner's Firebase project is connected (steps below) | Firebase project, 2 secrets |
| iPhone app | **OUT OF SCOPE now**: needs a paid Apple Developer account (99 USD/year) and an iOS build | owner decision |

## Owner: one-time steps for Android push (about 15 minutes, free)

1. **Create a Firebase project.** Open https://console.firebase.google.com, sign in with your Google account,
   "Create a project", name it **Yondo**. Google Analytics is not needed (turn it off). The free **Spark** plan is
   enough: push messages cost nothing.
2. **Add the Android app.** In the project: "Add app" → Android icon. Package name exactly **`uz.yondo.app`** (it is
   in `apps/mobile/app.json`). Nickname "Yondo". The SHA-1 field can stay empty. Press "Register app".
3. **Download `google-services.json`** (the button on the next screen). Do **not** put it into the repository (the
   repository is public).
4. **Add it as a GitHub secret.** GitHub → the Yondo repository → Settings → Secrets and variables → Actions → "New
   repository secret". Name: **`GOOGLE_SERVICES_JSON`**. Value: open the downloaded file in Notepad, copy everything,
   paste. Save. The next "Mobile APK" build includes push.
5. **Create a service-account key for the server.** Firebase console → ⚙ Project settings → "Service accounts" →
   "Generate new private key" → a `.json` file downloads. It is a password: never send it in chat or e-mail.
6. **Put it into Render.** Render → yondo-demo → Environment → "Add environment variable".
   Key **`YONDO_FCM_SERVICE_ACCOUNT_JSON`**, value = the whole content of that file (copy everything from Notepad).
   Save; Render restarts the server. `YONDO_FCM_PROJECT_ID` is optional (the project id is read from the file).
7. **Check:** install the new APK, sign in, tap "Yoqish", allow notifications. Then from another account send a
   booking request to this one: the phone shows "Yondo — Yangi bildirishnoma: yangi bron so‘rovi".

If step 6 is skipped, the server log says `push: Android (FCM) not configured` and the app's switch says push is not
set up. If step 4 is skipped, the APK still builds; the switch then cannot get a token and says the same.

## How it works (for developers)

- **Backend** (`apps/api/src/yondo_api/push/`):
  - `push_devices` table (migration 0024): user, platform (`android` | `web`), FCM token or Web Push subscription
    (endpoint + p256dh + auth), `created_at`, `last_seen_at`, `disabled_at`. Unique per token and per endpoint; a
    token seen again moves to the account that signed in on that device.
  - `GET /api/v1/push/config` (public): `{web: {enabled, vapid_public_key}, android: {enabled}}`.
  - `PUT /api/v1/push/devices` (signed in, active account): register or refresh. Web endpoints must be https on a known
    push service (`YONDO_WEBPUSH_ALLOWED_HOSTS`): the server POSTs to them, so arbitrary URLs would be an SSRF hole.
  - `DELETE /api/v1/push/devices/{id}`: unregister (sign-out, switch off).
  - Delivery: an `after_commit` hook on the ORM session sees every `UserNotification` the transaction created and
    starts a background task. The request never waits for it; timeouts are 5 s (`YONDO_PUSH_SEND_TIMEOUT_SECONDS`);
    every error is logged without tokens, keys or message text, and swallowed. A rolled-back transaction sends nothing.
  - Invalid targets are disabled (`disabled_at`): Web Push 404/410, FCM 404/410/`UNREGISTERED`. Registering again
    re-enables them. Only active accounts receive pushes.
  - **Web Push** is implemented with `cryptography` only (VAPID ES256 JWT, RFC 8291 aes128gcm, checked against the RFC
    test vector). That is the one new dependency; `pywebpush` was not used because it is synchronous (`requests`) and
    pulls in three more packages.
  - **VAPID keys:** `YONDO_WEBPUSH_VAPID_PRIVATE_KEY` (raw P-256 scalar, base64url) wins. Without it the server
    generates a key pair once and stores it in `push_vapid_keys` (one row). Why: the owner would otherwise have to run
    a key-generation command, and a key generated per process would change on every Render restart, silently
    breaking every browser subscription. The private key is never logged and never returned by an endpoint (only
    the public key is published); it is as sensitive as the rest of the database, which already holds password
    hashes. To rotate: delete the row (all browsers must then turn the switch on again).
  - **FCM HTTP v1:** the service-account JSON signs an RS256 JWT, exchanged for a one-hour OAuth token (cached).
    Messages carry `notification` (title/body) + `data` (`url`, `kind`, `notification_id`) on channel `yondo`.
- **Web** (`apps/web`): `public/sw.js` (shows the push with the brand icon, opens the in-app path on click, same-origin
  paths only), `src/lib/push.ts`, `src/ui/PushToggle.tsx` in Settings, `public/manifest.webmanifest` (needed for
  "Add to Home Screen" on iPhone).
- **Mobile** (`apps/mobile`): `expo-notifications`; `src/push.ts`, `src/pushUi.tsx` (card, switch, tap routing,
  token refresh). Android channel "Yondo" with the **default system sound**: the custom sound of PR #44 was not on
  `main` when this was built. `app.config.js` adds Firebase only when `google-services.json` exists; the APK
  workflow writes it from the `GOOGLE_SERVICES_JSON` secret.

## What the tests cover, and what they cannot

- API (`tests/companions/test_push_notifications.py`, SQLite and PostgreSQL): config, VAPID key generated once,
  auth, validation, SSRF allowlist, unique devices, a booking notification pushed to web (payload decrypted as a
  browser would) and Android (FCM request checked), invalid-token pruning, provider timeouts not failing requests,
  rollback = no push, account deletion cleanup, texts per language.
- Web: vitest (permission states, subscribe/unsubscribe, sign-out) and an e2e step in real Chromium against the real
  API (only `PushManager.subscribe` is faked: headless Chromium has no push service).
- Mobile: typecheck, `e2e/push.mjs` on the web build with a fake `expo-notifications` (card, Yoqish, denied, Later,
  switch, sign-out), `expo export` for web and Android, `expo prebuild` with and without `google-services.json`.
- **Not tested here:** a real Android permission prompt, a real FCM token, a notification actually delivered to a
  phone, and a real browser push service. These need the owner's Firebase project and a phone (step 7 above).
