# WORKLOG — read this first, update it last
Newest entry first. Template at the bottom. Labels: PASS / FAIL / BLOCKED / NOT IMPLEMENTED / OUT OF SCOPE.

## Status snapshot
- Branch `design/prototype` (base `origin/codex/notification-integration`), **pushed** (remote SHA verified equal to local at `88b410a`; later docs-only commits may follow). Includes `dbc9113` (decisions D1–D5, audit) and `c643b03` (CLAUDE.md, WORKLOG). CI read-out for the push: no runs yet.
- Backend: PostgreSQL 16 200/200 PASS (SQLite 192 + 8 skipped); migrations 14 up/down/up PASS; 50 real-backend decision tests PASS on both DBs.
- Prototype (mock-backed, NOT a real client): node 41/41 (S13), Chromium E2E 38/38 without REALFONTS (S13; 39/39 earlier with real fonts, difference not investigated), sweep 63 (+3) over 9 configs × 25 views, gallery 5/5.

## Next steps (priority order)
0a. **Owner (S36): Telegram Gateway** — open the account at gateway.telegram.org, top up (Fragment/TON; card route unverified), put the token ONLY into the host env `YONDO_TELEGRAM_GATEWAY_TOKEN` (checklist: `docs/otp-telegram-gateway.md` §12). First real test = a code to the owner's own number (free) — **done 2026-10-28 by the S35 chat: PASS** (`docs/login-telegram-gateway.md`); still to do: a +998 number with and without Telegram; report the error text, not the token. Also check the sender name shown to the user ("Verification Codes") — the login copy `login.tg.open`/`login.tg.noCode` names that chat and it is unverified. Before go-live set `YONDO_AUTH_OTP_PROVIDER_RATE_LIMIT_PER_MINUTE` (default 0 = off), name Telegram on the privacy page (phone + code go to Telegram), settle the cross-border question with a lawyer.
0. **Owner: read `docs/decision-brief-2026-10-28.md`** (hosting, one app vs modes, screens, 10 decisions, intro/onboarding/video plan, demo wording, go-live gate) and answer its 10 questions; approve or change section 5 before any animation/onboarding/video work starts. Neon persistent DB (owner creates it) and the domain stay owner steps.
1. **Owner: revoke the GitHub token pasted in chat on S10** and set up env-based auth (`gh auth login` / credential manager / SSH / `GH_TOKEN`) so pushes need no pasted token. Then read the CI result for `design/prototype` and fix any failure.
2. **Owner/ops before publication** (`docs/legal/pre-publication-checklist.md`): operator name in Terms/Privacy; backup retention; schedule `python -m yondo_api.account.jobs` daily; then bump the document versions. Install `infra/jobs/` timer on the production host. **Next:** meeting check-in/start/end UI in web (makes SOS moderator signal reachable). **Backend decisions still open:** delivery-fee configuration schema; blocking by booking (reports by booking done in S23); profile→user id mapping (options A/B/C in `design-prototype/docs/03-decisions-and-contract.md`, unlocks customer-side report/block); CORS policy; whether to cap/stringify amounts > 2^53−1; apply `contract/openapi-v1.decisions.overlay.json` to the FastAPI models.
3. **Staging:** none documented. Obtain URL, test-login method (staging has no dev OTP; no SMS provider), payment sandbox, approved fee policy (`docs/04-staging-readiness.md`). Then add a read-only real-API contract check and an adapter that swaps the mock for the real client.
4. **Real clients:** web + admin exist in `apps/web` (S14); `apps/mobile` is a stub. Build only if ROADMAP authorizes; reuse `design-prototype/design-system` and `prototype/src/logic.js`.
5. **Quality gaps:** native Uzbek copy review (and native ru/en review of `apps/web/src/i18n`, S21); real iOS Safari/Android, Firefox/WebKit and screen-reader testing; logo symbol outlining, kerning, similarity/legal check; merch + presentation (P1/P2) not started.
6. Housekeeping: decide on `ruff format` (50 files drift, not CI-enforced); keep screenshots/reports regenerated only when UI changes.

## Session log
## S36 — Telegram Gateway login codes, Docker CI job, multi-agent roles (2026-10-28) [cloud chat]
Done (multi-agent, owner order: no passwords, start with Telegram Gateway; the **verifier agent owns commits**): merged `origin/design/prototype` (0f2de4c) into the cloud branch `ccr-15294129-n60ucy`. Researcher: `docs/otp-telegram-gateway.md` (Telegram's own pages were unreachable → nothing tagged official). Backend: `OtpDelivery.channel`, response field `delivery_channel`, errors `otp_channel_unavailable` (422) / `otp_delivery_failed` (502), settings `YONDO_TELEGRAM_GATEWAY_TOKEN/BASE_URL/TIMEOUT_SECONDS`, `select_otp_provider`, adapter `auth/telegram_gateway.py` (one request, never retried, table-driven error mapping, no token/phone/code in logs or exceptions), PostgreSQL advisory lock per phone in `issue_otp`. Demo harnesses (`infra/deploy/demo/demo_app.py`, `marketing/ad-video/server_video.py`) are pinned to the on-screen code; tests/fixtures pinned too. Web: Telegram layout in `Login.tsx` (only when `delivery_channel == 'telegram'`; dev banner unchanged), digits-only 6-char code field, new uz/ru/en keys, 10 new Login tests, e2e steps with stubbed responses. DevOps: CI job `docker-image` (build `infra/deploy/Dockerfile` + `/health` + `/` smoke).
Merge with the S35 chat (`origin/design/prototype` 128000a, same feature built in parallel): ONE adapter, our names kept. Delivery is now two-step as live-verified in S35: `checkSendAbility` first, then `sendVerificationMessage` with `{phone_number, code, ttl 300, payload, request_id from the check}`; at most 2 requests, never retried, a failed check sends nothing, our table-driven error map (`PHONE_NUMBER_*` → 422 `otp_channel_unavailable`, everything else → 502 `otp_delivery_failed`) applies to both calls. Dropped from S35 (names differ from ours): its telegram-specific 422 error code, the 503 it used for delivery failures (`otp_delivery_unavailable` stays for "not configured"), its provider-selection function, its extra API-URL setting, its 6 test cases (covered by the 96-item two-step test file). Kept from S35: `try_telegram_gateway.py` (adapted to structlog, prints only method + error string), `docs/login-telegram-gateway.md` (rewritten for the merged reality), the live findings (also in `docs/otp-telegram-gateway.md` §14). Test nits fixed: `test_auth.py` fixture pins `telegram_gateway_token=None`; the settings-defaults test no longer depends on exported `YONDO_TELEGRAM_GATEWAY_*`.
Evidence (after the merge): backend SQLite 336 passed + 9 skipped, PostgreSQL 16 345 passed + 0 skipped, demo harness 7, ruff + OpenAPI PASS, all also green with a fake `YONDO_TELEGRAM_GATEWAY_TOKEN` (and `_BASE_URL`) exported; web typecheck, lint, build PASS, vitest 53/53, e2e 60/61 — the one failure is the `yondo-tun` axe contrast flake below, which fails the same way (60/61) on the pre-merge sources in the same sandbox. Before the merge: backend SQLite 288 passed + 9 skipped, PostgreSQL 16 297 passed + 0 skipped (incl. 3 concurrent first requests → 202 + 429 + 429, exactly one send; the test fails without the lock), demo harness 7, ruff, OpenAPI check PASS (verifier re-ran all); web typecheck, lint, build PASS, vitest 53/53 (was 42), e2e 61/61 (first run 59/61: one real bug fixed, one axe contrast failure in theme `yondo-tun` on /login that did not recur — unconfirmed flake).
Not done / unverified: the S35 live test (owner's own number, 2026-10-28) verified the two-step flow, JSON bodies, `ttl` 300, our own code, a +998 number and an individual account; **still unverified**: the exact "no Telegram" / "no balance" error strings (assumed `PHONE_NUMBER_*`; if different the user sees 502 "try again"), the `payload` field (never sent live), that success arrives as HTTP 2xx (we require it), the sender name shown to the user, other operators/users and the price, card top-up. The Docker image still has never been built (no daemon in the sandbox; first run = GitHub Actions, which triggers only on `main`/`codex/**` pushes and PRs). SMS fallback, WhatsApp, passwords, delivery-report callback: NOT IMPLEMENTED. Known limits: advisory lock + DB connection held across the Telegram call (timeout 10 s); `{"ok":true}` without `result` counts as sent; `login.lead` cannot say "Telegram" before sending.
Gate waived by the owner: the third verifier (review of the merge with the S35 chat) died on the account's 5-hour usage limit before approving; the owner then said "everything is great, no need to verify, just push". The merge commit was concluded by the commander after the integrator's full runs plus a quick re-run (ruff, OpenAPI check, 127 passed + 1 skipped in the auth/otp/telegram tests) — NOT independently re-reviewed; the earlier commits (5e82587, e27e85d, ecaeb9e, 8a093bc) were verifier-approved. e2e on the merged tree: 60/61, the only failure is the known axe contrast flake in theme `yondo-tun` (also seen on a pristine pre-merge export).
Branch: pushed to `ccr-15294129-n60ucy` and, as a fast-forward at the owner's order, to `design/prototype` (this redeploys the public Render demo; the harness is pinned to the on-screen code, the Dockerfile is unchanged since S31).
Commit: the merge commit on top of e27e85d (see git log).

## S36 — DigitalOcean production package, domain-independent (2026-10-28) [local chat]
Done: owner: domain later is fine if it adds no work. It adds none (one `DOMAIN` variable + a DNS A record), so the package was built now: `apps/api/Dockerfile` (production API: `alembic upgrade head`, then uvicorn; non-root; healthcheck), `infra/deploy/digitalocean/` (`docker-compose.yml`: caddy + api + jobs loop + postgres + redis, only 80/443 exposed; `Dockerfile.web` = web build + Caddy; `Caddyfile`: DOMAIN or `:80`, automatic HTTPS with a domain; `.env.example`; `backup.sh` nightly pg_dump; Uzbek `README.md` with the Droplet steps, first-admin SQL, update/backup/restore).
Verified natively (no Docker) on PostgreSQL 16 with production settings: 17 migrations apply and the second run is a no-op; `/health` 200, `/docs` 404, discovery 200 from the real DB, OTP request without a Telegram token = **503** (no on-screen code). The first 500s were a Windows-only launcher artifact (uvicorn forces the Proactor loop, psycopg async cannot use it); fixed in the test launcher only, Linux containers unaffected.
Not verified: Docker builds, Caddy config, Compose healthchecks/depends_on, HTTPS issuance (needs the domain), restore of a backup. Not built: S3/MinIO photo adapter (photo upload fails in production), identity verification, admin bootstrap command (SQL in the README), TezCheck needs the domain, Telegram needs a funded balance for numbers other than the owner's.
Commit: this entry's commit.

## S35 — Owner answers: DigitalOcean for now, TezCheck for individuals, own phone for now (2026-10-28)
Done: recorded in CLAUDE.md §7, the decision brief (#11 resolved for payments, blocker reworded) and `docs/payments-tezcheck.md`. Checked: DigitalOcean is **not free** — GitHub Student Pack credit (official page says $100/year, forum posts say $200; unverified for 2026), a marketing line says $200 for the first 60 days; card or PayPal required, Uzbek card acceptance unverified. Eskiz: community packages use sender "4546"; 85 UZS/SMS from a Bitrix24 listing; whether OTP must use a service route rather than advertising and whether individuals can sign a contract: not confirmed (ask Eskiz, notify.eskiz.uz). No code changed.
Later the same day: DigitalOcean confirmed (his Visa card works). Owner wants the code delivered by Telegram/WhatsApp instead of on screen, and asked about adding passwords; research: Telegram Gateway $0.01/code (Telegram's page; Uzbekistan availability and individual sign-up unconfirmed), `OtpDeliveryProvider` is the plug-in point, not built yet; passwords not recommended now.
Telegram login built the same day: `TelegramGatewayOtpProvider` (`auth/telegram_gateway.py`: checkSendAbility → sendVerificationMessage with our code; in the S36 merge the errors became 422 `otp_channel_unavailable` for numbers without Telegram and 502 `otp_delivery_failed` otherwise), `YONDO_TELEGRAM_GATEWAY_TOKEN`, provider selection in `main.py` (now `select_otp_provider`), demo harness pinned to the on-screen code, 3 i18n strings, `login.lead` no longer says SMS; `docs/login-telegram-gateway.md`. Mocked-transport tests only (9 new + auth 9 passed); the real gateway was never called (owner creates the account; funding via Fragment).
Live test PASS (2026-10-28, owner's own number via `apps/api/try_telegram_gateway.py`): two-step flow, JSON bodies, `ttl` 300 and our own code accepted, +998 number works, account opened by an individual; code delivered to Telegram and matched. Not tested: other users' numbers (balance must be funded via Fragment), error strings.
Next: owner answers the remaining closed questions (see the reply prompt in `reports/`); then CI Docker build check, DigitalOcean deploy how-to only after the owner confirms payment method and domain.
Commit: this entry's commit.

## S34 — Cloud branch merged, brief completed (2026-10-28)
Done: owner said "Birlashtir": `origin/ccr-15294129-n60ucy` (S33 decision brief + `main`'s two docs) fast-forwarded into `design/prototype` (no conflicts). Cross-checked the brief against the 7 local research notes (`research_notes/`, git-excluded) and added what it lacked, each tagged **[Y]**: legal entity / bank account as a go-live blocker and new owner decision #11 (Payme Business needs a registered entity; same entity = data operator; TezCheck onboarding for individuals unknown), the open legal question whether phone numbers count as telecom-user data + the 29 Jul 2026 adequacy list, SMS sender-ID lead time (Ucell blocks unregistered names since 3 Aug 2026; Eskiz ~85 UZS/SMS), closed-beta length 6–8 weeks, and a Tashkent-VPS vs EU-VPS comparison (the two research notes disagree: law note favours Tashkent, hosting note favours EU; recommendation for beta = Tashkent, owner decides).
Not done: all prices/lists are from search summaries, official texts (ZRU-1125, the 29 Jul resolution) unread; a lawyer must confirm. No code changed, so no test run.
Commit: this entry's commit.

## S33 — Decision brief for the owner (2026-10-28)
Done: merged `origin/design/prototype` (84c799c) into the cloud working branch `ccr-15294129-n60ucy` (it only had `main`'s two doc commits; clean merge). Wrote `docs/decision-brief-2026-10-28.md` (Uzbek, one table per topic): hosting (Render+Neon stays for demo; Toshkent VPS recommended for closed beta; Oracle Always Free only as staging; university PCs not recommended), data localization (2019 law + 26 Mar 2026 amendment, lawyer must confirm), one app with two modes + separate admin, screens must-have/optional, 10 owner decisions, intro/onboarding/video plan, demo-wording rule, go-live gate.
Found: **ROADMAP Phase 20 lists "bir nechta vendor", but `apps/web` has no gifts/vendor screens** (API only) — reported as owner decision #10, ROADMAP not edited (AGENTS.md).
Not done: the 7 local notes in `research_notes/` were NOT available in this cloud session (git-excluded), so claims are tied to repo files and today's web search instead of the notes; Oracle/Kun.uz pages could not be fetched here (host not allowed), facts come from search summaries; fee/cancel/refund/payout not invented. Step D (animation/onboarding/video) waits for the owner's approval. No code changed, so no test suite was run.
Branch: pushed to `ccr-15294129-n60ucy` only, NOT to `design/prototype` (a push there auto-deploys the public Render demo; no instruction to deploy was given).
Commit: this entry's commit.

## S32 — TezCheck payment adapter (2026-10-28)
Done: owner: "adapt payment to TezCheck (tezcheck.uz); Click/Payme merchant contracts are not needed for it; a domain must be bought first". Read the public API docs (`docs/payments-tezcheck.md`) and wrote `TezCheckPaymentProvider` (`apps/api/src/yondo_api/payments/tezcheck.py`) behind the existing `PaymentProvider` interface: `POST /bills` with `Idempotency-Key`, provider reference = bill id, webhook HMAC-SHA256 check (`{timestamp}.{delivery}.{raw body}`, ±300 s, rotation-safe), `payment.succeeded`/`payment.failed` only, test-environment events refused unless `YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS` (never in production). Settings + startup validation (token without webhook secret refuses to start), wiring in `create_application`, `httpx` is now a main dependency of `apps/api`, demo image uses the real adapter when the token is set, `render.yaml` declares the three secret names. Fee/cancellation/refund policy untouched (owner decisions).
Not done: **never run against the real TezCheck** (needs the domain, cash desk, API key, webhook secret from the owner); refund endpoint not documented by TezCheck; webhook amount is not compared with the stored payment; unpaid bill is not cancelled when a booking is cancelled; open questions for TezCheck support are in the doc.
Evidence: 9 new tests (`tests/companions/test_tezcheck.py`: request shape, signature accept/reject/stale/rotation, test-environment gate, settings validation, wiring, full checkout → signed webhook → booking confirmed with the real adapter on a mocked transport); full backend suite 221 passed + 8 PG-only skipped (was 212), demo harness 6 passed, ruff and OpenAPI contract PASS.
Also: the 7 research notes (hosting, Uzbek law/providers, one app vs two, customer pages, companion/admin pages, intro/onboarding/video, demo→launch) are complete in `research_notes/` (git-excluded); the synthesis brief for the owner is NOT written yet. Master prompt for a new chat: `reports/Master prompt for the next chat.md`.
Commit: this entry's commit.

## S31 — Review fixes for S28–S30 (13 findings, all fixed) (2026-10-28)
Done: `/code-review xhigh` on the S28–S30 work reported 13 findings; every one is fixed. Paths below are the new ones (**the S28–S30 entries still say `apps/web/e2e/…`: the harness moved to `infra/deploy/demo/`**, `apps/web/e2e/server.py` is now a thin entry point to the same code).
- Altitude: `demo_app.py` / `demo_payment.py` / `demo_persist.py` live in `infra/deploy/demo/`; the Dockerfile runs `demo_app.py`; e2e and the public demo share it.
- Admin phone: `YONDO_DEMO_ADMIN_PHONE` is normalized with the API's own rule (`+998 90 …`, `909990001` … all work) and a bad value stops the start with a clear message; before, a spaced spelling locked the admin out.
- Half-seeded database: seed is bracketed by a marker (table `demo_seed_state`); a start that died while seeding is wiped (`DROP SCHEMA public`) and seeded again, a complete or marker-less database is never wiped.
- DEMO payment is now the web app's own page `/demo-pay/:reference` (`DemoPay.tsx`, i18n uz/ru/en); the server endpoints accept only the paying customer (companion/anonymous refused) — replaces the unauthenticated Python page.
- Availability top-up runs in the background after the port is open and posts only the new day daily; unknown DEMO phones are skipped (no stray accounts); phones are shared constants.
- `render.yaml` declares `YONDO_DEMO_DATABASE_URL` (sync: false); README: persistent mode keeps personal data (old "deleted at restart" claim fixed), local-run snippet creates `e2e\.tmp`.
- Tests: `infra/deploy/demo/test_demo.py` (6, added to the CI `api` job) + `demo_payment_check.py` (re-runnable, shared with pytest, also usable against a live server). The edit of `docs/legal/pre-publication-checklist.md` was reverted (AGENTS.md: no policy-document edits unasked); the fonts note stays here in WORKLOG.
Ultrareview: `/ultrareview` refused (diff vs `main` = 356 files / 54,783 lines; limits 500 / 8,000). Local branch `ultrareview-base` (= `57d81bc`, not pushed) gives a small diff: `/code-review ultra ultrareview-base`.
Evidence: pytest demo 6 passed; vitest 42/42; tsc, eslint, build PASS; e2e 59/59. Real PostgreSQL 16.15 (same unsigned EDB zip, local only, deleted again): first start with a pasted `psql '…'` line and `+998 90 999 00 02` → admin only that number; DEMO payment CLI 14/14; restart keeps data and skips the seed (port open in 2 s); `running` marker → wipe + reseed (7 users, 2 bookings, marker complete); container layout (`/app/api`, clean venv) → 17 migrations, pages 200.
Not done: real Neon database (owner), Docker image build (Docker Desktop off), Neon TLS/auto-suspend.
Commit: this entry's commit.

## S30 — Persistent demo mode (free PostgreSQL such as Neon) (2026-10-28)
Done: owner: "free DB/servers are fine to start; I create the Neon account and put the connection string into Render myself". `apps/web/e2e/demo_persist.py` + `server.py`: with `YONDO_DEMO_DATABASE_URL` the demo uses that database (accepts `postgresql://`, `postgres://` or a pasted `psql '…'` line), runs the real Alembic migrations at every start, seeds only while there are no users, tops up DEMO companions' availability for 14 days (at start and daily), and runs the hourly job logic every 15 min (no cron on a free web service). Admin in this mode = exactly `YONDO_DEMO_ADMIN_PHONE`, nobody if unset: found while testing that a database first seeded by a local (loopback) run kept the well-known admin number, so every start now strips the admin role from everyone else. The connection string is read from the environment only and never printed. Windows: server.py uses the selector event loop (psycopg async cannot use Proactor). README: Neon step-by-step.
Not done: the real Neon database (the owner creates it); S3/MinIO adapter for photos; Redis (chat realtime). Neon-specific behaviour (TLS, auto-suspend) could not be tested locally.
Evidence: SQLite file in persistent mode: restart keeps data and skips the seed; admin phone added/removed/changed as specified. Real PostgreSQL 16.15 (EDB Windows zip, unsigned, official domain, run only on 127.0.0.1, then deleted; `D:\tools\pgtest\pgsql` kept for local PG tests): 17/17 migrations incl. btree_gist, seed, restart keeps the booking, admin lockdown, DEMO payment check 10/10 (real row locks). Full e2e on the default harness (SQLite, payment off): 59/59 PASS.
Commit: this entry's commit.

## S29 — DEMO payment provider: the demo can complete a booking (2026-10-28)
Done: owner: "use test tokens for now, real CLICK/other keys later; free servers/DB are fine to start, plan by user count later". `apps/web/e2e/demo_payment.py`: `DemoPaymentProvider` (HMAC-signed events into the REAL `/payments/webhook`), DEMO pay page `/demo-pay/{ref}` (confirm / reject), labelled DEMO fee 0; on only when an https `YONDO_DEMO_PUBLIC_URL` / Render's `RENDER_EXTERNAL_URL` exists, otherwise the honest 503 stays. API code untouched (provider injected by the harness). Dockerfile copies the module; README explains how real CLICK/Payme plugs in (new `PaymentProvider` class + the owner's keys in host env vars).
Not done: real CLICK/Payme adapter (needs the owner's merchant keys), fee/cancellation/refund policy (owner), S3/MinIO adapter (only the `ObjectStorage` protocol exists → photo upload says unavailable), persistent PostgreSQL mode for the demo (needs a free DB, e.g. Neon, created by the owner).
Evidence: `e2e/demo_payment_check.py` 10/10 PASS on a local harness (checkout → page → confirm → booking confirmed; confirm twice idempotent; forged webhook 401; reject keeps booking accepted); full e2e 59/59 PASS with the default (payment-off) config. Live (https://yondo-demo.onrender.com) after the redeploy: same 10/10 PASS, and the DEMO page button pressed in a real browser → booking `confirmed`.
Commit: this entry's commit.

## S28 — Handoff verification on Windows, 5 fixes, self-hosted fonts, free-hosting demo image (2026-10-27)
Done: local `design/prototype` was 29 commits behind; fast-forwarded to `c7f9b87`. Ran the whole check list and a manual tour (built-in browser, localhost only). Findings → fixes:
- FAIL→fixed: `/terms` and `/privacy` rendered as one `<h1>` on Windows (`core.autocrlf` makes the `.md` files CRLF; `Markdown` split on `\n\n`). `LegalPage.tsx` normalises line endings; test added.
- FAIL→fixed: booking error `availability_not_found` (409) had no i18n key and showed "data changed". Added `err.availability_not_found` (uz/ru/en). 39 other backend codes still lack a key (gifts/beta/vendor not in web, 404/422 fall back sensibly).
- FAIL→fixed: login field is prefilled `+998`; a pasted/typed full number became `+998+998…` and was rejected. `dedupePhonePrefix` in `lib/format.ts` (+ test).
- FAIL→fixed: `e2e/run.mjs` spawned `npx` (breaks on Windows/Node 24); now runs vite through `node`.
- Google Fonts → self-hosted `@fontsource-variable/*` (5 families, OFL). No request leaves the app (checked in the browser). **OPEN (owner):** `privacy.md` §10 "Shriftlar" bullet is now untrue; edit it with the next legal version.
- `infra/deploy/` + `render.yaml`: one image = API + web on one port for a free host (uses the e2e test doubles; `e2e/server.py` got 3 env hooks: host, private admin phone, web dist). Tested natively on :8100; Docker image NOT built (Docker Desktop not running). Render Blueprint created by the owner (2026-10-27): first deploy **FAILED** — `httpx` and `aiosqlite` are dev-only extras of `apps/api`, so the image lacked what `server.py` imports. Fixed in the Dockerfile and checked in a clean venv on D: (main deps only: both missing; with the two added: seed + `/health` + SPA + API 200). Redeploy went live (`/health` 200, SPA + API + login OK). **Found live: `+998901110001` was admin** (the private admin phone was not applied in Render), so with the on-screen OTP anyone could open the admin console. Fixed fail-closed in `e2e/server.py`: on a non-loopback bind an unset/empty `YONDO_DEMO_ADMIN_PHONE` yields a random unknown admin number (checked locally: well-known phone → 403, seed still works). Owner must set the variable in Render → Environment to use `/admin`. Live demo: https://yondo-demo.onrender.com (Render free, Blueprint "Yondo", branch `design/prototype`, redeploys on every push; data resets). Live check after the fix PASS: SPA routes, missing API/asset = 404, API, customer login, customer → admin 403, well-known admin phone 403.
Not done: realtime chat (socket needs Redis; no Redis in the demo) = NOT IMPLEMENTED; owner items (operator name, SMS/identity provider, payment/fee, backups); native-speaker review; real-device tests; old spelling in `design-prototype/` + `marketing/`; `ruff format`; `apps/mobile`.
Evidence: API SQLite 212 passed + 8 skipped (PG-only), ruff, OpenAPI check PASS; web tsc, eslint, build, vitest 39/39 PASS; real-backend e2e 59/59 PASS (Edge via `CHROME`); one run under heavy load had 2 `goto /help` timeouts, not reproducible. Manual PASS: search "Toşkent"/"Toshkent", booking, companion accept, payment 503 text, SOS dialog (no request sent), settings alphabet+theme.
Env note: C: was full (npm global install of `omniroute` died with ENOSPC; partial dir removed). A 2 GB `.omniroute-*` leftover from 2026-10-26 in `%APPDATA%\npm\node_modules` is not ours and was left alone. Owner asked for OmniRoute (AI gateway, unrelated to the product code): installed `omniroute@3.8.52` under `D:\tools\npm-global` (not on PATH, server never started; npm 11 skipped its 7 install scripts; default dashboard password is CHANGEME: set one before first run). e2e "legal pages" step now asserts section headings, so the CRLF bug cannot return unnoticed.
Commit: this entry's commit.

## S27 — Promo video: profile pictures + live waving portrait; RU via the app's own locale (2026-10-27)
Done: owner: "add pictures where there are none (it's an ad)" + "bring the frame to life (a gesture)". Illustrated portraits (brand palette, not photos of real people) for Madina/Jasur/Sevara + 2 gallery scenes, uploaded by the seed through the real photo endpoint; test storage served by `server_video.py`. In the video the in-app profile photo comes alive (arm rises, waves hello, head sways) in both formats. Air-kiss not done (product rule: no romantic imagery). Fast-forwarded to S22–S26 first (6 remote commits); capture adapted (consent checkbox; RU through the app's top-bar locale switch, `ru-dict.json` only for seed data; deterministic profile scroll + photo box).
Evidence (PASS): 4 × 20 shots, 0 errors; RU leftovers only Yondo/UZ/RU/EN/SOS/Magic City/IDs; stills + rendered frames checked (overlay aligned on phone and browser); 4 files: uz 44.93 s I=-14.7 LUFS, ru 40.50 s I=-14.3 LUFS, 1080×1920 + 1920×1080; delivered in chat (not committed).
Commit: this entry's commit.

## S26 — Web: booking detail (payment, meeting, chat, review) + notifications (2026-10-23)
Done: owner: "server at the end, do the rest". `apps/web` now covers the whole booking lifecycle on top of the existing API (no backend change):
- `/bookings/:id`: payment only when `accepted` (stable `Idempotency-Key` per booking; 503 shown as unavailable, never "declined"/paid), meeting check-in → start → finish (server rules), chat with polling + labelled system events + read cursor, review after `completed` (1–5 stars + comment), report + SOS. Bookings list links "Batafsil".
- `/notifications` (kind labels, open booking, mark all read) + unread badge in the Profile menu.
- e2e seed: one DEMO confirmed booking written directly to the DB (no payment provider exists) so the meeting/SOS/review path is testable.
Not done: realtime chat socket (polling used); payment provider, production host (owner: server/deploy last).
Evidence (PASS): tsc, eslint, build, vitest 37/37; real-backend e2e 59/59 (new: accept → 503 payment shown honestly → notification; chat both ways, both check in, start, SOS moderator signal recorded, both finish, review 5/5, chat read-only).
Commit: this entry's commit.

## S25 — SOS in web, booking slot expiry, block via booking, job scheduling (2026-10-23)
Done: owner approved "all" of the next stage.
- SOS (`apps/web/src/ui/Sos.tsx`): header button (signed in), Help, confirmed/active bookings. Dialog = confirmation; `tel:112`; trusted contacts via `sms:`/`tel:` of the user's phone; geolocation only after a tap and only into the SMS text; moderator signal (existing API) only for an active meeting; honest wording everywhere.
- Booking slots (owner text): overlap already guarded (app check + PG GiST exclusion) — PASS. New status `expired` (migration 0017): pending/accepted bookings past their start can no longer be accepted (`booking_expired`) or paid; sweep `bookings/expiry.py`; slot released.
- Block via booking: `PUT/DELETE /safety/bookings/{id}/block`, `GET /safety/blocked-bookings`; Bookings page Block/Unblock with confirmation.
- `python -m yondo_api.jobs` = booking expiry + account erasure (old `account.jobs` kept as alias); `infra/jobs/` systemd timer + cron + README (hourly).
- Fixed: every Dialog now portals to `body` (header `backdrop-filter` clipped the SOS dialog off-screen).
Not done: meeting check-in/start/end UI in web (so "active" meetings only arise via API); a production host to install the timer (OPEN, ops).
Evidence (PASS): API SQLite 212 passed + 8 skipped; PostgreSQL 16: 220/220, decision tests 50/50; migration 0017 up/down/up on SQLite + PG; ruff; OpenAPI export. Web: tsc, eslint, build, vitest 36/36; real-backend e2e 57/57 (new: SOS dialog with mocked geolocation + contact SMS link, block/unblock via booking).
Commit: this entry's commit.

## S24 — Account deletion (30 days), in-app support, Terms/Privacy pages + consent (2026-10-23)
Done: owner decisions of 2026-10-23 (attachment: privacy + terms drafts, decision table).
- API (migration 0016): `account_deletion_requests` (request/cancel, one pending per user, due after 29 days), erasure job `account/deletion.py` (de-identify user + clear personal data, keep bookings/payments/reviews/chats/safety/audit/consents; photo objects deleted when storage is configured), `python -m yondo_api.account.jobs` + `POST /admin/account-deletions/process-due` (audited); new status `deleted` (auth blocked, admin cannot set/revert). Pending accounts hidden from discovery and cannot book.
- API: `user_consents` + `/legal/versions`, `/account/consents` (non-current version refused); `support_requests` + `/support/requests`, `/admin/support/requests[/{id}/reply]` (audited).
- Web: `/terms`, `/privacy` (owner drafts adapted to the real data inventory: Google Fonts is the only external service; no e-mail), unticked consent box on login, consent gate, Help → support form + my requests, Profile → delete account (confirm box, pending/cancel), Settings links, admin pages Requests + Deletion requests.
- Not done (owner: next stage): SOS in web, block by booking. OPEN: operator name, backup retention, scheduling the daily job — `docs/legal/pre-publication-checklist.md`.
Evidence (PASS): API SQLite 210 passed + 8 skipped; PostgreSQL 16: 218/218, decision tests 50/50; migration 0016 up/down/up on SQLite + PG; ruff; OpenAPI export. Web: tsc, eslint, build, vitest 34/34; real-backend e2e 55/55 (new: legal pages, consent gate, support round trip, deletion refused/requested/cancelled). Only a CSS spacing tweak of `.legal-doc` came after the e2e run (checked by screenshot).
Commit: this entry's commit.

## S23 — Two Uzbek alphabets (web + API), Help & safety, Profile/Settings rework (2026-10-23)
Done: owner: "ikki variant bo'lsin, backendni ham mosla; shikoyat/yordam bo'limi; profil va sozlamalarni o'xshash ilovalardek tuzat".
- i18n: 1995 spelling derived from the 2026 `uz.ts` (`toUz1995`, round-trip = old dictionary, 0 diffs); default by date (1995 until 2027-04-22); Settings alphabet picker; Uzbek dates formatted by hand ("23-oktyabr 2026, 05:51"; Chromium printed "2026 M10 23").
- API: migration 0015 `users.ui_locale` (`uz-Latn-1995|uz-Latn-2026|ru|en`, partial `PUT /auth/profile`, in `/auth/me`); client syncs it across devices. Discovery `q`/`city` fold both alphabets + apostrophe shapes (`discovery/textfold.py`).
- Reports: `POST /safety/reports` with `booking_id` only derives the counterparty (option C, reports only; `report_target_required`). Web: "Report a problem" on each booking.
- `/help` (112, how to report, my reports, trusted contacts, FAQ, support status, beta feedback if enrolled); Profile hub menu; Settings groups (language+alphabet, look, account, privacy & safety, about+version); footer links.
- Fixed: `PageTransition` left `filter: blur(0px)` → fixed booking bar was positioned relative to the page (now portal + `transitionEnd`).
Not done / NOT IMPLEMENTED (stated in the FAQ): account deletion (needs owner retention rules), support channel, SOS + meeting flow in web, block by booking, terms/privacy docs. Competitor research run BLOCKED (research usage limit); IA based on common app patterns.
Evidence (PASS): API SQLite 206 passed + 8 skipped; PostgreSQL 16: 214/214, decision tests 50/50; migration up/down/up on SQLite + PG; ruff clean; `export_openapi.py --check`. Web: tsc, eslint, build; vitest 31/31; real-backend e2e 51/51 (new: help/report/contacts, locale follows account to a 2nd device, alphabet default + switch + cross-alphabet search; axe on /help, /account).
Commit: this entry's commit.

## S22 — Top-bar language switch, no-remount fix, Uzbek in the 2026 alphabet (2026-10-23)
Done: (1) owner: "o'zbek tili yangilandi, qaytadan yozib chiq" — law of 2026-10-21 (in force 2027-04-22): sh→ş, ch→ç, o‘→ö, g‘→ğ, ng = n+g, tutuq ʼ. Converted all 304 `uz.ts` values with a placeholder/plural-safe script, plus UI label `Özbekça`, `index.html`, test/e2e expectations. (2) Added `i18n/LanguageSwitch.tsx` (UZ|RU|EN, 44px targets) in the top bar; Settings picker stays. (3) Removed `LanguageBoundary` remount (it wiped typed form text): `App` calls `useLang()`, `ApiError.message` is lazy.
Not done / OUT OF SCOPE: `design-prototype/`, `marketing/ad-video` and docs still use the old spelling; Intl month names come from CLDR (no sh/ch in uz months, so no visible effect); backend/user content is not converted.
Next: native review of the converted Uzbek (loanwords like `Şopping`, `çat`, proper nouns) and of ru/en; update the prototype/video copy if the owner wants it.
Evidence (PASS): tsc, eslint, `npm run build`; vitest 27/27 (new: typed input survives a switch); real-backend e2e 48/48 (new: phone typed on /login survives header RU/UZ switch).
Commit: this entry's commit.

## S21 — apps/web multilingual: uz (default) / ru / en (2026-10-23)
Done: owner asked "loyihani ko'p tillik qil". Added `apps/web/src/i18n/` (no new dependency): `uz.ts` = source of truth, `ru.ts`/`en.ts` typed `Record<Key,string>` (tsc fails on a missing key), `t(key, params)` with `{name}` and ICU-lite `{n, plural, one {…} few {…} other {…}}` (Intl.PluralRules), `LanguageBoundary` (remounts the tree below Router/Auth/Toasts on change), `LanguagePicker` in `/settings` (next to the theme picker; not in the top bar), `<html lang>`/title/meta follow the language. ru/en are lazy chunks; uz stays in the main bundle. Every page, the admin console, error messages (by `code`), status/role/service labels, money (`so‘m`/`сум`/`UZS`, `,` decimal in ru) and dates (per-locale Intl, still Asia/Tashkent) are migrated (~600 keys). Default stays **Uzbek, no browser auto-detect** (product language; e2e relies on it). Choice stored in `localStorage['yondo.lang']`.
Not done / OUT OF SCOPE: `design-prototype/` (mock prototype, own build) and `marketing/ad-video` untouched; backend messages are not localized (client maps `code`); user-written text (bios, interests, review notes) is shown as written; native `datetime-local` pickers follow the browser locale. RU/EN copy was written by me, **not native-reviewed**; "Companion" = "компаньон" (matches the promo script).
Next: native review of ru/en strings (`i18n/ru.ts`, `en.ts`); decide whether to add a compact language switch to the top bar or Login (owner rule so far: switchers live in Settings only).
Evidence (PASS): `npm run typecheck`, `npm run lint`; `npm test` 26/26 (18 old + 8 new: key parity ru/en vs uz, placeholder parity, plural forms, switching, formats); `npm run build` (no >500 kB warning); `npm run e2e` against the real FastAPI app on SQLite 48/48 (45 old unchanged in uz + new: uz→ru→en→uz persists on reload, `<html lang>`, Russian API-backed error + verified badge, axe A/AA in ru and en). Chromium sweep of design-prototype not run (not touched).
Note: supersedes S20's "apps/web has no RU locale" — the RU promo cut can now use the real Russian UI (`localStorage['yondo.lang']='ru'`) instead of capture-time `ru-dict.json`; marketing pipeline left untouched here.
Commit: this entry's commit.

## S20 — Promo video: no subtitles, Russian app screens in the RU cut (2026-10-23)
Done: owner: (1) remove subtitles, (2) RU version must show the app fully in Russian. Subtitles disabled in `page.tpl.html`; per-language screen sets; `capture.mjs` APP_LANG=ru swaps visible text via `ru-dict.json` (+ "<price> dan" → "от <price>", dates dd.mm.yyyy, `--lang=ru-RU`), restores after each shot; long headlines auto-fit to 2 lines.
Evidence (PASS): RU day + night captures 20 + 20 shots; `untranslated.json` leftovers only Yondo / Magic City / IDs; stills v/h checked (no subtitles, Russian UI).
Not done: `apps/web` has no RU locale (NOT IMPLEMENTED in the app; the video uses capture-time translation).
Commit: this entry's commit.

## S19 — Promo video: owner voices + apps/web screens (2026-10-22)
Done: owner supplied `yondo-ovozlar.zip` (uz-01..07, ru-01..07; 24 kHz mono 16-bit; the separate ru zip is byte-identical) → timeline from real durations (uz 44.9 s, ru 40.5 s). Owner: "replace only the in-app screens, keep everything else" → screens now from `apps/web` (real FastAPI on SQLite + labelled doubles) via `capture.mjs`, themes `yondo` / `yondo-tun`. Fixes: booking time is a round daytime slot (server_video seeds day+2 09:00–16:00 Tashkent; capture books 12:00 / 14:00); price chip back to 150 000 (apps/web Kofe price).
Evidence (PASS): 20 + 20 screens captured; contact sheets checked (no DEMO, verified badges hidden); stills v/h checked (taps land on "Bron qilish"); 4 renders produced in this session (see final message for durations/LUFS).
Not done: app formats dates as "2026 M10 24" in headless Chromium (Intl uz fallback; app behaviour, not changed); voices/videos not committed (size/owner audio).
Commit: this entry's commit.

## S18 — Promo video: line-art illustrations per line (2026-10-22)
Done: owner asked to illustrate each spoken line with pictures. `marketing/ad-video/page.tpl.html` gained a `#scene` layer (skyline → map+route → lonely figure + dashed "?" silhouette; faint skyline in line 2; public square in line 6; evening skyline at the end) and chip icons. Owner asked why there is no voice: voicelab.uz files were never supplied to this session (site blocked from sandbox).
Evidence (PASS): stills checked in 9:16 and 16:9 (overlaps with text fixed); 4 files rendered: uz/ru × 9:16 (1080×1920) / 16:9 (1920×1080), 41.33 s / 40.16 s, all ebur128 I = -14.4 LUFS; delivered to owner in chat (not committed: size).
Not done / BLOCKED: voice-over (needs 14 wav from owner).
Next: owner voices → `$AD/voice/`, re-run build_timeline → build_page → render ×4 → audio → mux.
Commit: this entry's commit.

## S17 — Promo video pipeline imported, draft rendered without voices (2026-10-22)
Done: owner uploaded `yondo-ad-video-skriptlar.zip` (scripts from a cloud session whose push was blocked; `apps/web` and voices are NOT in this repo). Added `marketing/ad-video/` with: `capture_proto.mjs` (screens from design-prototype, DEMO/verified hidden, avatars/status recoloured to ink/paper/carrot), draft mode in `build_timeline.py`/`audio.py` (missing voice → text-estimated timing, music+SFX only), `AD` env var in all scripts, outlined `wordmark.svgfrag`, price chip 150 000 → 110 000 (matches captured screen). README section "Alternative".
Evidence (PASS): 16 light + 2 dark screens captured; contact sheets checked visually (no DEMO text, palette OK); stills v/h checked; `yondo-reklama-uz-9x16.mp4` 1080×1920 H.264+AAC 41.3 s, ebur128 I=-14.4 LUFS, peak -0.8 dB; other 3 formats rendered in the same session (see final message).
Not done / BLOCKED: owner voices (14 wav) not supplied → draft has no voice-over; admin screens replaced by booking-detail pending/accepted; tap marker positions tuned for apps/web, not re-tuned; videos not committed (size).
Next: owner sends `uz-01..07.wav`, `ru-01..07.wav` → put in `$AD/voice/`, re-run steps 2–6.
Commit: this entry's commit.

## S16 — Motion pass across screens/components (2026-10-22)
Done: owner asked for motion on every button/page (login, home, etc.), my choice. CSS-first, transform/opacity only, existing 150–400 ms tokens; added `--ease-spring` (tokens.css/json). Map in `design-system/components.md` (Motion map). JS edits are class/attr only (app.js welcome/login/roles `.up`; roles.js lists `.list.st`); no logic change.
Evidence (PASS): `node tests/run.js` 41/41; `SWEEP='[]' node tests/browser.js` 38/38 (F12 reduced-motion + 200/300/300 ms specs PASS); `AXE=1 SWEEP='[360,1440]' ONLY_SWEEP=1` 28/28. First sweep FAILED contrast on welcome (text measured mid-stagger at 500 ms) → stagger shortened to ≤460 ms, re-run PASS. Ad-hoc Chromium check: login shake, OTP enter, nav bar indicator, timeline ring, check pop then text (opacity 0→1) all applied; no page errors.
Not done: REALFONTS not used; no real-device/Safari check of motion; hover effects only verified by CSS, not interaction tests.
Next: unchanged priorities below.
Commit: this entry's commit.

## S15 — Yondo day/night themes, promo video, settings (2026-10-22)
Done: theme switch moved to `/settings`; official logo mark/favicon; slogan "Yondo doim yoningda"; themes `yondo` (day) and `yondo-tun` (night) restricted to the logo colours (ink, paper/white, carrot #E8501A); promo video pipeline in `marketing/ad-video/` (real app captures, synthesized music/SFX, owner's voicelab voices, uz/ru × 9:16/16:9); single-file screen gallery. CLAUDE.md §7 now logs owner decisions.
Not done: push (BLOCKED by the session permission classifier); real-device/screen-reader checks.
Next: owner revokes chat-pasted tokens; owner decides whether `yondo` becomes the default theme.
Evidence: web e2e 45/45 (axe A/AA in 5 themes), tsc/eslint/build clean, unit 18/18.
Commit: see `git log -1 -- docs/WORKLOG.md`.

## S14 — Real web app + secured admin console (apps/web) (2026-10-22)
Done: `apps/web` (React 19/TS/Vite, Uzbek-first, glass + motion, themes Gul/Jurnal/Stone) on the REAL FastAPI backend (no Supabase): discovery, profile, OTP login, bookings, favorites, account, companion studio, admin (dashboard, applications/content moderation, safety signals, users, bookings read-only, audit log). Backend: `GET /companions/admin/applications`, `GET /admin/audit-events`, audit rows in the same transaction for application/content decisions and safety acknowledgements, masked-phone users list, typed summary/bookings. OpenAPI regenerated; CI `web` job added. Details: `docs/web-and-admin.md`.
Not done: payments/chat/SOS creation/reviews/gift UI (NOT IMPLEMENTED, endpoints exist); studio activate/availability/withdraw not browser-tested; real-device, screen-reader, Firefox/WebKit not tested; photo bytes in e2e come from an in-memory storage double.
Next: owner bootstraps first admin by DB insert (see docs/web-and-admin.md); wire a real identity provider + SMS; owner revokes the exposed chat token.
Blockers: BLOCKED (push): no token in session; never use the old tokens.
Evidence: web unit 18/18, tsc/eslint/vite build clean; Chromium e2e 41/41 (real FastAPI on SQLite, 3 labelled doubles; axe A/AA in 3 themes); backend SQLite 204 passed + 8 skipped; PostgreSQL 16 full pytest 212 passed; ruff clean; openapi --check PASS.
Commit: see `git log -1 -- docs/WORKLOG.md`.

## S13 — S12 verified by execution (2026-10-20)
Done: before any change, HEAD == origin/design/prototype == d8ad0a6; 87015d8, 2bf4e73, d8ad0a6 present (logic.js 503 copy, run.js test, WORKLOG). Ran the S12 "Next" tests. No failures, so no source change.
Evidence (PASS):
- `NODE_PATH=<tools>/node_modules node design-prototype/tests/run.js` -> 41 passed, 0 failed, 41 total (incl. new unknown-HTTP-503 test).
- `cd design-prototype; NODE_PATH=<tools>/node_modules SWEEP='[]' node tests/browser.js` -> 38 passed, 0 failed, 38 total (F10 offline+retry, F10 loading skeleton, F9 vendor earnings 503 unavailable state, F11 keyboard, F12 reduced motion, no console errors).
Not done: browser sweep (ONLY_SWEEP) NOT run (copy-only change, no CSS/layout). REALFONTS not used; 38 vs documented 39 not investigated (UNVERIFIED). Generic-503 copy is covered by the node test only, not by a browser flow. CI result not read.
Design source: owner uploaded `grok-workspace.zip` (TanStack Router/TSX app; Gul/Jurnal/Stone palettes live in its `src/styles.css`). It is NOT in this repo. Polish plan awaits owner approval; no palette invented, no code written.
Next: owner approves design plan (and says where it should land); read CI for design/prototype; owner revokes the chat token.
Commit: this entry's commit (see `git log -1 -- docs/WORKLOG.md`).

## S12 — Generic HTTP 503 fallback copy (87015d8 / 2bf4e73)
Done: `logic.js` now gives unmapped HTTP 503 responses explicit temporary-unavailability copy; regression test added to `tests/run.js`. Existing mapped payment 503 errors retain their contract-specific copy.
Not done / BLOCKED: tests were not executed in this session; connected Desktop Commander devices were offline and GitHub file API does not provide a local test runtime. No CSS/theme changes: safe-area nav/CTA rules already exist in `components.css`; Gul/Jurnal/Stone tokens are not defined in current `tokens.css`, so their palettes were not invented.
Next: run `node design-prototype/tests/run.js`, then the browser sweep because UI-facing error copy changed; inspect CI result.
Evidence: source + regression test committed on `design/prototype`; execution evidence pending.

### S11 — Time-boxed push permission recorded
Done: owner granted repeated use (no re-asking) of the 2026-10-20 token until 2026-10-27 for push + read-only API; documented in CLAUDE.md §5 without the token.
Next: owner sets the token's own expiry to 7 days and revokes it on 2026-10-27; afterwards use env-based auth.

### S10 — Push completed (`88b410a`)
Done: owner supplied a one-off token; pushed `design/prototype` via a per-command header (token never stored); verified remote == local without credentials; CLAUDE.md §5 now documents the owner-supplied-token exception.
Not done: CI fix-ups (see snapshot for the read-out); token revocation is the owner's action. Evidence: `git ls-remote --heads origin design/prototype` = local HEAD.

### S9 — CLAUDE.md + WORKLOG (`c643b03`)
Done: created `CLAUDE.md` (credit-saving rules, commands, product rules, git/push policy, session protocol) and this worklog. Owner granted standing permission to push without asking (merge/force/deploy still need explicit instruction).
Not done: push (BLOCKED, no auth). Evidence: files exist; no secrets (scanned). Commit: see `git log -1 -- CLAUDE.md`.

### S8 — Decisions D1–D5 + backend audit (`dbc9113`)
Done: fee policy unconfigured by default (503), integer tiyin/BigInt money, availability containment (backend already did it), "Maxsus kunlar", user-id vs profile-id reports (prototype stopped sending profile ids), mock aligned with real backend, 50 real-backend tests, OpenAPI overlay (proposal only), staging readiness doc, audit report.
Not done: staging/real devices/CI/push (BLOCKED); delivery-fee schema & mapping (backend work).
Evidence: `design-prototype/reports/test-report.md`, `reports/backend-audit.md`.

### S7 — Backend decisions round 1 + push (`065741f`, pushed)
Done: report target = user id and cancellation/refund = undefined decisions applied to copy/docs; F7b test. Push succeeded once with a user-supplied token (token now compromised/revoked: never reuse).

### S6 — Iteration 5, component library, companion/vendor flows, 6 screens, real-browser tests (`f9a6331`)
Done: component library + gallery, companion and vendor flows to the contract, six standalone screens, Chromium harness (overflow, touch, clipping, measured contrast, occlusion, axe), 11 defects found/fixed, PostgreSQL 16 validation (200/200).
Key corrections found: payment only after `accepted`; gift+booking checkout always 503; backend error envelope is flat.

### S1–S5 — Audit, brand, tokens, first prototype, iterations 1–4
Done: repo audit; brand directions → logo (angled-Y, 4 themes); tokens + measured contrast; first prototype; iteration reports 1–4 and honest scoring (`design-prototype/reports/`).

## Template for a new entry (prepend above)
### S<n> — <title> (`<short sha>` or "uncommitted")
Done: <what changed, files>
Not done / BLOCKED: <what and why>
Next: <what the next developer should do first>
Evidence: <test command + counts, report path>
