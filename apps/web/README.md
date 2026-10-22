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
* Uzbek text follows the **2026 alphabet** (law signed 2026-10-21, in force 2027-04-22): `sh→ş ch→ç o‘→ö g‘→ğ`,
  `ng` is plain n+g, tutuq is `ʼ` (U+02BC). Write new `uz.ts` text that way. `lib/format.ts` formats money/dates per language
  (dates stay in Asia/Tashkent).
* User-written text (bios, interests, notes) and backend messages are not translated.

## Security notes

* Roles in the UI are a convenience only. Every privileged endpoint authorizes on the server
  (`Admin` dependency) and every consequential admin action is written to `admin_audit_events`
  in the same transaction as the decision.
* Access/refresh tokens are kept in `sessionStorage` (cleared with the tab) and sent as bearer
  headers; nothing privileged is bundled. Admin code is a separate lazy chunk.
* Error text shown to people is chosen from the stable error `code`
  (`src/lib/messages.ts`), never from server message text.

See `docs/web-and-admin.md` for the verified feature matrix and known gaps.
