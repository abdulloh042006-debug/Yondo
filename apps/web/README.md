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

## Security notes

* Roles in the UI are a convenience only. Every privileged endpoint authorizes on the server
  (`Admin` dependency) and every consequential admin action is written to `admin_audit_events`
  in the same transaction as the decision.
* Access/refresh tokens are kept in `sessionStorage` (cleared with the tab) and sent as bearer
  headers; nothing privileged is bundled. Admin code is a separate lazy chunk.
* Error text shown to people is chosen from the stable error `code`
  (`src/lib/messages.ts`), never from server message text.

See `docs/web-and-admin.md` for the verified feature matrix and known gaps.
