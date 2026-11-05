# Staging readiness (what exists, what is missing)
**Result: no staging environment, URL or test accounts are documented in the repository.** Searched README, TZ, ROADMAP, `docs/`, `.env.example`, `compose.yaml`, `.github/workflows/ci.yml`: the only environments mentioned are local development (compose), CI (PostgreSQL service) and a rule that offline CLICK test mode is forbidden outside local environments. **BLOCKED: staging integration was not run.** Nothing here was tested against any remote backend.

## Required configuration (names only; never commit values)
Prefix `YONDO_`. From `apps/api/src/yondo_api/config.py` and `.env.example`.
| Variable | Needed for staging | Note |
|---|---|---|
| `YONDO_ENVIRONMENT` | yes (`staging`) | gates dev-only behaviour below |
| `YONDO_DATABASE_URL` | yes | PostgreSQL (`postgresql+psycopg://…`); **secret** |
| `YONDO_AUTH_OTP_PEPPER` | yes | **secret**; outside development/test it must be a strong non-default value or startup fails |
| `YONDO_PLATFORM_FEE_BPS` | only to enable payments | unset ⇒ payments return 503 (intended until the owner approves a policy) |
| storage, notification and payment provider settings | see `config.py` | no concrete provider exists in the repo (protocols only) |
| CORS | **not present** | no CORS/allowed-origin setting was found in `config.py` or `main.py`; a browser client on a different origin would need CORS added by the backend owner |
Endpoints: base path `/api/v1`; liveness `GET /health`; readiness `GET /api/v1/health/ready`; contract `docs/openapi-v1.json` (checked in CI).

## Consequences for test accounts
- OTP: the dev code (`development_otp`) is returned **only** when `environment` is `development` or `test`. On staging a real OTP delivery provider is required; none exists in the repo (`integrations/` has protocols only). So safe test logins on staging need either a sandbox SMS provider or a separately approved test-login mechanism.
- Offline CLICK/gift test orders (`/gifts/test-orders`, `/gifts/click-test/*`) are disabled outside local environments (`click_test_disabled`), so gift test flows cannot be exercised on staging.
- Payments cannot be exercised until a provider and `YONDO_PLATFORM_FEE_BPS` are approved; no real charge or refund must be attempted.

## Missing values to obtain (no secrets in chat or Git)
1. Staging API base URL (and whether the sandbox/egress allow-list can reach it).
2. How test users sign in (sandbox SMS provider or approved test-login path) and the test phone numbers.
3. Staging database/Redis provisioning owner; migration policy (`alembic upgrade head`, 14 migrations verified on a clean PostgreSQL 16).
4. Payment sandbox provider + approved fee policy (platform fee; delivery fee schema) — business decision.
5. Frontend origin and a CORS decision (the backend currently has no CORS configuration).
Safe next step once 1–2 exist: run `tests/run.js`-style contract checks against the real base URL read-only (discovery, health), then extend to authenticated flows with test accounts. Never run destructive or payment/refund operations against production.
