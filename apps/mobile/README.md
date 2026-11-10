# Yondo mobile app (Expo / React Native)

One app for every role: a customer books, a companion accepts the booking in the same app. The owner has not decided yet between one app with role modes and two separate apps. One app is the working default because `apps/web` works the same way, and the choice can be changed later.

## What it has

| Area | Screens | Rules it keeps |
| --- | --- | --- |
| Discovery | list with search and service filter, companion profile | the verified badge only when the API says `verified: true`; photos come from short-lived signed URLs |
| Sign-in | phone, then the one-time code (Telegram Gateway in production), Terms/Privacy consent with versions | the on-screen code exists only in development; the consent gate also asks again after a document update |
| Booking | form with exactly the 5 API fields (service, start instant, duration, place, `Asia/Tashkent`) | Tashkent wall time is sent as an explicit `+05:00` instant |
| Bookings | list and detail; a companion accepts or declines; cancel | |
| Payment | "Go to payment" only for `accepted`, opens the provider's `checkout_url` | one `Idempotency-Key` per booking, kept on the device; 503 is shown as "unavailable", never as "declined"; no money logic in the app |
| Safety | report and block **via `booking_id`** (the app never sees the other side's user id); SOS dialog | SOS offers 112 and trusted contacts through the phone's own dialer and SMS app, plus a moderator signal for an active meeting; it never claims help was sent |
| Settings | language uz / ru / en, Uzbek alphabet 1995 / 2026, theme | the language follows the account (`users.ui_locale`) |

**Brand.** Only paper `#F5F2EC`, ink `#111111` and carrot `#E8501A`, in the themes `yondo` (day) and `yondo-tun` (night), or following the phone's setting. Carrot never carries small text: it is used for borders, dots and fills with ink text. The icons are copied from `design-prototype/brand/logo/png`.

**One source of text.** The app imports these from `apps/web/src`, so they are written in one place only:
- the uz / ru / en dictionaries (`uz.ts` in the 2026 alphabet, 1995 derived);
- money and date formatting (integer tiyin, Tashkent time);
- error messages chosen by the API error `code`;
- the labels;
- the legal document versions.

`metro.config.js` makes those shared files use this app's React. New mobile texts are the `mobile.*` keys in the web dictionaries.

**Not in the mobile app yet** (they work in the web app; Settings links there when `EXPO_PUBLIC_WEB_URL` is set):
- chat;
- meeting check-in;
- reviews;
- favourites;
- notifications and push;
- the companion studio (profile, services, photos, availability);
- trusted-contact editing;
- support;
- account deletion;
- gifts;
- location in SOS.

## Run

```bash
cd apps/mobile
npm ci
cp .env.example .env    # EXPO_PUBLIC_API_URL: on a phone use the computer's LAN address or the HTTPS API, not localhost
npx expo start          # scan the QR code with Expo Go
```

## Checks

```bash
npm run typecheck                                   # also checks the shared apps/web modules
npx expo export --platform web --output-dir /tmp/m  # Metro bundle (CI job "Mobile app typecheck and bundle")
# Smoke test of the web build against the real API (DEMO seed, development OTP, no payment provider):
cd ../web && YONDO_WEB_DIST=/tmp/m PYTHONPATH=../api/src python e2e/server.py 8765 /tmp/m.db &
cd ../mobile && MOBILE_URL=http://127.0.0.1:8765 node e2e/smoke.mjs
```

`e2e/smoke.mjs` uses a 390 px phone viewport and the English UI. It covers:
- discovery;
- sign-in;
- the booking with exactly 5 fields and the 18:30 Tashkent → 13:30Z conversion;
- a report sent with `booking_id` only;
- the companion accepting the booking;
- payment answering 503, shown as unavailable and sent with the same idempotency key twice;
- language, alphabet and night theme switching;
- axe (WCAG A/AA) on four screens;
- no horizontal scroll;
- no console errors.

It has not been run on a real iOS or Android device yet.
