# Public demo deployment (free hosting)

One container = the real Yondo API + the built web app (`apps/web`) on **one port** (`/api/*` is the API, everything else is the web app).
Files: [`Dockerfile`](Dockerfile), [`demo/`](demo) (the harness: `demo_app.py`, `demo_payment.py`, `demo_persist.py` and their tests),
[`../../render.yaml`](../../render.yaml) (Render Blueprint), [`../../.dockerignore`](../../.dockerignore).
The e2e suite (`apps/web/e2e/server.py`) is a thin entry point to the same `demo/demo_app.py`, so what is tested is what ships.

## What this is — and is not

This is a **demo**, not production. `demo/demo_app.py` runs the real API with these test doubles:

| Real production code | Test double (demo only) |
|---|---|
| authz, booking/safety/support state machines, audit trail, discovery | OTP: the code is **shown on screen** (no SMS provider exists yet) |
| web app, admin console, i18n | photos: in-memory (not stored, not served) |
| | identity check: always "verified" |
| | database: throw-away SQLite in `/tmp`, re-seeded with DEMO data at every start (**kept instead in persistent mode**, below) |
| | payment: `demo/demo_payment.py`, a stand-in for CLICK/Payme (see below) |

### DEMO payment (until real CLICK/Payme keys exist)
When `YONDO_DEMO_PUBLIC_URL` (or Render's `RENDER_EXTERNAL_URL`) is set, "To‘lovga o‘tish" creates a checkout whose link opens the web
app's own DEMO page (`/demo-pay/<reference>`, translated like the rest of the app). Only the **paying customer's** session can use it:
"To‘lovni tasdiqlash" sends a signed event to the real `/payments/webhook` route and the booking becomes "Tasdiqlangan"; "Rad etish"
fails the payment. **No money moves.** The platform fee is the labelled DEMO value 0 — the real fee, cancellation and refund rules are still
the owner's decision. Without the URL the API answers 503 "sozlanmagan" as before.
Real CLICK/Payme later = a new provider class behind the same `PaymentProvider` interface (`apps/api/src/yondo_api/payments/provider.py`)
plus the owner's merchant keys in the host's environment variables (never in git).
Checks: `demo/test_demo.py` (in CI) and, against a running server started with the DEMO payment provider and the web app,
`python infra/deploy/demo/demo_payment_check.py <port | https://origin>` (re-runnable).

### Risks you accept by publishing it
- Because the OTP is on screen, **anyone who opens the URL can sign in as any phone number**, including the admin. Mitigation built in: set `YONDO_DEMO_ADMIN_PHONE` to a private, unguessable number (any spelling the API accepts; it replaces the well-known `+998901110001`; nobody else knows which number is the admin). If it is **not** set, the public image fails closed: the admin gets a random unknown number, so nobody can open the admin console (set the variable when you need it). A malformed value stops the start with a clear message. Check after every deploy that `+998901110001` gets 403 on `/api/v1/admin/summary`.
- **Do not enter real phone numbers or personal data.** With the default throw-away SQLite everything disappears at the next start, but in **persistent mode every phone number, booking and chat stays in the database** until an account-deletion request is processed (the 15-minute loop does that after the 30-day window). Treat the site as public either way.
- The legal pages are still drafts (operator name "hali ko‘rsatilmagan"); see `docs/legal/pre-publication-checklist.md`.
- Not included: realtime chat (the socket needs Redis; the web app polls every 8 s instead) and photo storage (no S3 adapter yet).

A real launch still needs the owner items in `docs/WORKLOG.md` → Next steps (operator name, SMS provider, payment provider and fee policy, backups, PostgreSQL, S3/MinIO storage).

## Persistent mode: keep the data between restarts (free PostgreSQL, e.g. Neon)

Set **`YONDO_DEMO_DATABASE_URL`** (a secret: only in the host's environment, never in git or chat) and the same image keeps its data
(`demo/demo_persist.py`; an empty value counts as unset):
- the schema comes from the real Alembic migrations (`alembic upgrade head` at every start, a no-op when current);
- the DEMO seed runs only into an **empty** database and is bracketed by a state marker (table `demo_seed_state`): later starts keep accounts,
  bookings, chats and reviews, while a start that died halfway through seeding (e.g. a redeploy during the first seed) is wiped and seeded
  again — nobody can have used a database that was never served. Users without any marker are left alone, never wiped;
- once the server is serving, and then daily, DEMO Madina and DEMO Jasur get 10:00–22:00 (Tashkent) availability for the next 14 days
  (the seed window is a single evening, so without this the demo would stop taking bookings after two days);
- a loop every 15 minutes does what `infra/jobs` does hourly in production (booking expiry, due account erasures);
- **admin = exactly `YONDO_DEMO_ADMIN_PHONE`** (nobody if unset): the well-known test number, a changed number and the random seed admin
  lose the admin role at every start, so a database first filled by a local run cannot leak an admin;
- the log line `PERSISTENT_MODE=on|off` at every start shows which mode is active.

Neon setup (about 5 minutes, you sign in yourself):
1. neon.com → sign up → **Create project** (name `yondo-demo`, PostgreSQL 16 or 17). Pick the Neon region closest to your Render
   service's region (Render → `yondo-demo` → Settings → Region; the default is Oregon = Neon "AWS US West 2").
2. On the project page press **Connect**, turn **Connection pooling OFF** (use the *direct* string; the pooled `-pooler` host may
   break prepared statements) and copy the `postgresql://…?sslmode=require` string. A `psql '…'` line is also accepted.
3. Render → `yondo-demo` → **Environment**: `render.yaml` declares `YONDO_DEMO_DATABASE_URL` (and `YONDO_DEMO_ADMIN_PHONE`) without a value,
   so Render asks for it on the next Blueprint sync, or add/edit it by hand → paste the string → **Save** (Render redeploys).
4. Check: the logs say `PERSISTENT_MODE=on`; make a booking, then **Manual Deploy → Deploy latest commit**; the booking must still be there.
   The first start takes longer (migrations + seed).

Free limits to know: Neon suspends the compute after ~5 idle minutes (the first query after that adds about a second) and the free
project is small (0.5 GB); both are plenty for a demo.

## Try it locally first (Windows PowerShell)

```powershell
cd apps\web; npm ci; npm run build
New-Item -ItemType Directory -Force e2e\.tmp | Out-Null          # git-ignored, absent on a fresh clone
$env:YONDO_WEB_DIST = "$PWD\dist"; $env:YONDO_DEMO_ADMIN_PHONE = '+998 90 000 00 01'   # any private number
python ..\..\infra\deploy\demo\demo_app.py 8100 e2e\.tmp\demo.db     # wait for SEED_DONE, then open http://localhost:8100
```
(The `.venv` with `pip install -e "apps/api[dev]"` must be active; delete `e2e\.tmp\demo.db` before each start. Add
`$env:YONDO_DEMO_PUBLIC_URL = 'https://demo.test'` to try the DEMO payment API; the browser cannot open that host, so use the checks.)

Tests: `cd apps\api; python -m pytest ..\..\infra\deploy\demo -c pyproject.toml --rootdir .`

Docker (when Docker Desktop is running): `docker build -f infra/deploy/Dockerfile -t yondo-demo .` then
`docker run --rm -p 8000:8000 -e YONDO_DEMO_ADMIN_PHONE=+998900000001 yondo-demo`.

## Option A — Render (free web service, connects to GitHub)

You (the account owner) do the sign-in; nobody else can create the account or authorise GitHub for you.
1. Sign in at render.com with your GitHub account and allow it to read the `Yondo` repository.
2. **New → Blueprint**, pick the repository and the branch `design/prototype` (the Blueprint is `render.yaml`).
3. When asked for `YONDO_DEMO_ADMIN_PHONE`, enter a private number (not `+998901110001`); `YONDO_DEMO_DATABASE_URL` can stay empty until you
   have the Neon string. Deploy.
4. Open the `*.onrender.com` URL. The first request after 15 idle minutes takes about a minute (cold start + seeding).

## Option B — any Docker host (Hugging Face Spaces, Koyeb, Fly.io, Cloud Run …)

Build from the repository root with `infra/deploy/Dockerfile`; set `PORT` to the port the host expects
(Hugging Face Spaces: `7860`) and `YONDO_DEMO_ADMIN_PHONE`. Health check path: `/health`.
