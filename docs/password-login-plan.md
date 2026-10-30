# Password login — plan (S38, 2026-10-29)

Status: **PLAN ONLY. Nothing is built.** Owner decision of 2026-10-29: add password login (phone + password) next to phone + code,
because a code per login is slow and costs money (CLAUDE.md section 7). TZ.md section 42 says "Phone number → OTP" (later Google/Apple), so it
needs an owner-approved amendment first (AGENTS.md: do not change product docs unless asked).

## What the code does today (read-only inspection)
- `apps/api/src/yondo_api/auth/service.py`: 6-digit code, 5 min life, 60 s resend cooldown, 3 wrong tries lock the number for 60 s; the user row is created on the first verified code (`verification_pending`). Session = `auth_sessions` row, access token 15 min, **refresh token 30 days** (`YONDO_AUTH_REFRESH_TOKEN_LIFETIME_SECONDS`).
- `apps/web/src/api/client.ts`: tokens live in **`sessionStorage`** (cleared with the tab). So every new tab/browser start asks for phone + code again even though the server would keep the session for 30 days. This is most of the pain the owner describes, and it is fixable without a password.
- No password library in `apps/api/pyproject.toml`; 17 migrations (latest `20261023_0017_booking_expired.py`); web login = `apps/web/src/pages/Login.tsx` (226 lines) + `Login.test.tsx`; Settings = `pages/Settings.tsx`.

## Proposal
**Phase 0 — "remember this device" (no TZ change, no new endpoint, small).** Optional checkbox on login keeps the refresh token in `localStorage` for the 30 days the server already allows; unchecked = today's behaviour. Trade-off: a persistent token is exposed to XSS longer than a tab-scoped one (mitigations: short access token, refresh rotation already exists, Logout revokes the session).

**Phase 1 — password (backend).** Migration `0018`: `users.password_hash` (nullable), `password_set_at`, failure counter + `password_blocked_until`. Hash: **argon2id** (`argon2-cffi`, new dependency; alternative: stdlib `hashlib.scrypt`, no new dependency). New endpoints (additive, v1, OpenAPI regenerated):
- `POST /auth/login` {phone_number, password} → tokens. One generic error `invalid_credentials` for wrong password, unknown number and "no password set" (no account enumeration; a dummy hash check keeps timing equal). 5 wrong tries → 15 min lock (`password_temporarily_blocked`, 429). Suspended/banned accounts stay blocked as in the code flow.
- `PUT /auth/password` (signed in): set the first password; change needs the current one. Revokes the user's other sessions.
- `POST /auth/password/reset` {phone_number, code, new_password}: uses the existing code flow (`/auth/otp/request`) to prove the phone, sets the password, revokes all sessions.
- `GET /auth/me` gains `has_password`.
- Policy (default): 8–128 chars, no composition rules, reject numeric-only, equal-to-phone and a small common-password list. Branch on error `code`, never on message text (CLAUDE.md section 4).

**Phase 2 — web.** Login: phone → "Parol bilan kirish" (phone + password) or "Kod bilan kirish"; "Parolni unutdim" = code → new password. Settings: set/change password. After the first code login a skippable "set a password?" hint. All text through `apps/web/src/i18n` (uz/ru/en; 1995 uz derived from 2026). Update `Login.test.tsx`; a11y + sweep only if CSS changes.

**Phase 3 — verification and docs.** Backend tests (set, login, wrong/locked, unknown number, reset, session revocation, suspended user, migration up/down on PostgreSQL), OpenAPI `--check`, web vitest, e2e login flow, secrets scan. Docs: TZ.md section 42 amendment (owner), `docs/frontend-api-integration.md`, privacy policy mention (the owner drafts; version bump), WORKLOG. Roles (S36): backend, front-end, **verifier approves before any commit**.

Cost: no external service; argon2 runs on the server CPU (Render free is slow: tune cost parameters).

## Decisions for the owner (defaults in bold)
1. Do Phase 0 first? **Yes** (cheapest fix for the daily pain).
2. Password rule: **min 8 characters, no composition rules**?
3. Forgot password via a code (one paid Telegram code per reset): **yes**?
4. Admin accounts: **always code, no password** (a stolen password must not open the admin console)?
5. Password after first login: **optional (skippable)**, not mandatory?
6. TZ.md section 42: may I draft the amendment text for your approval? **Yes**.
