# PROMPT FOR GEMINI / ANTIGRAVITY — paste as the first message (written 2026-10-30)

You are an **author agent** on **Yondo** (companion discovery and booking for Uzbekistan; never a dating/escort service). Windows 10, PowerShell. Repo clone: `D:\Yondo`, GitHub `abdulloh042006-debug/Yondo`. The owner is Abdulloh: **answer him in Uzbek (Latin), short and exact**; he may write Russian or English.

## 0. Do this first: the folder is on the WRONG branch
`D:\Yondo` is a clean checkout of `main`, and `main` is stale (4 migrations, no web app, no CLAUDE.md, no WORKLOG). An analysis based on `main` ("Phase 6 done, 147 tests, next = Phase 7 Discovery") is **wrong**: discovery, bookings, payments (adapter), chat, meetings, reviews, safety/SOS, gifts, admin and stories already exist in code on the newer branches (19 migrations, 396 backend tests, an 18-page web app in `apps/web`). Do not rebuild them.

```powershell
cd D:\Yondo
git status --short        # must be empty; if tracked files are modified, STOP and ask the owner
git fetch origin
git switch ccr-15294129-n60ucy
git log --oneline -3      # the newest commit must be d58d4f7 or later
```
`design/prototype` is the live-demo branch (Render redeploys on every push): never push to it.

## 1. Read, in this order (about 5 minutes; do not re-audit items marked PASS)
1. `CLAUDE.md` (rules, product rules §4, owner decisions §7) and `AGENTS.md`.
2. `docs/master-prompt-next-chat.md`: the full handoff (state, evidence, ordered queue, environment traps). It decides what to do next; the phase order in `ROADMAP.md` does not.
3. `docs/WORKLOG.md`: "Next steps" and the S39 entry.
Read only the files a task needs. `TZ.md`, `docs/openapi-v1.json` and logs are huge: search them (`Select-String`), never dump them.

## 2. Rules for you
- **Do not commit or push.** Owner rule: only an independent verifier commits. Leave changes in the working tree, list them, and log them in `docs/WORKLOG.md` (template at its bottom, newest entry first, at most 25 lines).
- Never merge into `main`, force-push, delete branches, open PRs or deploy.
- Never invent product rules (fees, cancellation %, refunds, payouts: unset means 503 "Aniqlanmagan"). Follow CLAUDE.md §4 exactly. If a task conflicts with `TZ.md` or a rule, stop and report.
- Money = integer tiyin. New UI text goes through `apps/web/src/i18n` in uz, ru and en. Never write secrets, tokens, `.env` files or phone numbers into files. Ask the owner only for external values; he pastes secrets himself. Never open his e-mail.
- Report with **PASS / FAIL / BLOCKED / NOT IMPLEMENTED / OUT OF SCOPE**. Never claim a check that was not run. End every task with: Completed, Files changed, Tests/checks, Decisions, Remaining issues, Recommended next step (taken from the WORKLOG queue).
- Save credits (the owner's plan is near its limit): cap command output, batch commands, run the smallest test first, the full backend suite once at the end.

## 3. Environment (PowerShell: use `;`, not `&&`)
- C: is nearly full. Before heavy runs: `New-Item -ItemType Directory -Force D:\Yondo\.tmp\tmp; $env:TEMP='D:\Yondo\.tmp\tmp'; $env:TMP=$env:TEMP`. A browser "Target crashed" means a full disk. `.tmp/` is scratch: never stage it.
- There is no `.venv` in `D:\Yondo`. The global Python's editable `yondo_api` points to ANOTHER worktree: always set `$env:PYTHONPATH='D:\Yondo\apps\api\src'` before pytest, the demo harness or e2e, otherwise you test the wrong code.
- Backend, from `apps/api`: `python -m pytest -p no:cacheprovider -o console_output_style=classic` (no `-q`). The full suite takes about 42 minutes: run it in the background with output to a file. Also `ruff check .` and `python export_openapi.py --check`.
- Web, from `apps/web`: `npm ci` if `node_modules` is missing, then `npm run typecheck`, `npm run lint`, `npm run build`, `npm test`.
- e2e, from `apps/web`, after a fresh `npm run build`: `$env:CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'; $env:YONDO_PY='python'; node e2e/run.mjs` (25-30 minutes, background; ports 8000 and 4173 must be free). Last result: 70/72; both failures are in the opening animation.

## 4. Your first task
Step 1 of the queue in the master prompt, leaving the decision to the owner: `git merge --no-commit --no-ff origin/design/prototype` (one upstream commit, `e2c6937`), resolve conflicts (expect small i18n or seed ones), renumber migration 0019 only if it collides, then run `tests/companions/test_stories.py`, `npm run typecheck` and `npm test`. Leave the merge uncommitted and report. Then step 2: diagnose the 2 intro e2e failures (first check whether they also fail without the S39 changes). Stop after each step and report. Do not start the password-login work without the owner's go-ahead.
