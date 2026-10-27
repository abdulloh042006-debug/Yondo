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

Payments stay unconfigured: "To‘lovga o‘tish" answers 503 / "sozlanmagan", exactly as locally.

### Risks you accept by publishing it
- Because the OTP is on screen, **anyone who opens the URL can sign in as any phone number**, including the admin. Mitigation built in: set `YONDO_DEMO_ADMIN_PHONE` to a private, unguessable number (it replaces the well-known `+998901110001`; nobody else knows which number is the admin). If it is **not** set, the public image fails closed: the admin gets a random unknown number, so nobody can open the admin console (set the variable when you need it). Check after every deploy that `+998901110001` gets 403 on `/api/v1/admin/summary`.
- Do not enter real phone numbers or personal data; everything is deleted at restart, but treat the site as public.
- The legal pages are still drafts (operator name "hali ko‘rsatilmagan"); see `docs/legal/pre-publication-checklist.md`.
- Not included: the hourly job (`infra/jobs/`, booking expiry + account erasure), realtime chat (the socket needs Redis; the web app polls every 8 s instead).

A real launch still needs the owner items in `docs/WORKLOG.md` → Next steps (operator name, SMS provider, payment provider and fee policy, backups, PostgreSQL, S3/MinIO storage).

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
