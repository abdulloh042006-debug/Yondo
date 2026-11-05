# Password login (phone + password) — design plan

Status: **PLAN, not built.** The owner approves it before any code is written.
Why: on 2026-10-29 the owner decided to add password login next to phone + code (CLAUDE.md §7, WORKLOG Next step 00a). Sending a code for every login is slow, and every Telegram Gateway code costs money.
Labels used here: **taklif** marks a proposed default that the owner decides (§8). Everything else is a technical consequence of today's code.

## 0. What exists today (facts, with sources)

- **Login is phone → 6-digit code only.**
  - `POST /auth/otp/request` returns 202 and `POST /auth/otp/verify` returns tokens (`apps/api/src/yondo_api/auth/router.py`).
  - If the phone is new, `verify_otp` creates the user with status `verification_pending` (`auth/service.py`).
- **Code limits** (`auth/service.py`): lifetime 5 min (`OTP_LIFETIME`), 60 s resend cooldown (error `otp_resend_cooldown`, 429), 3 wrong tries then a 60 s block (`OTP_MAX_ATTEMPTS`, `OTP_LOCKOUT`, error `otp_temporarily_blocked`, 429).
- **How the code is stored:** as an HMAC-SHA256 keyed with `auth_otp_pepper`, in `otp_challenges` (`models/auth.py`, `auth/service.py::_otp_hash`). Under PostgreSQL, requests for the same phone are serialised by a per-phone advisory lock.
- **Wrong or expired code** gives `invalid_otp` / `otp_expired` (401). A suspended or banned account gives `account_unavailable` (403).
- **Sessions:** opaque access and refresh tokens, stored only as SHA-256 hashes in `auth_sessions` (`models/auth.py`, `auth/service.py::create_session`). Lifetimes: access 900 s, refresh 2 592 000 s = 30 days (`config.py`). `/auth/refresh` rotates both tokens; `/auth/logout` revokes the session.
- **Rate limiting:** there is only one global limit, `RedisOtpRateLimitHook` (`auth/providers.py`). It counts code *sends* per minute, it is off when `auth_otp_provider_rate_limit_per_minute = 0` (the default, `config.py`), and it is wired in `main.py`. **No per-IP limit exists today.**
- **Errors:** `ApplicationError(code, message, status)` is rendered as a problem response (`api/errors.py`). Clients branch on `code` only (CLAUDE.md §4).
- **Users table:** `models/user.py` has no password column. `AccountStatus` is one of `active`, `verification_pending`, `restricted`, `suspended`, `banned`, `deleted`.
- **Account deletion** (`account/deletion.py`) deletes sessions and OTP challenges, then de-identifies the user (`phone_number = deleted-…`).
- **Dependencies** (`apps/api/pyproject.toml`): no `argon2`, `bcrypt` or `passlib`. Python's stdlib `hashlib.scrypt` is available.
- **Migrations:** 17 so far, the latest is `apps/api/migrations/versions/20261023_0017_booking_expired.py`.
- **Logging** (`logging.py`): structlog writes JSON and has no redaction processor. That is safe today only because no handler logs request bodies.
- **Web:** `apps/web/src/auth/AuthContext.tsx` calls `/auth/otp/request` and `/auth/otp/verify`. The page is `apps/web/src/pages/Login.tsx` and its texts are the `login.*` keys in `apps/web/src/i18n/uz.ts`. Settings has the sections language, look, account, safety and about (`pages/Settings.tsx`).
- **TZ.md** says: §3 "telefon orqali ro‘yxatdan o‘tadi; OTP orqali tasdiqlanadi", and §42 "MVP: Phone number → OTP. Keyinchalik: Google, Apple".

## 1. Proposed TZ.md amendment (owner approves; TZ.md is NOT edited by this PR)

> **§42 Authentication (tahrir, 2026-xx-xx, egasi tasdiqladi)**
> MVP: Phone number → OTP (ro‘yxatdan o‘tish va har qanday kirish uchun).
> Qo‘shimcha: telefon raqami tasdiqlangan foydalanuvchi ixtiyoriy ravishda **parol** o‘rnatishi mumkin; keyin u **telefon + parol** bilan kod kutmasdan kiradi. Kod bilan kirish har doim saqlanadi.
> Parolni unutgan foydalanuvchi uni telefoniga yuborilgan kod orqali tiklaydi; tiklash boshqa barcha seanslarni yopadi *(taklif, Q5)*.
> Parollar faqat bir tomonlama xesh ko‘rinishida saqlanadi; ochiq matnda hech qayerda (DB, log, javob) bo‘lmaydi.
> Keyinchalik: Google, Apple.

§3 needs one bullet added: "- xohlasa parol o‘rnatadi va telefon + parol bilan kiradi;".

## 2. Flows

1. **Sign-up.** Unchanged: phone → code → session. A phone number is proven only by a code, so sign-up always needs a code. Afterwards Login (and Settings) offer "Parol örnatiş" as an optional step. Whether this step is skippable is owner question Q1.
2. **Password login.** Phone + password → session, the same token pair as today. No code is sent, so it costs nothing.
3. **Change password** (Settings → Account). Needs the current password and a new one. After the change, every *other* session is revoked and the current one stays (*taklif*, Q5).
4. **Set the first password** (no password yet). Needs a signed-in session. **taklif:** the session must have been created by a code login no more than 10 minutes ago. Otherwise the user requests a new code first. This stops a stolen long-lived session from planting a password.
5. **Reset (forgot password).** `/auth/otp/request` (existing) → code + new password → the password is replaced, **all** sessions are revoked (*taklif*, Q5) and a fresh session is returned. It uses the same per-phone limits as code login.
6. **New-device rule.** A code is required on the first password login from an unknown device. This is **owner question Q3**, and the plan builds nothing for it until he answers. **taklif:** no, not in this version.

## 3. API (all under `/auth`; sessions unchanged)

| Method + path | Auth | Request | Success | Errors (`code`, status) |
|---|---|---|---|---|
| `POST /auth/password/login` | none | `{phone_number, password}` | 200 `TokenResponse` | `invalid_credentials` 401 · `password_login_blocked` 429 · `account_unavailable` 403 |
| `PUT /auth/password` | bearer | `{current_password?, new_password}` | 204 | `invalid_credentials` 401 (wrong current) · `reauth_required` 403 (first set, session not fresh) · `weak_password` 422 · `password_login_blocked` 429 |
| `POST /auth/password/reset` | none | `{phone_number, code, new_password}` | 200 `TokenResponse` | existing `invalid_otp`/`otp_expired` 401, `otp_temporarily_blocked` 429, `account_unavailable` 403 · `weak_password` 422 |
| `GET /auth/me` (existing) | bearer | — | adds `has_password: bool` | — |

- **No user enumeration.** An unknown phone, an account with no password and a wrong password all return the same `invalid_credentials` 401 with the same body. The server does equal hashing work in all three cases (it verifies against a fixed dummy hash). The UI then offers "Kod bilan kirish".
- **Login checks** `account_status` exactly as `verify_otp` does: `suspended`/`banned` → 403 `account_unavailable`, and `deleted` never matches because its phone is rewritten.
- **Reset** reuses the code check from `verify_otp` (attempt counter, lockout, delete-on-use). The implementation should extract a shared `_consume_otp()` and not duplicate that logic.
- **OpenAPI:** three new operations, new schemas `PasswordLogin`, `PasswordChange`, `PasswordReset`, and `UserResponse.has_password`. Regenerate `docs/openapi-v1.json` (`python export_openapi.py`, the CI `--check`) and `apps/web/src/api/schema.d.ts` (`npm run gen:api`).
- **Responses never contain** the password or its hash.

## 4. Data and hashing

- **Migration** `0018_user_password`, additive only:
  - `users.password_hash` (String(255), nullable) and `users.password_changed_at` (timestamptz, nullable).
  - A new table `password_login_guards(phone_number PK String(16), failed_attempts int, blocked_until timestamptz, updated_at)`, the same shape as `otp_challenges`.
  - Nothing is dropped or rewritten. Downgrade drops only these.
- **Session freshness** (flow 4): `auth_sessions.created_at` already exists (`TimestampMixin`). Add `auth_sessions.via` (`'otp'|'password'|'refresh'`, nullable) so that "fresh code login" can be checked.
- **Hashing: `hashlib.scrypt` from the Python stdlib.** It adds no dependency and OWASP lists it as acceptable.
  - Parameters: N=2^17, r=8, p=1, 16-byte random salt, 32-byte key.
  - Stored as one self-describing string: `scrypt$17$8$1$<salt b64>$<hash b64>`. This keeps a later move to argon2id possible: rehash on the next successful login.
  - Compare with `hmac.compare_digest`. Run hashing in a thread (`asyncio.to_thread`) and pass `maxmem` of at least 2^27 + a margin (the stdlib default refuses N=2^17), so the event loop is not blocked (about 0.1 s and 128 MiB per hash; size the host for this).
  - Alternative: `argon2-cffi` (argon2id, OWASP's first choice) would add one compiled dependency. Recommended only if the owner/CEO prefers it to zero new dependencies.
- **No plaintext anywhere.**
  - Passwords travel only in request bodies over HTTPS.
  - Pydantic fields are `SecretStr`, so a `repr` or a validation error never echoes them. Add a test that a 422 response does not contain the submitted password.
  - Add a structlog processor that drops the keys `password`, `current_password`, `new_password` and `code` as a guard.
- **Account deletion** (`account/deletion.py`) also sets `password_hash = NULL`, `password_changed_at = NULL` and deletes the `password_login_guards` row for the phone.

## 5. Abuse limits (reuse the existing patterns)

- **Per phone (DB, like `OtpChallenge`).** Each failed login or wrong current password adds to `failed_attempts`. At the threshold, set `blocked_until` and return `password_login_blocked` 429 with the same body whether or not the account exists. Success resets the counter. Under PostgreSQL, take the same per-phone advisory lock as `issue_otp`. **taklif:** 5 failures, then a 15 min block; doubling on repeat is optional.
- **Per IP (Redis).** A new `RedisPasswordRateLimitHook`, a copy of `RedisOtpRateLimitHook` with the key `yondo:pwd:ip:<ip>:<minute>`. Without Redis or with a limit of 0 it is a no-op, as today. **taklif:** 20 attempts/min per IP. The client IP comes from the proxy header only behind a trusted proxy; that is deploy config, done with the server work at the end (§7 "Serverni oxirida").
- **Code sends** for reset stay under the existing limits: the cooldown, `auth_otp_provider_rate_limit_per_minute`, and Telegram Gateway cost per code.
- **Minimum password rule.** `weak_password` is the only complexity error. **taklif:** at least 8 characters, at most 128, not equal to the phone digits, no other composition rules (NIST 800-63B). Owner question Q2.

## 6. Web UI (`apps/web`)

- **Login** (`pages/Login.tsx`):
  - Two modes in a `role="tablist"`: "Kod bilan" (default, today's flow) and "Parol bilan".
  - The password mode has the phone field, a password field (`type=password`, `autocomplete="current-password"`), a show/hide toggle (`aria-pressed`, labelled), the existing consent checkbox, "Kiriş", and a "Parolni unutdingizmi?" link to the reset step.
  - The reset step is phone → code (the existing code UI) → new password (`autocomplete="new-password"`).
  - Errors render from `code`: `invalid_credentials` shows one generic text plus a "Kod bilan kiriş" action; `password_login_blocked` shows the wait text.
- **After a code sign-up,** a dismissible card "Parol örnatiş" is shown (Q1 decides whether it can be dismissed).
- **Settings → Account** (`pages/Settings.tsx`): a "Parol" row. If `has_password` is false, it offers "Parol örnatiş"; if true, it offers "Parolni özgartiriş" with current + new fields.
- **a11y:** visible labels, errors tied with `aria-describedby` and `role="alert"`, focus moves to the first field on mode switch, 44 px targets (as `.lang-opt`), no reliance on colour. **Brand unchanged:** ink/paper/carrot, glass, motion with reduced-motion respected.
- **New i18n keys** go in `uz.ts` (2026 alphabet; the 1995 form is derived), `ru.ts` and `en.ts`. Drafts:

| key | uz (2026) | ru | en |
|---|---|---|---|
| `login.mode.code` | Kod bilan | По коду | With a code |
| `login.mode.password` | Parol bilan | По паролю | With a password |
| `login.password` | Parol | Пароль | Password |
| `login.password.show` / `.hide` | Parolni körsatiş / Parolni yaşiriş | Показать пароль / Скрыть пароль | Show password / Hide password |
| `login.password.forgot` | Parolni unutdingizmi? | Забыли пароль? | Forgot your password? |
| `login.password.invalid` | Telefon raqami yoki parol notöğri. | Неверный номер телефона или пароль. | Wrong phone number or password. |
| `login.password.blocked` | Juda köp urinişlar. Birozdan keyin qayta urinib köring. | Слишком много попыток. Повторите позже. | Too many attempts. Please try again later. |
| `login.password.useCode` | Kod bilan kiriş | Войти по коду | Sign in with a code |
| `password.new` | Yangi parol | Новый пароль | New password |
| `password.current` | Joriy parol | Текущий пароль | Current password |
| `password.rule` | Kamida {n} ta belgi | Не менее {n} символов | At least {n} characters |
| `password.set` | Parol örnatiş | Установить пароль | Set a password |
| `password.change` | Parolni özgartiriş | Изменить пароль | Change password |
| `password.saved` | Parol saqlandi. Boşqa qurilmalardagi seanslar yopildi. | Пароль сохранён. Сеансы на других устройствах завершены. | Password saved. Sessions on other devices were signed out. |
| `password.reauth` | Avval kod bilan qayta kiring. | Сначала войдите заново по коду. | Sign in again with a code first. |
| `password.weak` | Parol juda qisqa yoki oddiy. | Пароль слишком короткий или простой. | The password is too short or too simple. |

(The uz drafts follow the 2026 spelling rules in CLAUDE.md §7: ş ç ö ğ. A native-speaker check is part of the review.)

## 7. Tests and rollout

- **Backend** (`apps/api/tests/test_auth_password.py`):
  - hash format and verify;
  - login success, wrong password, unknown phone and no-password case give identical responses;
  - per-phone lockout and reset of the counter;
  - suspended/banned → 403;
  - change revokes other sessions only;
  - first set needs a fresh code session;
  - reset consumes the code, revokes all sessions and respects `otp_temporarily_blocked`;
  - deletion clears the hash;
  - a 422 body does not echo the password;
  - on PostgreSQL, concurrent wrong passwords count exactly;
  - the OpenAPI `--check` passes.
- **Web vitest:** Login mode switch, error mapping by `code`, show/hide toggle, Settings row by `has_password`.
- **e2e** (`apps/web/e2e/run.mjs`): code sign-up → set password → logout → password login → wrong password message → reset via the on-screen code; axe on the new screens in all 5 themes.
- **Rollout:**
  1. Backend and migration ship first: additive, and the old clients keep working.
  2. Then the web UI.
  3. The demo harness keeps the on-screen code (`development_otp`, only in `development`/`test`, `router.py`). The reset flow uses it too.
  4. No feature flag is needed: a user without a password sees no change unless they opt in.

## 8. Owner questions (only the owner decides; each has a *taklif*)

- **Q1** Is a password mandatory after sign-up, or optional? *taklif:* optional, with a skippable card after the first code login.
- **Q2** Password rule? *taklif:* 8–128 characters, not equal to the phone digits, no composition rules.
- **Q3** A code on a new device/browser? *taklif:* not now; revisit if account-takeover reports appear.
- **Q4** Lockout values? *taklif:* 5 wrong passwords → 15 min per phone, and 20 attempts/min per IP.
- **Q5** Does changing or resetting the password sign out other devices? *taklif:* yes for both: other sessions on change, all sessions on reset.
- **Q6** Approve the TZ.md amendment text in §1 (wording and date).
- **Q7** Hashing: stdlib scrypt (no new dependency) or argon2id (`argon2-cffi`, one new dependency)? *taklif:* scrypt now, with the stored format allowing a later switch.
