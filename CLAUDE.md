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
- `apps/api` FastAPI backend (14 migrations, 200 tests). `apps/mobile`, `apps/admin` are README stubs (no real client yet).
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
- Authentication must come from the environment: `gh auth login`, Git Credential Manager, SSH key, or a `GH_TOKEN` env var set outside chat. Never accept tokens pasted into chat, never write a token into a file, remote URL, log or commit. A token pasted in chat earlier is **compromised: never use it**.
- If no auth exists: commit locally, `git bundle create design-prototype.bundle origin/codex/notification-integration..<branch>`, log **BLOCKED (push)** in the WORKLOG, continue with local work. Do not ask repeatedly.
- Stage only intended paths (`git add <paths>`, then check `git diff --cached --stat`); scan for secrets before committing; do not mass-format (50 files drift under `ruff format`; CI does not enforce it).

## 6. Session protocol (so the next developer can continue)
1. Start: read WORKLOG "Next steps"; `git status`, `git log --oneline -3`; verify branch/remote SHA.
2. Work in small steps; after each meaningful step run its focused test.
3. **End (always, even if stopping early):** prepend an entry to `docs/WORKLOG.md` using the template there (Done / Not done / Next / Blockers / Evidence / Commit); update "Next steps"; commit; push (§5).
4. Keep entries short (≤ 25 lines). After ~10 entries, move the oldest to "Archive" at the bottom.
