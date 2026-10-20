## S12 — Generic HTTP 503 fallback copy (87015d8 / 2bf4e73)
Done: `logic.js` now gives unmapped HTTP 503 responses explicit temporary-unavailability copy; regression test added to `tests/run.js`. Existing mapped payment 503 errors retain their contract-specific copy.
Not done / BLOCKED: tests were not executed in this session; connected Desktop Commander devices were offline and GitHub file API does not provide a local test runtime. No CSS/theme changes: safe-area nav/CTA rules already exist in `components.css`; Gul/Jurnal/Stone tokens are not defined in current `tokens.css`, so their palettes were not invented.
Next: run `node design-prototype/tests/run.js`, then the browser sweep because UI-facing error copy changed; inspect CI result.
Evidence: source + regression test committed on `design/prototype`; execution evidence pending.

# WORKLOG — read this first, update it last
Newest entry first. Template at the bottom. Labels: PASS / FAIL / BLOCKED / NOT IMPLEMENTED / OUT OF SCOPE.

## Status snapshot
- Branch `design/prototype` (base `origin/codex/notification-integration`), **pushed** (remote SHA verified equal to local at `88b410a`; later docs-only commits may follow). Includes `dbc9113` (decisions D1–D5, audit) and `c643b03` (CLAUDE.md, WORKLOG). CI read-out for the push: no runs yet.
- Backend: PostgreSQL 16 200/200 PASS (SQLite 192 + 8 skipped); migrations 14 up/down/up PASS; 50 real-backend decision tests PASS on both DBs.
- Prototype (mock-backed, NOT a real client): node 40/40, Chromium E2E 39/39, sweep 63 (+3) over 9 configs × 25 views, gallery 5/5.

## Next steps (priority order)
1. **Owner: revoke the GitHub token pasted in chat on S10** and set up env-based auth (`gh auth login` / credential manager / SSH / `GH_TOKEN`) so pushes need no pasted token. Then read the CI result for `design/prototype` and fix any failure.
2. **Backend owner decisions needed:** delivery-fee configuration schema; profile→user id mapping (options A/B/C in `design-prototype/docs/03-decisions-and-contract.md`, unlocks customer-side report/block); CORS policy; whether to cap/stringify amounts > 2^53−1; apply `contract/openapi-v1.decisions.overlay.json` to the FastAPI models.
3. **Staging:** none documented. Obtain URL, test-login method (staging has no dev OTP; no SMS provider), payment sandbox, approved fee policy (`docs/04-staging-readiness.md`). Then add a read-only real-API contract check and an adapter that swaps the mock for the real client.
4. **Real clients:** `apps/mobile`/`apps/admin` are stubs. Build only if ROADMAP authorizes; reuse `design-prototype/design-system` and `prototype/src/logic.js`.
5. **Quality gaps:** native Uzbek copy review; real iOS Safari/Android, Firefox/WebKit and screen-reader testing; logo symbol outlining, kerning, similarity/legal check; merch + presentation (P1/P2) not started.
6. Housekeeping: decide on `ruff format` (50 files drift, not CI-enforced); keep screenshots/reports regenerated only when UI changes.

## Session log
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
