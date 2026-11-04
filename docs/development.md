# Development

Monorepo layout:

| Path | What |
| --- | --- |
| `apps/api` | FastAPI backend (Python 3.12+, PostgreSQL, Redis, S3-compatible storage) |
| `apps/admin` | Admin + vendor web panel (React, TypeScript, Vite) |
| `apps/mobile` | Customer + companion app (Expo React Native, TypeScript) |
| `compose.yaml` | Local PostgreSQL, Redis, MinIO; optional full stack (`--profile app`) |

Commands below work in Windows PowerShell; POSIX alternatives are noted where they differ.

## Requirements

- Python 3.12+, Node.js 22+, Docker with Compose.

## 1. Infrastructure

```text
docker compose up -d postgres redis minio
```

Create the `yondo-local` bucket once in the MinIO console (http://localhost:9001,
user `yondo`, password `change-me-in-local-env`), or run the full stack below, which creates it.

## 2. API

```text
python -m venv .venv
.venv\Scripts\Activate.ps1            # POSIX: source .venv/bin/activate
cd apps/api
Copy-Item ..\..\.env.example .env     # POSIX: cp ../../.env.example .env
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m yondo_api.cli seed-demo     # optional demo accounts and content
uvicorn yondo_api.main:app --reload
```

In a second terminal (same virtual environment, from `apps/api`):

```text
python -m yondo_api.cli worker        # expiries, refunds, reminders, push delivery
```

- API docs: http://localhost:8000/docs (disabled in production).
- Liveness `GET /health`; readiness `GET /api/v1/health/ready`.
- In development `/auth/otp/request` returns the OTP (`development_otp`); it is never logged
  and never returned in staging/production.
- Payments use the local **sandbox** provider: the checkout URL opens a page with *Pay* and
  *Fail* buttons that sends a signed webhook. It is refused outside development/test.
- Without MinIO you can set `YONDO_STORAGE_BACKEND=local` (development only).

### Demo accounts (`seed-demo`)

| Role | Phone |
| --- | --- |
| Admin | +998 90 000 00 01 |
| Customer | +998 90 000 00 02 |
| Companions | +998 90 000 00 03 / 04 / 05 |
| Vendor | +998 90 000 00 09 |

Sign in with OTP; the development code is shown by the app/panel.

### First administrator in a real environment

The person signs in once with OTP, then an operator runs:

```text
python -m yondo_api.cli grant-admin +998901234567
```

## 3. Admin and vendor panel

```text
cd apps/admin
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

## 4. Mobile app

```text
cd apps/mobile
npm install
npm start            # Expo Go / emulator; `npm run web` for a browser preview
```

Set `EXPO_PUBLIC_API_URL` to an address the device can reach (for a phone, the computer's LAN
IP). The browser preview needs its origin in `YONDO_CORS_ALLOW_ORIGINS`.

## Full stack in Docker

```text
docker compose --profile app up -d --build
```

API http://localhost:8000, panel http://localhost:8080 (development mode, sandbox payments).

## Quality checks

From `apps/api`:

```text
python -m ruff check .
python -m pytest                                        # SQLite
$env:YONDO_TEST_DATABASE_URL="postgresql+psycopg://yondo:yondo@localhost:5432/yondo_test"
python -m pytest                                        # PostgreSQL (migrated test DB)
python -m alembic check
```

PostgreSQL-only tests (exclusion constraints, concurrent accepts/checkouts) are skipped on
SQLite. Create and migrate `yondo_test` first (`YONDO_DATABASE_URL=... alembic upgrade head`).

From `apps/admin`: `npm run typecheck`, `npm test`, `npm run build`.
From `apps/mobile`: `npm run typecheck`, `npm run export:web`.

Ruff formatting is configured; format files you edit with `ruff format path/to/file.py`. CI
does not enforce whole-tree formatting because older API files are not uniformly formatted.

Never commit `.env`, service-account files or real credentials.
