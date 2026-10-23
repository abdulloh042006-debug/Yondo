# Yondo web (`apps/web`)

React 19 + TypeScript + Vite single-page app: the public experience (discovery, companion
profiles, sign-in, bookings, account, companion studio) **and** the administrator console under
`/admin`. It talks only to the real FastAPI backend (`apps/api`) through `/api/v1`; there is no
mock data and no second backend.

## Run

```bash
# terminal 1 — API (see docs/development.md)
cd apps/api && alembic upgrade head && uvicorn yondo_api.main:app --reload
# terminal 2
cd apps/web && npm ci && npm run dev        # http://localhost:5173
```

`vite.config.ts` proxies `/api` to `YONDO_API_ORIGIN` (default `http://127.0.0.1:8000`), so the
browser is always same-origin and **no CORS relaxation is required**. In production route `/api`
to the API on the same origin with your reverse proxy.

## Scripts

| script | what it does |
| --- | --- |
| `npm run gen:api` | regenerates `src/api/schema.d.ts` from `docs/openapi-v1.json` (CI fails if stale) |
| `npm run lint` / `typecheck` / `test` / `build` | quality gates |
| `npm run e2e` | Playwright (Chromium) against the **real FastAPI app** on SQLite — see `e2e/server.py` |

## Design system

Glass surfaces (`.glass`, `.glass-bar`) over a slowly drifting colour field; three owner-approved
themes (**Gul**, **Jurnal**, **Stone**) are CSS custom properties on `[data-theme]`. Motion uses
the `motion` library (spring dialogs, shared-layout nav/filter pills, scroll reveals, counters,
cursor spotlight, pointer parallax) and honours `prefers-reduced-motion` globally
(`<MotionConfig reducedMotion="user">` + a CSS fallback).

## Languages (uz / ru / en)

The UI is Uzbek (Latin) by default and also available in Russian and English. Choose it in **Settings**
(stored in `localStorage['yondo.lang']`; there is deliberately no browser-language auto-detect).

* `src/i18n/uz.ts` is the source of truth; `ru.ts` and `en.ts` are typed `Record<Key, string>`, so `tsc`
  fails if a key is missing. Russian and English are lazy chunks.
* Use `t('area.key', { name })` (`{name}` interpolation; `{n, plural, one {# x} few {# y} other {# z}}` for
  counts). Never hard-code UI text, and never branch on translated text — error messages are looked up by the
  backend's stable error `code` (`err.<code>`), status/role/service labels by their codes (`lib/labels.ts`).
* Changing language re-renders in place (`App` calls `useLang()`; no remount), so typed form text, dialogs and
  the OTP step survive; `ApiError.message` is a lazy getter. The switch is `UZ | RU | EN` in the top bar
  (`i18n/LanguageSwitch.tsx`) plus the full-name picker in Settings.
* Uzbek has **two alphabets**: `uz.ts` is written in the **2026 alphabet** (law signed 2026-10-21, in force
  2027-04-22: `sh→ş ch→ç o‘→ö g‘→ğ`, `ng` = n+g, tutuq `ʼ` U+02BC) — write new `uz.ts` text that way. The
  **1995 alphabet** (o‘ g‘ sh ch) is derived from it by `toUz1995()` (one-to-one; verified to reproduce the old
  dictionary exactly). Settings → “Özbek alifbosi” chooses (`localStorage['yondo.uzAlphabet']`); the default is
  1995 before 2027-04-22 and 2026 from that day (`defaultUzAlphabet`). Unit tests pin 2026 in `test-setup.ts`.
* Signed in, the choice is also saved on the account (`PUT /auth/profile {ui_locale}`: `uz-Latn-1995`,
  `uz-Latn-2026`, `ru`, `en`) and applied on the user's other devices (`AuthContext`).
* Discovery search and the city filter match both alphabets on the server (`discovery/textfold.py`). `lib/format.ts` formats money/dates per language
  (dates stay in Asia/Tashkent).
* User-written text (bios, interests, notes) and backend messages are not translated.

## Profile, settings, help

* **Profile** (`/account`): header card, a menu (Bookings, Favorites, Companion studio, Help and safety, Settings),
  personal data, roles, sign out.
* **Settings** (`/settings`): language + Uzbek alphabet, appearance, account, privacy & safety, about (version).
* **Help and safety** (`/help`, also signed out; linked from the page footer): call 112, how to report, *my
  reports* (`GET /safety/reports`), trusted contacts (stored only — the app notifies nobody), FAQ, support status,
  closed-beta feedback (only if `GET /beta/me` succeeds).
* **Report a problem** on each booking (`ReportDialog`) sends only `booking_id`; the server derives the other
  participant, so a customer never needs a companion's user id.
* **Support** (in Help): in-app request form + "my requests" with replies; admins answer in `/admin/support`
  (audited). No e-mail or phone by owner decision.
* **Account deletion** (Profile → "Hisobni o‘chirish", linked from Settings): request with explicit confirmation →
  profile hidden, new bookings refused, cancellable → erased/de-identified by the scheduled job (`python -m yondo_api.jobs`, `infra/jobs/`) within 30 days
  (`/admin/deletions` shows requests and can run the job). Refused while bookings are open.
* **Legal**: `/terms` and `/privacy` render `src/legal/*.md` (owner drafts); an unticked consent box on login and a
  consent gate record the accepted version (`src/legal/versions.ts` = `account/legal.py`).
* **SOS** (`ui/Sos.tsx`): header button for signed-in users, also in Help and on confirmed/active bookings. The dialog
  is the confirmation step; 112 and trusted contacts are reached through the phone's own `tel:`/`sms:` links;
  location is read only after a tap and only goes into the SMS text; the moderator signal
  (`POST /safety/bookings/{id}/sos`) is offered only for an active meeting and never claims help was sent.
* **Block via booking**: "Bloklash" on each booking (`PUT/DELETE /safety/bookings/{id}/block`, state from
  `GET /safety/blocked-bookings`); new bookings between the two are refused, existing ones stay.
* Bookings that were never confirmed and whose start passed show as **expired** (slot released).
* Dialogs render through a portal (the glass top bar's `backdrop-filter` would otherwise clip them).
* Not available yet: reporting a profile without a booking; meeting check-in/start/end in the web app.

## Security notes

* Roles in the UI are a convenience only. Every privileged endpoint authorizes on the server
  (`Admin` dependency) and every consequential admin action is written to `admin_audit_events`
  in the same transaction as the decision.
* Access/refresh tokens are kept in `sessionStorage` (cleared with the tab) and sent as bearer
  headers; nothing privileged is bundled. Admin code is a separate lazy chunk.
* Error text shown to people is chosen from the stable error `code`
  (`src/lib/messages.ts`), never from server message text.

See `docs/web-and-admin.md` for the verified feature matrix and known gaps.
