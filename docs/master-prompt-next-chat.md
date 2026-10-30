# MASTER PROMPT — paste this as the first message of a new chat (written 2026-10-29, end of S39; folder paths fixed 2026-10-30)

You are continuing work on **Yondo** (companion discovery and booking for Uzbekistan; never a dating/escort service). Repo: `https://github.com/abdulloh042006-debug/Yondo`. Windows 10, PowerShell + Git Bash, Claude Code desktop. Everything here is the starting state; verify facts marked *(verify)* with one cheap command.

## 0. Owner and limits
- Owner: **Abdulloh** (head of IT at a university, not a full-time DevOps). **Answer in Uzbek (Latin)**, short and exact, no jargon without a one-line explanation. He may write Russian/English.
- **His Claude Pro weekly limit was at 94 % on 2026-10-29** (reset Tue 5:00 PM). Save credits: read only what the task needs, cap command output, no long essays, run the full backend suite once at the end (about 42 min on this PC, run it in the background).
- Account creation, passwords, card data, domain purchase, sign-ins and secrets are **his** steps. Never ask him to paste secrets in chat; never open his e-mail. Report with **PASS / FAIL / BLOCKED / NOT IMPLEMENTED / OUT OF SCOPE**; never claim a check that was not run.

## 1. Read first (about 5 minutes; do not re-audit PASS items)
1. `CLAUDE.md` (rules, product rules §4, owner decisions §7) and `AGENTS.md`.
2. `docs/WORKLOG.md`: the **S39** entry (newest) and "Next steps".
3. `docs/stories-avatars-design.md` (the S39 design) and, for the password-login work, `docs/password-login-plan.md` (**it was never on GitHub (an untracked local file of another chat) and as of 2026-10-30 it is gone from `D:\Yondo` and was not found on D: or in the Copilot worktrees**: ask the owner for a copy, otherwise rebuild the plan from the S38 decision in CLAUDE.md §7).

## 2. Where the code is (one local folder: `D:\Yondo`)
- **Work in `D:\Yondo`.** As of 2026-10-30 it is a clean checkout of **`main`, which is stale** (4 migrations, no web app, no CLAUDE.md, no WORKLOG). An analysis that reads `main` wrongly concludes "Phase 6 done, 147 tests, next = Phase 7": do not trust it. Switch first: `git fetch origin; git switch ccr-15294129-n60ucy` (if `git status` shows modified tracked files, stop and ask the owner).
- **`ccr-15294129-n60ucy`** (the cloud chat's branch) is the newest: **S39 work, pushed as an UNVERIFIED work-in-progress commit** (see §3). `design/prototype` is the live-demo branch (Render redeploys on every push). The old second folder `D:\Yondo-ccr` **no longer exists**, and the old local-only files of `D:\Yondo` (`.venv`, `reports/`, `research_notes/`) are gone too: recreate what you need (§6).
- The branches **diverged**: `origin/design/prototype` has 1 commit that `ccr` lacks (`e2c6937`, removes "til mashqi" from copy, seeds, prototype and video scripts); `ccr` has 13+ commits that `design/prototype` lacks (warm skin, opening animation, S37 backend, S39). Merge-base `f93ccc7`. A fast-forward is impossible: plan one merge (`git fetch`, then merge `origin/design/prototype` into `ccr`, then resolve; expect small i18n/seed conflicts). Do not merge into `main`, force-push, open PRs or deploy without an explicit owner instruction (CLAUDE.md §5).
- Migration **0019** (`20261029_0019_companion_stories.py`) may collide with the password-login chat's migration: renumber at merge time and re-run `alembic upgrade head` on SQLite and PostgreSQL.

## 3. What S39 built (stories + avatars, decided by the commander, NOT reviewed by the owner)
- Customers never upload a face: generated **ornament avatar** (12 patterns x 3 grounds x 2 folds) derived from the account id, same on every device. Companions keep their moderated photo.
- **Only companions post stories ("cards")**, card-first (`availability` built from live free windows, `note` caption <= 80 chars), 24 h, 5 active, 10 per day, no video, no viewer tracking, seen state only on the device.
- Backend: `apps/api/src/yondo_api/stories/`, migration 0019, `tests/companions/test_stories.py`, account-deletion cleanup, OpenAPI regenerated. Web (`apps/web`): `Avatar`, story-ring strip on Discovery, `StoryViewer`, report sheet, "Cards" tab in Studio (route `studio/cards`), `?service=` preselect in Profile, 87 i18n keys x 3 languages, `schema.d.ts` regenerated.

## 4. Evidence so far (labels honest)
- Backend, SQLite: **396 passed + 9 skipped** (2553 s) = PASS. ruff and `export_openapi.py --check` = PASS. PostgreSQL run: NOT RUN for S39.
- Web (author's own run, not re-run by the verifier): typecheck, lint, build PASS; vitest 156/156.
- e2e (`node e2e/run.mjs`, Edge, 2026-10-29): **70/72**. FAIL: "intro: first visit shows the opening animation ... auto-closes in ~3 s" (took 3941 ms, expected ~2.8 s) and "intro: mid-animation screenshots" (`getBoundingClientRect` of null). Cause undiagnosed; S39 touched `App.tsx` by one route line only. **The e2e suite has no step for stories/avatars.**
- **NOT RUN:** axe pass on the new screens, keyboard-only pass, reduced-motion pass, visual check at 360 / 390 / 1440, independent verifier.
- **NOT IMPLEMENTED:** avatar picker in Settings and `users.avatar_code` (auth code was off limits; waits for the password-login work). Uzbek text of S39 is the agent's, not owner-reviewed.

## 5. Work queue (in order; one small verified step at a time)
1. **Sync the branches** (§2), renumber migration 0019 if needed, re-run the focused tests (`tests/companions/test_stories.py`, i18n key parity, `npm run typecheck`).
2. **Close the S39 verification gaps:** diagnose the e2e failures listed in §4 (check first whether they also fail on the commit before S39: the intro-animation timing step is not a stories step), then axe, keyboard-only, reduced-motion and the three viewport checks on Discovery strip, StoryViewer, report sheet and Studio Cards.
3. **Independent verifier pass** (read-only agent: full backend + web suites, diff scope, secrets scan, CLAUDE.md §4). The S39 commit is a WIP pushed at the owner's order without it (the same waiver as S36): nothing from `ccr` goes into `design/prototype` or the demo before the verifier says APPROVE.
4. **Owner review of the S39 decisions** (ask him once, in Uzbek, as a short list): auto-advance timing of a card; whether a note may carry a photo; when the avatar picker is built; whether a companion may see a customer's avatar before a booking.
5. **Password login** (owner decision 2026-10-29: phone + password next to phone + code; code for sign-up, new device, reset). Plan in `docs/password-login-plan.md`; needs a TZ.md amendment the owner approves, a hash migration, rate limit and lockout, OpenAPI export, uz/ru/en UI. Then the avatar picker.
6. **Older queue:** WORKLOG "Next steps" item 000 (verifier pass over earlier unverified commits, schema regeneration, warm-skin follow-ups) and the owner items 0b, 00c, 00d, 00e.

## 6. Environment traps (these cost hours)
- **C: was filled to 0 bytes once; it has about 10 GB now.** Put temp on D: for heavy runs: `$env:TEMP='D:\Yondo\.tmp\tmp'; $env:TMP=$env:TEMP` (create the folder first). Browser "Target crashed" = disk full, not a code bug.
- **The global Python's editable `yondo_api` points to another worktree** (`C:\Users\T31\copilot-worktrees\...`; there is no `.venv` now). Always set `PYTHONPATH=D:\Yondo\apps\api\src` (or `pip install -e apps/api` from `D:\Yondo`) for pytest, e2e and the demo harness, otherwise you test the wrong code.
- e2e (from `apps/web`, needs a current `dist`: run `npm run build` after any `src` change): set `CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'`, `YONDO_PY=python`, `PYTHONPATH` as above; run it in the background with output to a file (about 25-30 minutes; ports 8000 and 4173 must be free).
- Backend suite: `python -m pytest -p no:cacheprovider -o console_output_style=classic` from `apps/api` (no `-q`); never inside a 900 s limit. `.tmp/` is untracked scratch: never stage it.
- Pushing works from this machine (credentials present). Never write a token into any file.

## 7. Product rules that bite (full list in CLAUDE.md §4)
Never invent fees, cancellation or refund rules; money = integer tiyin; verified badge only from the API; branch on error `code`; reports/blocks go through `booking_id`, customers never get a companion's user id; SOS = a recorded alert, never "help was sent"; no romantic imagery or wording; new UI text goes through `apps/web/src/i18n` (uz, ru, en); Uzbek UI keeps the 2026 spelling in `uz.ts`.
