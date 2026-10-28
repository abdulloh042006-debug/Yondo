# Payments through TezCheck (tezcheck.uz)

Status: **adapter implemented and unit/integration-tested with a mocked HTTP transport (S32); never run against the real TezCheck API** — that needs the owner's domain, cash desk and keys. Official reference: <https://tezcheck.uz/api-docs> (read 2026-10-28). Everything marked *not stated* below was missing from that page; ask TezCheck support (<https://t.me/call_menejer>) before relying on it.

## Why TezCheck
The owner chose it (2026-10-28) as the payment gateway: one merchant API in front of Click, Payme, Uzum and Uzcard/Humo, so separate Click/Payme merchant contracts are not needed for the beta. Funds flow model reported by the API: `direct_to_merchant` (provider funds go to the merchant's bank). Fees: *not stated* on the docs page.

## API facts used by the adapter
| Topic | Fact |
|---|---|
| Base URL | `https://api.tezcheck.uz/api/merchant/v1` (JSON, ISO 8601) |
| Auth | `Authorization: Bearer <token>` (secret, server-side only) + `X-Cash-Desk-Code: cdk_…` (not secret; optional for desk-bound keys) |
| Money | integer tiyin (`amount_minor`), **UZS only**, no `currency` field in requests; default minimum `100000` (1 000.00 UZS); maximum *not stated* |
| Create | `POST /bills` — `amount_minor`, `title` (2–191), `description` (≤2000), `external_reference` (≤128), `return_url` (must match the desk allow-list), `allowed_provider_codes` → `data.bill.id`, one-time `data.payment_url` (never retrievable again) |
| Idempotency | header `Idempotency-Key` (1–128 ASCII, 24 h, per key+desk); replay returns the stored response (`Idempotent-Replayed: true`); `external_reference` is **not** a dedup key |
| Status | `POST /bills/{bill}` → branch on `paid`, not `state`; ship only when `paid` **and** `livemode` are true |
| Cancel / reissue | `POST /bills/{bill}/cancel` (unpaid only, permanent), `POST /bills/{bill}/reissue` (new URL, old one invalidated) |
| Webhook headers | `X-Checkout-Event`, `X-Checkout-Event-Id`, `X-Checkout-Delivery` (constant over retries), `X-Checkout-Timestamp`, `X-Checkout-Signature: v1=<hex>[,v1=<hex>]` |
| Webhook signature | `HMAC-SHA256(secret, "{timestamp}.{delivery_id}.{raw body}")`, constant-time compare against every `v1=` value, timestamp window 300 s, deduplicate on the **body `id`** |
| Webhook payload | `id`, `type` (`payment.<state>`), `data.{payment_id,state,bill_id,external_reference,amount_minor,fee_minor,net_minor,environment,…}`; use `data.environment`, not top-level `mode` |
| Retries | up to 8 attempts (0, 5, 5, 8, 16, 32, 64, 128 s ±25 %); retried: 5xx, timeouts, 429; not retried: other 4xx, redirects; timeouts 5 s connect / 15 s total; then `dead_lettered`, manual resend in the cabinet |
| Test mode | no separate sandbox; the cabinet's **test provider** makes payments with `environment:"test"`, `livemode:false` (no real money, cancelled after a day) |
| Limits | 300 requests/min; optional signed requests and IP allow-list per desk |
| Not stated | refund initiation endpoint, return-URL query parameters, default bill expiry, test/live key format, maximum amount, commissions, individual vs legal-entity onboarding, domain verification rules |

## How the adapter maps to Yondo (`apps/api/src/yondo_api/payments/tezcheck.py`)
- `PaymentProvider.create_checkout` → `POST /bills`; `provider_reference` = **bill id** (the webhook carries it as `data.bill_id`; the router finds the payment by it); `Idempotency-Key` and `external_reference` = our payment id, so a retry after a timeout returns the same link.
- `PaymentProvider.verify_event` → signature + window check, then `payment.succeeded` → `succeeded`, `payment.failed` → `failed`; every other type is refused (HTTP 401 from our route, which TezCheck does not retry). **Configure the webhook in the cabinet to send only these two event types.** Refund/dispute events are not handled (owner policy undefined).
- Test-environment events are refused unless `YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS=true`; settings reject that flag in `production`.
- The router's rules stay: pay only when the booking is `accepted`, fee from `YONDO_PLATFORM_FEE_BPS` (unset ⇒ 503 "sozlanmagan" — **the fee is the owner's decision; for a test run set a labelled test value yourself**), booking confirmed only by a verified webhook, duplicate events harmless, late success after cancellation flagged `refund_required` (no automatic refund).
- A failed attempt does not lock the booking out: the same bill's page may be retried by the customer and a later `payment.succeeded` still confirms it.

## Settings (environment variables, never in git)
`YONDO_TEZCHECK_TOKEN` (enables the adapter), `YONDO_TEZCHECK_CASH_DESK_CODE`, `YONDO_TEZCHECK_WEBHOOK_SECRET` (16+ chars, shown once when the webhook is created), optional `YONDO_TEZCHECK_RETURN_URL`, `YONDO_TEZCHECK_API_URL`, `YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS`. A token without a webhook secret refuses to start (unsigned events would otherwise be accepted). In the public demo image the real adapter replaces the DEMO payment page as soon as the token is set.

## Owner checklist
1. Buy the domain (the cash-desk form asks for the website address and confirms it is yours). Owner decision 2026-10-28: a real domain, bought later; no subdomain workaround. Until then the DEMO payment page stays.
2. In tezcheck.uz: *Kassa ochish* → channel **Veb-sayt**, address = the domain, support phone/Telegram; webhook = **Bor**, URL `https://<domain>/api/v1/payments/webhook`, events `payment.succeeded` + `payment.failed`; save the webhook secret.
3. Create an API key for the desk; put token, cash-desk code and webhook secret into Render → Environment (`render.yaml` declares the three names) plus `YONDO_PLATFORM_FEE_BPS` and, for test mode, `YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS=true`. Optionally also `YONDO_TEZCHECK_RETURN_URL` (must match the desk's allow-list).
4. Make a test payment with TezCheck's test provider; confirm the booking becomes "Tasdiqlangan" and the cabinet shows the webhook as delivered.
5. Ask TezCheck: commission, refund API, individual vs entity onboarding, return-URL parameters, bill expiry, test/live switch for the key.

## Follow-ups (not done)
- Compare `data.amount_minor` of the webhook with the stored payment amount (the router does not check amounts today; `PaymentEvent` has no amount field).
- Refund/cancel flow and `POST /bills/{bill}/cancel` when a booking is cancelled before payment (the unpaid bill stays payable until `available_until`).
- Optional request signing (`X-TezCheck-Signature`) and the desk IP allow-list.
- Run the whole flow against the real test provider once keys exist.
