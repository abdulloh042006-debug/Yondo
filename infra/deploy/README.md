# Public demo deployment (free hosting)

One container = the real Yondo API + the built web app (`apps/web`) on **one port** (`/api/*` is the API, everything else is the web app).
Files: [`Dockerfile`](Dockerfile), [`../../render.yaml`](../../render.yaml) (Render Blueprint), [`../../.dockerignore`](../../.dockerignore).

## What this is — and is not

This is a **demo**, not production. It runs `apps/web/e2e/server.py`, which uses the e2e test doubles:

| Real production code | Test double (demo only) |
|---|---|
| authz, booking/safety/support state machines, audit trail, discovery | OTP: the code is **shown on screen** (no SMS provider exists yet) |
| web app, admin console, i18n | photos: in-memory (not stored, not served) |
| | identity check: always "verified" |
| | database: throw-away SQLite in `/tmp`, **re-seeded with DEMO data at every start** |
| | payment: `apps/web/e2e/demo_payment.py`, a stand-in for CLICK/Payme (see below) |

### DEMO payment (until real CLICK/Payme keys exist)
When `YONDO_DEMO_PUBLIC_URL` (or Render's `RENDER_EXTERNAL_URL`) is set, "To‘lovga o‘tish" creates a checkout whose link opens a
**DEMO page on this same server**: "To‘lovni tasdiqlash" sends a signed event to the real `/payments/webhook` route and the booking
becomes "Tasdiqlangan"; "Rad etish" fails the payment. **No money moves.** The platform fee is the labelled DEMO value 0 — the real fee,
cancellation and refund rules are still the owner's decision. Without the URL the API answers 503 "sozlanmagan" as before.
Real CLICK/Payme later = a new provider class behind the same `PaymentProvider` interface (`apps/api/src/yondo_api/payments/provider.py`)
plus the owner's merchant keys in the host's environment variables (never in git).
Check it against a running harness: `python apps/web/e2e/demo_payment_check.py <port>` (start `server.py` with `YONDO_DEMO_PUBLIC_URL=https://demo.test`).

### Risks you accept by publishing it
- Because the OTP is on screen, **anyone who opens the URL can sign in as any phone number**, including the admin. Mitigation built in: set `YONDO_DEMO_ADMIN_PHONE` to a private, unguessable number (it replaces the well-known `+998901110001`; nobody else knows which number is the admin). If it is **not** set, the public image fails closed: the admin gets a random unknown number, so nobody can open the admin console (set the variable when you need it). Check after every deploy that `+998901110001` gets 403 on `/api/v1/admin/summary`.
- Do not enter real phone numbers or personal data; everything is deleted at restart, but treat the site as public.
- The legal pages are still drafts (operator name "hali ko‘rsatilmagan"); see `docs/legal/pre-publication-checklist.md`.
- Not included: the hourly job (`infra/jobs/`, booking expiry + account erasure), realtime chat (the socket needs Redis; the web app polls every 8 s instead).

A real launch still needs the owner items in `docs/WORKLOG.md` → Next steps (operator name, SMS provider, payment provider and fee policy, backups, PostgreSQL, S3/MinIO storage).

## Persistent mode: keep the data between restarts (free PostgreSQL, e.g. Neon)

By default the demo forgets everything at each start. Set **`YONDO_DEMO_DATABASE_URL`** (a secret: only in the host's environment,
never in git or chat) and the same image becomes persistent (`apps/web/e2e/demo_persist.py`):
- the schema comes from the real Alembic migrations (`alembic upgrade head` at every start, a no-op when current);
- the DEMO seed runs **only while the database has no users**; later starts keep accounts, bookings, chats, reviews;
- every start and then daily, DEMO Madina and DEMO Jasur get 10:00–22:00 (Tashkent) availability for the next 14 days
  (the seed window is a single evening, so without this the demo would stop taking bookings after two days);
- a loop every 15 minutes does what `infra/jobs` does hourly in production (booking expiry, due account erasures);
- **admin = exactly `YONDO_DEMO_ADMIN_PHONE`** (nobody if unset): the well-known test number, a changed number and the random
  seed admin lose the admin role at every start, so a database first filled by a local run cannot leak an admin.

Neon setup (about 5 minutes, you sign in yourself):
1. neon.com → sign up → **Create project** (name `yondo-demo`, PostgreSQL 16 or 17). Pick the Neon region closest to your Render
   service's region (Render → `yondo-demo` → Settings → Region; the default is Oregon = Neon "AWS US West 2").
2. On the project page press **Connect**, turn **Connection pooling OFF** (use the *direct* string; the pooled `-pooler` host may
   break prepared statements) and copy the `postgresql://…?sslmode=require` string. A `psql '…'` line is also accepted.
3. Render → `yondo-demo` → **Environment** → **Add Environment Variable**: key `YONDO_DEMO_DATABASE_URL`, value = the string → **Save**
   (Render redeploys). Optionally add `YONDO_DEMO_ADMIN_PHONE` (a private number) in the same place.
4. Check: make a booking, then **Manual Deploy → Deploy latest commit**; the booking must still be there. The first start takes longer (migrations + seed).

Free limits to know: Neon suspends the compute after ~5 idle minutes (the first query after that adds about a second) and the free
project is small (0.5 GB); both are plenty for a demo. Photos are still in memory (no S3 adapter yet), the chat still polls.

## Try it locally first (Windows PowerShell)

```powershell
cd apps\web; npm ci; npm run build
$env:YONDO_WEB_DIST = "$PWD\dist"; $env:YONDO_DEMO_ADMIN_PHONE = '+998900000001'   # any private number
python e2e\server.py 8100 e2e\.tmp\demo.db     # wait for SEED_DONE, then open http://localhost:8100
```
(The `.venv` with `pip install -e "apps/api[dev]"` must be active; delete `e2e\.tmp\demo.db` before each start.)

Docker (when Docker Desktop is running): `docker build -f infra/deploy/Dockerfile -t yondo-demo .` then
`docker run --rm -p 8000:8000 -e YONDO_DEMO_ADMIN_PHONE=+998900000001 yondo-demo`.

## Option A — Render (free web service, connects to GitHub)

You (the account owner) do the sign-in; nobody else can create the account or authorise GitHub for you.
1. Sign in at render.com with your GitHub account and allow it to read the `Yondo` repository.
2. **New → Blueprint**, pick the repository and the branch `design/prototype` (the Blueprint is `render.yaml`).
3. When asked for `YONDO_DEMO_ADMIN_PHONE`, enter a private number (not `+998901110001`). Deploy.
4. Open the `*.onrender.com` URL. The first request after 15 idle minutes takes about a minute (cold start + seeding).

## Option B — any Docker host (Hugging Face Spaces, Koyeb, Fly.io, Cloud Run …)

Build from the repository root with `infra/deploy/Dockerfile`; set `PORT` to the port the host expects
(Hugging Face Spaces: `7860`) and `YONDO_DEMO_ADMIN_PHONE`. Health check path: `/health`.
