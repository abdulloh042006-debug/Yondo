# Yondo API

FastAPI backend for Yondo. Python 3.12 or later is required.

The repository's `docs/development.md` covers local setup, `docs/api-overview.md` lists every
endpoint, `docs/business-policies.md` lists configurable policy placeholders and
`docs/companion-system.md` documents the Phase 6 companion domain.

From this directory (PowerShell or a POSIX shell):

```text
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m pytest
python -m ruff check --no-cache .
python -m pip wheel --no-deps --wheel-dir dist .
```

Operational commands:

```text
python -m yondo_api.cli grant-admin +998901234567   # bootstrap an administrator
python -m yondo_api.cli worker [--once]             # background jobs
python -m yondo_api.cli seed-demo                   # development demo data
```

Set `YONDO_DATABASE_URL` for your PostgreSQL database. Migration 0003 needs the
`btree_gist` extension; a DBA may provision it before running migrations.
The source distribution includes Alembic configuration, migrations, and tests.
The wheel contains the runtime application; deploy migrations from the source
checkout or source distribution alongside it (the Docker image includes both).

## Modules

| Module | Phase | Responsibility |
| --- | --- | --- |
| `auth` | 5 | Phone OTP, sessions, profile, roles, account activation |
| `companions` | 6 | Application, profile, services, photos, availability, approval gates |
| `discovery` | 7 | Search, filters, home sections, public profile, favorites |
| `bookings` | 8, 11 | Booking engine, contract, cancellation, meeting flow |
| `payments` | 9 | Checkout, providers, webhooks, refunds, payouts |
| `chat`, `realtime` | 10 | Booking chat, WebSocket fan-out |
| `reviews` | 12 | Two-way ratings and reviews |
| `safety` | 13 | Verification, reports, blocks, disputes, trusted contacts, SOS |
| `admin` | 14 | Admin API, moderation, analytics, audit log |
| `gifts` | 15–17 | Marketplace, one checkout, vendor panel API |
| `notifications`, `worker` | 18 | In-app/push notifications, reminders, background jobs |
