# Configuration and integrations

> **Qisqacha (egasi uchun):** Bu sahifada serverga qo‘yiladigan barcha sozlamalar (`YONDO_*`) jadvali va faqat siz bajara oladigan ishlar ro‘yxati bor. Holatni tekshirish: `cd apps/api && python -m yondo_api.doctor`. Buyruq har bir integratsiya uchun "ok / missing / invalid" deb yozadi; maxfiy qiymatlarni (token, kalit, karta raqami) hech qachon chiqarmaydi va hech qayerga ulanmaydi. Kalitlarni faqat server sozlamalariga (Render → Environment yoki serverdagi `.env`) qo‘ying, hech qachon chatga yoki repozitoriyga emas.

## Check the configuration

```
cd apps/api
python -m yondo_api.doctor              # exit 0 = everything required here is OK, 1 = something required is missing/invalid
python -m yondo_api.doctor --strict     # also fails on missing optional integrations
python -m yondo_api.doctor --env-file /path/to/.env
```

- **What it checks:** format only. It makes **no network calls**, so a Telegram balance, S3 bucket access or TezCheck token validity are not checked.
- **What it prints:**
  - secrets as `set (N chars)` or `missing`;
  - card numbers as the last 4 digits, with holder names hidden;
  - URLs as scheme and host only.
- **Which values it sees:** the same sources as the API, i.e. `YONDO_*` environment variables, which override the `.env` file in the current directory.
- **What is required** depends on `YONDO_ENVIRONMENT`. In `development`/`test` the local defaults are enough; in `staging`/`production` the rows marked "yes" below are needed.
- **API start-up errors:** the doctor also runs the API's own settings validation and lists every reason the API would refuse to start.

## Safe fallbacks (verified in code)

| Integration | When it is missing | Where |
|---|---|---|
| Telegram Gateway | Production: login answers 503 "not configured". Development/test: the code is shown on screen. | `main.py::select_otp_provider` |
| S3 storage | Photo and ID uploads answer 503. | `integrations/s3.py::build_object_storage`, `companions/dependencies.py::object_storage` |
| Payment provider / TezCheck | Payments answer 503. No money moves. | `main.py::select_payment_provider` |
| Platform fee | Payment creation answers 503 `payment_configuration_unavailable`. | `payments/router.py` |
| Manual payments | The API refuses to start with `YONDO_PAYMENT_PROVIDER=manual` but no cards or no https `YONDO_PUBLIC_WEB_URL`, so it fails fast instead of failing silently. | `config.py::validate_payment_provider` |
| Database, Redis, OTP pepper | No fallback, by design: required in production. The API refuses the default pepper outside development. | `config.py` |

**Finding (platform fee):** the owner decided on a 5% fee **deducted from the companion's side** (`docs/product-decisions.md`). The code today **adds** the fee to the customer's total (`payments/router.py`, `platform_fee()`). Leave `YONDO_PLATFORM_FEE_BPS` unset until the deduction is built. The doctor warns when it is set.

## Every variable

Unless noted otherwise, the owner sets each value: in Render → Environment for the demo, or in the server's `.env` for `infra/deploy/digitalocean`. Placeholders only, never real values. "Prod?" = required in staging/production.

| Name | Purpose | Prod? | Example placeholder | Where to get it |
|---|---|---|---|---|
| `YONDO_ENVIRONMENT` | `development` / `test` / `staging` / `production` | yes | `production` | Set by `docker-compose.yml` |
| `YONDO_DATABASE_URL` | PostgreSQL connection (contains a password) | yes | `postgresql+psycopg://yondo:<password>@<host>:5432/yondo` | Set by docker-compose from `POSTGRES_PASSWORD`; or the hosted DB console |
| `POSTGRES_PASSWORD` | Database password (compose only) | yes | output of `openssl rand -hex 24` | Owner generates |
| `YONDO_REDIS_URL` | Redis (OTP rate limit, chat events) | yes | `redis://redis:6379/0` | Set by docker-compose |
| `YONDO_AUTH_OTP_PEPPER` | Secret key for login-code hashes (32+ chars) | yes | output of `openssl rand -hex 24` | Owner generates |
| `DOMAIN` | Site domain for Caddy/HTTPS (compose only) | yes for real users | `yondo.example` | Domain registrar (owner buys) |
| `YONDO_TELEGRAM_GATEWAY_TOKEN` | Sends login codes via Telegram | yes for real users | `<token>` | gateway.telegram.org account (owner) |
| `YONDO_TELEGRAM_GATEWAY_BASE_URL` | Gateway API origin (https) | no | `https://gatewayapi.telegram.org` | Default |
| `YONDO_TELEGRAM_GATEWAY_TIMEOUT_SECONDS` | Request timeout | no | `10` | Default |
| `YONDO_AUTH_OTP_PROVIDER_RATE_LIMIT_PER_MINUTE` | Global cap on code sends per minute (0 = off) | recommended | `30` | Owner/CEO decides |
| `YONDO_AUTH_ACCESS_TOKEN_LIFETIME_SECONDS` / `..._REFRESH_...` | Session lifetimes | no | `900` / `2592000` | Defaults |
| `YONDO_STORAGE_BACKEND` | `disabled` or `s3` | for photos/ID | `s3` | — |
| `YONDO_STORAGE_ENDPOINT` | S3 API origin (https in prod) | with s3 | `https://<region>.digitaloceanspaces.com` | Storage provider console |
| `YONDO_STORAGE_PUBLIC_ENDPOINT` | Origin the apps download from (defaults to endpoint) | no | `https://<s3-endpoint>` | Storage provider |
| `YONDO_STORAGE_BUCKET` | Private bucket name | with s3 | `yondo-photos` | Storage provider (owner creates) |
| `YONDO_STORAGE_REGION` | Bucket region | no | `us-east-1` | Storage provider |
| `YONDO_STORAGE_ACCESS_KEY` / `YONDO_STORAGE_SECRET_KEY` | S3 keys | with s3 | `<access key>` / `<secret key>` | Storage provider (owner) |
| `YONDO_STORAGE_PATH_STYLE` | `true` = endpoint/bucket/key (MinIO), `false` = bucket.endpoint/key | no | `false` | Provider docs |
| `YONDO_PAYMENT_PROVIDER` | `auto` (TezCheck if token, else 503), `manual`, `tezcheck` | no | `manual` | Owner decision |
| `YONDO_MANUAL_PAYMENT_CARDS` | JSON list of cards shown to the payer | with manual | `[{"label":"Uzcard","number":"<16 digits>","holder":"<Name S.>"}]` | Owner's own cards; set only in the host env (the repo is public) |
| `YONDO_PUBLIC_WEB_URL` | https origin of the web app (manual pay page) | with manual | `https://yondo.example` | Owner's domain |
| `YONDO_PLATFORM_FEE_BPS` | Fee in basis points (500 = 5%) | no; **leave unset** (finding above) | `500` | Owner decision |
| `YONDO_TEZCHECK_TOKEN`, `_CASH_DESK_CODE`, `_WEBHOOK_SECRET` (16+), `_API_URL`, `_RETURN_URL` | TezCheck aggregator. **Not used in the beta** (the doctor shows "disabled (beta)") | no | `<token>` … | tezcheck.uz cabinet (owner) |
| `YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS` | Accept TezCheck test payments; refused in production | no | `false` | — |
| `YONDO_CLICK_TEST_ENABLED`, `_SERVICE_ID`, `_SECRET` | Offline CLICK emulator, local only | no | `false` | — |
| `YONDO_FCM_PROJECT_ID` | Reserved for push; not used by the code yet | no | — | — |
| `YONDO_LOG_LEVEL`, `YONDO_DEBUG` | Logging | no | `INFO`, `false` | Defaults |
| `YONDO_COMPANION_*`, `YONDO_IDENTITY_*` | Technical limits (photo size/count, ID submissions, retention days) | no | defaults | Defaults; retention days is a proposal, not an owner decision |
| `YONDO_DEMO_HOST`, `YONDO_DEMO_PUBLIC_URL`, `YONDO_DEMO_DATABASE_URL`, `YONDO_DEMO_ADMIN_PHONE`, `YONDO_WEB_DIST`, `YONDO_API_DIR` | Public demo harness only (`infra/deploy/demo/demo_app.py`) | demo only | see `infra/deploy/README.md` | Render (owner) |

**CORS:** there is no CORS setting. The API sends no CORS headers, and the web app reaches it same-origin through `/api` (Caddy `reverse_proxy` in production, the Vite proxy in development, `apps/web/vite.config.ts`).

## Owner-only tasks

These need the owner's accounts, money or decisions. Details in Uzbek: `docs/owner-todo.md`.

1. **Buy a domain**, point its DNS A record to the server, and put it in `DOMAIN` and `YONDO_PUBLIC_WEB_URL`. TezCheck and the HTTPS certificate need it.
2. **S3 bucket and keys** (e.g. DigitalOcean Spaces). Create a private bucket and keys, then set `YONDO_STORAGE_*`. Without them, photo and ID uploads answer 503.
3. **Telegram Gateway token and balance.** Create the account at gateway.telegram.org, top up the balance, and set `YONDO_TELEGRAM_GATEWAY_TOKEN` in the host env only. Each code costs money; the doctor cannot see the balance.
4. **Render env for manual payments.** Set `YONDO_PAYMENT_PROVIDER=manual`, `YONDO_MANUAL_PAYMENT_CARDS` and `YONDO_PUBLIC_WEB_URL` in Render → Environment, then run the doctor. This turns on real transfers, so it needs the owner's separate permission (`docs/product-decisions.md`).
5. **Bank and accountant.** Clarify receiving business payments to personal cards: bank limits, blocking risk, tax.
6. **Expo Go on your phone,** to try the mobile app (`apps/mobile/README.md`). The API must be reachable from the phone.
7. **Agent Creator permission rule.** The Agent Creator ("ona") needs an owner permission rule before it can create worker sessions itself (CLAUDE.md, team roles). Until then the lead session creates workers.
