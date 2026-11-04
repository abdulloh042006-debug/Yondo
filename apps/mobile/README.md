# Yondo mobile app

Expo (React Native + TypeScript) client for customers and companions. Vendors and
administrators use the web panel in `apps/admin`.

## Run locally (Windows PowerShell or POSIX shell)

```text
npm install
npm start          # Expo dev server; open in Expo Go or an emulator
npm run web        # browser preview
```

The API address is read at build time from `EXPO_PUBLIC_API_URL` (default
`http://localhost:8000`). On a phone use your computer's LAN address, e.g.
PowerShell: `$env:EXPO_PUBLIC_API_URL="http://192.168.1.10:8000"; npm start`.
For the browser preview add `http://localhost:8081` to the API's `YONDO_CORS_ALLOW_ORIGINS`.

## Checks

```text
npm run typecheck
npm run export:web   # static web build into dist/ (smoke test of the bundle)
```

## Features

- Phone OTP sign-in, profile completion (name, age, gender, city) and role selection.
- Home sections (available today, nearby, top rated, new, recommended, flowers, gifts),
  search with filters, companion profile with photos, services, reviews, favorite,
  report and block.
- Booking flow: service → duration → date → time (from free slots) → meeting place →
  summary with price breakdown and cancellation rules → contract acceptance → request.
- Booking detail with server-driven actions: pay (optionally adding flowers delivered to
  the meeting place), cancel with refund preview, accept/decline, I'm here, start/end
  meeting, SOS, share with a trusted contact, chat, review, no-show, dispute, book again.
- Realtime booking chat (WebSocket with polling fallback), text and photos.
- Gifts catalog, product page, cart, delivery checkout and order tracking.
- Profile, ID + selfie verification, notifications, favorites, Safety Center
  (SOS, emergency numbers, trusted contacts, guide).
- Companion panel: status and blockers, application and profile, services and prices,
  availability, photos, approximate area, booking requests and earnings.

## Release prerequisites (need project credentials)

- Firebase project: `google-services.json` (Android) / APNs key (iOS) for push.
- App icons/splash from the final brand design; store listings.
- Production API URL and EAS build configuration (`eas.json`).
