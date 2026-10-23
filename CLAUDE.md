# CLAUDE.md — YONDO working rules (read first, ~2 min)
Also read `AGENTS.md` (repo rules; not repeated here) and **`docs/WORKLOG.md` → "Next steps"** before doing anything. Do not re-audit items the worklog marks PASS with evidence.

## 1. Save credits (limits are real)
- Start from WORKLOG "Next steps"; read only the files that task needs. `TZ.md`, `docs/openapi-v1.json` and test logs are large: query them (`grep -n`, `sed -n 10,40p`, `python -c` over the JSON), never `cat` them.
- Cap every command's output (`| tail -n 20`, `| head`, `cut -c1-160`). Print counts and failures, not logs.
- Batch independent commands in one tool call. Create a file in one call; edit with targeted replace + `assert count==1`, not by rewriting whole files.
- Run the smallest test first (`-k`, one file); the full suite once at the end. Run the browser sweep only if UI/CSS changed (chunks ≤ 290 s). Do not view screenshots unless debugging visuals.
- Reuse what exists: venv, `node_modules` tools dir, PostgreSQL cluster (see §3). Do not reinstall or regenerate artifacts that are already current.
- Do not retry a failing network call blindly. Do not ask the owner for anything discoverable in the repo; ask only for external values (URLs, accounts, secrets via a secure channel).
- **If a limit looks near: stop starting new work, finish the WORKLOG entry (§6), commit, make the bundle, then stop.**

## 2. Where things are
- `apps/api` FastAPI backend (16 migrations, 218 tests on PostgreSQL). `apps/web` = the real web app + secured admin console (React/TS/Vite, talks to the real API via `/api`; see `apps/web/README.md`, `docs/web-and-admin.md`). `apps/mobile` is a README stub; `apps/admin/README.md` points to `apps/web/src/admin`.
- `marketing/ad-video/` = promo-video pipeline (scripts only, no audio/video committed; see its README). Screens: `capture_proto.mjs` (design-prototype) or `capture.mjs` (apps/web). Owner video rules: 9:16 + 16:9, UZ + RU, voices from voicelab.uz supplied by the owner, **no DEMO labels in the video**, only ink/paper/carrot.
- `docs/openapi-v1.json` = API contract (CI keeps it in sync). `docs/frontend-api-integration.md` = client rules.
- `design-prototype/` = brand, tokens, component library, mock-backed prototype, tests, reports. Start at `design-prototype/docs/02-handoff.md`, decisions in `docs/03-decisions-and-contract.md`, staging in `docs/04-staging-readiness.md`, evidence in `reports/test-report.md` and `reports/backend-audit.md`.
- Prototype sources: `prototype/src/{logic,mockapi,components,app,roles}.js`, `design-system/{tokens.*,components.css}`; `node design-prototype/prototype/build.js` builds `prototype/index.html`, `screens/*.html`, `design-system/gallery.html`. Never hand-edit the built files.

## 3. Commands (verified; Windows/PowerShell note: use `;` not `&&`, set env with `$env:NAME='x'`)
- Backend (from `apps/api`): `python -m pytest -p no:cacheprovider -o console_output_style=classic` (**no `-q`**: it hides the summary line). Lint `ruff check .`; contract `python export_openapi.py --check`.
- PostgreSQL (required for 4 concurrency tests; SQLite skips them): Linux `apt-get install -y postgresql`, `pg_ctlcluster 16 main start` (it can stop between sessions), create role/db, then set `YONDO_DATABASE_URL` and `YONDO_TEST_DATABASE_URL` (`postgresql+psycopg://…`) and run `python -m alembic upgrade head`. Windows: use the repo's `compose.yaml` (`docs/development.md`).
- Real-backend decision tests: `cd apps/api; python -m pytest ../../design-prototype/tests/backend -c pyproject.toml --rootdir .`
- Prototype logic/mock/contract tests: `node design-prototype/tests/run.js` (needs `ajv`, `ajv-formats`; set `AJV_PATH`/`AJVF_PATH` if not on `NODE_PATH`).
- Chromium tests: tools dir with `@sparticuz/chromium puppeteer-core ajv ajv-formats axe-core`; `NODE_PATH=<tools>/node_modules`; flows `SWEEP='[]' node tests/browser.js`; sweep `AXE=1 REALFONTS=1 SWEEP='[360,1440]' ONLY_SWEEP=1 node tests/browser.js`; gallery `GALLERY=1`. `REALFONTS` reads Inter/Space Grotesk TTFs from a hard-coded path in `tests/browser.js`: adjust it for your machine.
- Gotchas that cost time: the tool shell is `sh` (no `${PIPESTATUS}`); background processes die between calls; mobile emulation inflates `innerWidth` (tests use `window.__W`); Google Fonts are blocked in tests; `git commit` needs `-c user.name="Claude" -c user.email="noreply@anthropic.com"` if no identity is configured.

## 4. Non-negotiable product rules (do not invent business rules)
- Never invent: platform fee, delivery fee, cancellation percentage, refund amount, payout rules. Unset ⇒ show "Aniqlanmagan"/503. The ⚙ DEMO fee policy is a labelled fixture only.
- Booking create takes exactly 5 fields (service_id, starts_at UTC instant, duration_minutes, meeting_place, timezone). Pay only when `accepted` (`Idempotency-Key` required); success ⇒ `confirmed`. Gifts are a separate cart/test-order flow; booking+gift checkout is always 503.
- 503 (provider/config unavailable) is never shown as "payment declined". Test/demo payments are simulations; no real charge/refund is ever attempted.
- Verified badge only from the API `verified: true`. Branch logic on error `code`, never on message text.
- Money = integer tiyin (100 = 1 UZS), no floats (`logic.js`: `money`, `toMinor`). Times = ISO instants with `Z`/offset (UTC). Availability filter = full containment; booking conflicts stay in force.
- `reported_user_id` / block target = **user id**, never a companion profile id. Customers currently cannot report/block companions (no mapping): do not paper over it.
- SOS = a recorded alert for manual review; never claim emergency services, trusted contacts or tracking were notified. Show "Maxsus kunlar" for category `romantic`. Mark sample data DEMO. Product is NOT a dating/escort service: no romantic imagery/wording.
- Report results with labels **PASS / FAIL / BLOCKED / NOT IMPLEMENTED / OUT OF SCOPE**. Never claim a check that was not run.

## 5. Git and push policy (standing owner permission)
- The owner permits pushing **without asking**: at the end of every work session, commit verified work and push the working branch (currently `design/prototype`), then verify with `git ls-remote --heads origin <branch>` == local HEAD.
- This permission does **not** cover merging into the default branch, force-push, deleting branches, opening PRs, or deploying: do those only on an explicit instruction.
- Preferred authentication comes from the environment: `gh auth login`, Git Credential Manager, SSH key, or a `GH_TOKEN` env var set outside chat. Never ask the owner to paste a token.
- **Time-boxed standing permission (granted by the owner 2026-10-20, valid until 2026-10-27 inclusive):** the one-off GitHub token the owner supplies in chat (the 2026-10-20 token, fingerprint `…QY0qf`) may be used repeatedly, **without asking again**, for exactly two things: `git push` of the current working branch (`design/prototype` or another feature branch) and read-only GitHub API calls (e.g. Actions status). Not covered: merge/force-push/branch deletion/PRs/deploy/repo settings or secrets. The earlier token (fingerprint `…QY0TC`) was declared compromised and is **never** used. After 2026-10-27, ask before using any token again; without a new permission, treat push as BLOCKED.
- How to use a supplied token: keep it in a shell variable only, pass it per command (`git -c http.https://github.com/.extraheader="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$T" | base64 -w0)" push origin <branch>:<branch>`), redact output, `unset` it, verify with `git ls-remote --heads origin <branch>`. **Never write the token into any file, remote URL, git config, log, commit or report: this repo is public and GitHub auto-revokes leaked tokens.** The owner must paste the token into each new Claude session themselves (sandboxes do not persist it).
- If no auth exists: commit locally, `git bundle create design-prototype.bundle origin/codex/notification-integration..<branch>`, log **BLOCKED (push)** in the WORKLOG, continue with local work. Do not ask repeatedly.
- Stage only intended paths (`git add <paths>`, then check `git diff --cached --stat`); scan for secrets before committing; do not mass-format (50 files drift under `ruff format`; CI does not enforce it).

## 6. Session protocol (so the next developer can continue)
1. Start: read WORKLOG "Next steps"; `git status`, `git log --oneline -3`; verify branch/remote SHA.
2. Work in small steps; after each meaningful step run its focused test.
3. **End (always, even if stopping early):** prepend an entry to `docs/WORKLOG.md` using the template there (Done / Not done / Next / Blockers / Evidence / Commit); update "Next steps"; commit; push (§5).
4. Keep entries short (≤ 25 lines). After ~10 entries, move the oldest to "Archive" at the bottom.

## 7. Owner decisions and preferences (living log — append, never delete; newest last)
Keep this list current: when the owner states a preference or decision, add one line here in the same session.
- Language: answer the owner in **Uzbek** (Latin). Owner sometimes writes Russian/English.
- Product: Yondo = companion discovery/booking ("hamroh topish"), **never** dating/escort. Slogan: **"Yondo doim yoningda"** (RU: "Yondo. Всегда рядом.").
- Backend is the real FastAPI API; **no Supabase**, no duplicate tables. Admin must be server-authorized; no client-trusted roles.
- Brand/logo: `design-prototype/brand/logo` (Y-fork with nodes, wordmark = outlined paths, never retyped). Logo colours: ink `#111111`, paper `#F5F2EC`, carrot accent `#E8501A` (graphic only, never small text: 3.36:1 on paper).
- **"Yondo" themes (owner rule, 2026-10-22): only white/paper, black/ink and carrot `#E8501A` — no other hue** (greys only as ink/paper mixes; status colours collapse to ink + carrot border, meaning carried by words). Two variants: `yondo` (kunduzgi/day: paper ground, ink actions) and `yondo-tun` (tungi/night: ink ground, paper actions). Glow is carrot at low opacity, never mixed into brown/peach. Other themes (Gul/Jurnal/Stone) stay available in Settings.
- Theme switcher lives **only in Settings** (`/settings`), not in the top bar. Settings is linked from Account and Login.
- Style the owner wants: glass UI (frosted, translucent, blur) + strong but meaningful motion; `prefers-reduced-motion` respected.
- Promo video (2026-10-22, for the owner's own viewing, not an official ad): 9:16 + 16:9, Uzbek + Russian, voices from voicelab.uz supplied by the owner (3 speakers: **A narrator = woman, B customer = young man, C companion = young woman**; lines 1/3/7 = A, 2/5 = B, 4/6 = C). Owner asked to **remove every "DEMO" label from the video**; screens use seed names without the DEMO prefix and the "Yondo" theme. Music and SFX are original synthesis. Voice script: `marketing/ad-video/README.md`.
- voicelab.uz is not reachable from the cloud sandbox (proxy 403); the owner generates voices and uploads them.
- Push: still BLOCKED by the session permission classifier even with a pasted token or the GitHub connector; do not work around it. Local commits + `git bundle` are the fallback. Tokens pasted in chat are considered exposed: owner should revoke them.
- Motion (owner, 2026-10-22): animate every button and every page (login, home, lists, sheets, success states); my choice of effects; always respect `prefers-reduced-motion` (S16, design-prototype).
- Promo video (owner, 2026-10-22): illustrate every spoken line with pictures (e.g. "Yangi shahar" → a city behind the text); line-art in ink/paper/carrot only (S18). Voices: `yondo-ovozlar.zip` (uz+ru, 24 kHz mono) supplied in chat, not committed.
- Languages (owner, 2026-10-23, S21): make the project multilingual — `apps/web` now ships **uz (default) / ru / en**; switcher only in Settings; no browser auto-detect; new UI text must go through `apps/web/src/i18n` (`t('key')`, add the key to uz.ts, ru.ts and en.ts).
- Uzbek orthography (owner, 2026-10-23, S22): Uzbek UI text uses the **new 2026 Latin alphabet** (`sh→ş ch→ç o‘→ö g‘→ğ`; `ng` = n+g; tutuq `ʼ`); `apps/web/src/i18n/uz.ts` rewritten. The top bar now also holds a compact UZ|RU|EN language switch (theme switcher still only in Settings).
- Uzbek alphabets (owner, 2026-10-23, S23): **both** variants are kept — 1995 (o‘ g‘ sh ch) and 2026 (ö ğ ş ç); `uz.ts` stays in 2026 spelling, 1995 is derived; default = 1995 until 2027-04-22, then 2026; choice in Settings, saved to the account (`users.ui_locale`); server search matches both spellings.
- Help & safety (owner, 2026-10-23, S23): `/help` page (112, reports, trusted contacts, FAQ) + Profile hub menu + Settings groups; customers report a companion **via booking_id** (server derives the user, option C). Still not built: account deletion, support channel, SOS in web, block by booking.
- Account/legal/support (owner, 2026-10-23, S24): in-app account deletion — personal data erased or de-identified **within 30 days**, legally needed records kept de-identified (daily job `python -m yondo_api.account.jobs` must be scheduled); support = **in-app request form only** (no e-mail, phone only if a real line exists; response time/hours not defined); Terms of use + Privacy policy as **separate pages** (`/terms`, `/privacy`, owner drafts, Uzbek first) with versioned consent recorded at login. **SOS in web and block-by-booking = next stage**, not now. Legal review before publication: owner says not required. Checklist: `docs/legal/pre-publication-checklist.md`.
- Push (2026-10-22, S16–S18): works from a cloud session once the repo is attached via the session's GitHub connection (no pasted token); the bundle from the blocked session was merged into `design/prototype` (merge commit, no force-push).
- Promo video (owner, 2026-10-23): **no subtitles**; the RU cut must show the app **fully in Russian** (capture-time translation via `marketing/ad-video/ru-dict.json` until `apps/web` gets a RU locale).
