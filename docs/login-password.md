# Username + password login (backend)

Built 2026-11-15 from `docs/product-decisions.md` §3 and §6 and the owner's addition of a
**username** ("login"). Web and mobile screens: see "Clients" below (S68). Design history:
`docs/auth-password-login.md` (plan).

## Flows

1. **Registration:** phone → code (`/auth/otp/request` + `/auth/otp/verify`; the Telegram bot on
   the demo, an SMS provider later through the same slot) → `POST /auth/registration` with
   `{username, password}`. The account is then complete.
2. **Sign-in:** `POST /auth/password/login` with `{login, password}`, where `login` is the
   username or the phone number. Sign-in with a code (phone + OTP) stays available.
3. **Change:** `PUT /auth/password` with `{current_password, new_password}` returns 204 and
   signs out all **other** sessions.
4. **Forgotten password:** `/auth/otp/request` for a code, then `POST /auth/password/reset` with
   `{phone_number, code, new_password}`. It returns a new token pair and signs out **all** old
   sessions.
5. **Username check:** `GET /auth/username/available?username=` returns
   `{username, available, reason: invalid|reserved|taken|null}`. Rate-limited per IP.
6. `GET /auth/me` adds `username`, `has_password` and `password_setup_required`. Only the account
   owner ever sees their username.

## Rules

| What | Rule |
|---|---|
| Password | 8–128 characters, not the phone number (in any common spelling), no composition rules |
| Hash | stdlib `hashlib.scrypt`, random 16-byte salt, stored as `scrypt$<log2 N>$<r>$<p>$<salt>$<key>` (N = 2^17, r = 8, p = 1 by default), at most 2 hashes at a time |
| Username | 3–30 characters of `a–z 0–9 _ .`, starts with a letter, no `..`, stored in lower case, unique; reserved names (admin, administrator, yondo…, support, help, sos, api, root, moderator, system, null and similar) are refused |
| Privacy | The username is a login identifier only. It is never in discovery, profiles or another user's payload. |
| Wrong password | 5 failures lock that account's password login for 15 minutes. The counter is per account, whether the username or the phone was used. |
| Unknown login | Gets the same 401 `invalid_credentials` as a wrong password, with the same hashing work and the same lock after 5 tries, so nothing reveals whether a login exists. The only deliberate exception is the availability endpoint. |
| Per IP | 20 attempts per minute per client IP, counted separately for login, reset and the username check. In-process memory, so one API instance (see "Deploy note"). |
| Registration | Needs a session created by a **code** sign-in at most 15 minutes ago (`reauth_required`). A stolen long-lived token cannot plant a password. |
| New device | No extra code (owner decision). |
| Logs | Plain passwords are never stored or logged. A structlog processor also redacts `password`, `code` and `token` fields. |
| Account deletion | Clears the username, the password hash and the attempt counter. The username becomes free again. |

## Error codes (branch on `code`)

`invalid_credentials` 401 · `password_login_blocked` 429 · `rate_limited` 429 ·
`account_unavailable` 403 · `weak_password` 422 · `invalid_username` 422 ·
`username_unavailable` 409 (reserved or taken) · `username_already_set` 409 ·
`registration_complete` 409 · `reauth_required` 403 · `password_not_set` 409 ·
`password_setup_required` 403 (only with the gate on) · the existing `invalid_otp`,
`otp_expired` and `otp_temporarily_blocked` on reset.

## Enforcement for accounts without a password

Existing accounts (seeded demo users and real ones) have no username or password, so their
`/auth/me` says `password_setup_required: true`. Clients must show the setup screen after a
code sign-in.

Server side, the setting `YONDO_AUTH_REQUIRE_PASSWORD_SETUP` turns on a gate. With the gate on,
such an account gets 403 `password_setup_required` everywhere except `/auth/*` and `/legal/*`.
**Default: off** in the code. The web and mobile setup screens shipped in S68 (#41). From 2026-11-16
the owner made the password mandatory: the public demo runs with the gate **on** (Render env
`YONDO_AUTH_REQUIRE_PASSWORD_SETUP=true`), so every visitor sets a username and password after a code
sign-in.

**Demo harness and the gate.** `infra/deploy/demo/demo_app.py` seeds and maintains the DEMO data by
signing in itself. That work (seed, admin-number refresh, availability top-up) goes through a second,
never-served app instance on the same database with the gate off (`build_app(..., internal=True)`).
The seeded DEMO accounts and the owner's admin number therefore never get a password nobody knows.
The served app follows the environment exactly; the owner too sets his own password on his first sign-in.
The web e2e and the video harness keep the gate off.

Always enforced regardless of the gate:
- registration needs a fresh code session;
- a password change needs the current password;
- a reset needs a code.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `YONDO_AUTH_SCRYPT_LOG_N` | `17` | scrypt cost, N = 2^value (14–20). 17 uses about 128 MiB and 0.1–0.3 s per hash. |
| `YONDO_AUTH_PASSWORD_IP_RATE_LIMIT_PER_MINUTE` | `20` | Per-IP attempts per minute (0 = off) |
| `YONDO_AUTH_REGISTRATION_WINDOW_SECONDS` | `900` | How fresh the code session must be for registration |
| `YONDO_AUTH_REQUIRE_PASSWORD_SETUP` | `false` | The setup gate above |

## Deploy note

The per-IP limit needs the real client IP:
- **DigitalOcean package:** uvicorn trusts the proxy's forwarded headers.
- **Demo on Render:** the harness does not, so every visitor counts as Render's proxy IP. That is
  20 password attempts per minute for the whole demo. It only affects the new password endpoints,
  which no client uses yet. Fix it with the server work.

With several API instances, move the counter to Redis.

## Clients (S68, 2026-11-15)

- **Kirish** (web `apps/web/src/pages/Login.tsx`, mobile `apps/mobile/src/screens/Login.tsx`): username or phone + password first, a code via Telegram second, "Parolni unutdingizmi?" = phone → code → new password. Errors are chosen by `code`.
- **Setup** (`apps/web/src/auth/PasswordSetup.tsx`, `apps/mobile/src/screens/Password.tsx`): shown after a code sign-in while `password_setup_required` is true. Help and the documents stay reachable. `reauth_required` sends the user back to a code sign-in.
- **Change** in Settings → Hisob. A 401 `invalid_credentials` there is a form error: the clients do not treat it as an expired session.
- **Face ID / fingerprint:** there is no in-app biometric lock (removed 2026-11-16 at the owner's word). The forms carry autofill hints (`apps/mobile/src/autofill.ts`; `autocomplete` on the web), so the phone's own password manager offers the saved login and unlocks it with Face ID or a fingerprint.
- **How long you stay signed in:** a session slides. Each refresh, which the app does on its own while in use, extends it to 30 days from that moment (`YONDO_AUTH_REFRESH_TOKEN_LIFETIME_SECONDS`). After 30 days without use, or 180 days after the sign-in however active (`YONDO_AUTH_SESSION_MAX_AGE_SECONDS`), the user signs in again. Logout, a password change (other sessions), a reset (all sessions), suspension and admin revocation still end sessions at once.
- Client-side rule mirror: `apps/web/src/lib/credentials.ts`. The server stays the authority.

