# Deployment checklist (staging / production)

`compose.yaml` is for local development only. A real deployment needs the items below.
Items marked **[owner input]** require credentials or decisions from the project owner.

## Components

| Component | Image / build | Command |
| --- | --- | --- |
| API | `apps/api/Dockerfile` | default (`uvicorn … --no-access-log --proxy-headers`) |
| Migrations | same image | `alembic upgrade head` (run once per release, before the API) |
| Worker | same image | `python -m yondo_api.cli worker` (one or more replicas) |
| Admin/vendor panel | `apps/admin/Dockerfile` | nginx serving static files, proxying `/api` |
| Mobile app | Expo EAS build | `eas build` with `EXPO_PUBLIC_API_URL` set to the public API |

Managed services: PostgreSQL 16+ (with permission to create the `btree_gist` extension or the
extension preinstalled), Redis 7, S3-compatible private bucket, HTTPS reverse proxy that
supports WebSockets (`/api/v1/realtime/ws`).

## Required configuration

- `YONDO_ENVIRONMENT=production` (or `staging`) — enables fail-closed checks.
- `YONDO_DATABASE_URL`, `YONDO_REDIS_URL`.
- `YONDO_AUTH_OTP_PEPPER` — random, ≥ 32 characters (startup fails otherwise).
- Storage: `YONDO_STORAGE_BACKEND=s3`, endpoint, bucket, keys, region,
  `YONDO_STORAGE_PUBLIC_ENDPOINT` (origin clients use for presigned URLs). **[owner input]**
- `YONDO_CORS_ALLOW_ORIGINS` only if the panel is served from another origin.
- Business policy values from `docs/business-policies.md`. **[owner input]**

## Integrations still to connect **[owner input]**

1. **SMS OTP provider.** Without one, production OTP requests return
   `503 otp_delivery_unavailable` (fail-closed). Implement `OtpDeliveryProvider`
   (`yondo_api/auth/providers.py`) for the chosen provider (e.g. Eskiz, Play Mobile) and pass it
   to `create_application`.
2. **Payment provider.** `YONDO_PAYMENT_PROVIDER` defaults to `disabled` outside local
   environments; checkout then returns `503 payment_unavailable`. Implement
   `PaymentProvider` (`yondo_api/payments/providers.py`: checkout, refund, signed webhook
   parsing) for the chosen provider (Payme/Click/Uzum…), register it in `wiring.py`, and set
   the provider's merchant credentials as secrets. Webhook URL:
   `POST /api/v1/payments/webhooks/{provider}`.
3. **Payouts.** Companion/vendor payouts are recorded and marked paid manually in the panel
   (Finance → Payouts) until a payout API is chosen.
4. **Push.** `YONDO_PUSH_PROVIDER=fcm`, `YONDO_FCM_PROJECT_ID`,
   `YONDO_FCM_SERVICE_ACCOUNT_FILE` (mounted secret). The mobile build needs
   `google-services.json` (Android) and APNs configuration (iOS).
5. **Maps.** The app stores approximate coordinates only; a map SDK/key is optional.

## Release steps

1. Back up the database.
2. Run migrations with the new image (`alembic upgrade head`).
3. Deploy API and worker; verify `GET /api/v1/health/ready` returns `ok`.
4. Deploy the panel; sign in; `grant-admin` the first administrator if needed.
5. Smoke test: OTP sign-in, companion approval and verification, booking, payment in the
   provider's test mode, chat, meeting, review, gift order, refund.

## Operations

- Logs are structured JSON with request ids; access logs are disabled so query strings
  (e.g. WebSocket credentials) are never written.
- Run at least one worker; every job is idempotent and safe to run on several replicas.
- Monitor: readiness endpoint, worker cycle logs (`worker_cycle`), pending refunds
  (Finance → Refunds), open SOS alerts (SOS page).
