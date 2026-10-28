# Telegram Gateway API — facts for the OTP delivery adapter

Researched 2026-10-28 (research only; nothing was called against the live API; no secrets here).

**Source access.** This sandbox blocks `core.telegram.org`, `gateway.telegram.org`, `gatewayapi.telegram.org`, `telegram.org` (proxy 403 / ENOTFOUND). **No Telegram page could be read directly, so nothing below is tagged `[official]`.** Tags used:
- `[tg-search]` = excerpt/summary of a Telegram page (`core.telegram.org/gateway`, `/gateway/api`, `/gateway/verification-tutorial`, `telegram.org/tos/gateway`, Telegram blog) returned by the search tool. Near-official but second-hand.
- `[sdk]` = source/docs of third-party clients downloaded from PyPI/npm/pkg.go.dev/JSR (`tgateway`, `PyTGGateway`, `telegram-gateway-api`, `telegramgateway-js`, `apifonica/tg-gateway-go`, `@roj/gateway-api`). Their docstrings copy the official text and cite `core.telegram.org/gateway/api#…`.
- `[search]` = other third-party page; `[unverified]` = not established. Re-check against `core.telegram.org/gateway/api` before go-live.

## 1. Transport
- Base `https://gatewayapi.telegram.org/<method>`; HTTPS only; method names case-insensitive; UTF-8. GET and POST both work; parameters as query string, form-urlencoded or JSON body. `[tg-search][sdk]`
- Auth: `Authorization: Bearer <token>` header **or** `access_token` parameter. `[tg-search]` Use the header (keeps the token out of URLs/logs). Older `PyTGGateway` puts it in the JSON body `[sdk]`.
- Response: JSON `{"ok": true, "result": {...}}` or `{"ok": false, "error": "SOME_CODE"}`; docs' only example error is `ACCESS_TOKEN_INVALID`. `revokeVerificationMessage` returns `result: true`. No `description`/`error_code` fields. `[tg-search][sdk]`
- HTTP status on errors (200 vs 4xx): `[unverified]` (one SDK treats >=400 as failure before reading the body, another parses the body regardless). Adapter: parse JSON `ok`/`error` first; also handle non-JSON, 5xx and timeouts as "provider unavailable".

## 2. Methods
**sendVerificationMessage** (charged per delivered message; free to your own number) `[sdk]` unless noted
| param | type | notes |
|---|---|---|
| `phone_number` | string, required | E.164 (`+998…`) |
| `request_id` | string | id from `checkSendAbility`; makes this send free; usable once (reuse → error). Must be the same number |
| `sender_username` | string | verified channel owned by the token's account; not needed |
| `code` | string | **our own code**: digits only, 4–8 chars; if set, `code_length` is ignored |
| `code_length` | int | 4–8, Telegram generates the code. One of `code`/`code_length` is needed (else `CODE_LENGTH_REQUIRED`, presumably) |
| `callback_url` | string | HTTPS only, 0–256 bytes; receives delivery reports |
| `payload` | string | 0–128 bytes, never shown to the user, echoed back in `RequestStatus` and reports (keep it an opaque id, no PII) |
| `ttl` | int | seconds; if not delivered in time the message expires and the **fee is refunded automatically**; not deleted if already read; omitted = no expiry. Range **30–3600** (changelog 2025-02-26 `[tg-search]`, npm README `[sdk]`); older SDKs say 60–86400 / <=86400 → stay inside 30–3600 |

**checkSendAbility**(`phone_number`) → RequestStatus. Optional dry run: can this number receive Telegram messages. Fee applies if sendable (see §6); error → no charge.
**checkVerificationStatus**(`request_id`, `code?`) → RequestStatus. With `code` (4–8) it checks the code (needed only for Telegram-generated codes); Telegram still recommends calling it after the user enters a correct code, even for own codes, for conversion statistics.
**revokeVerificationMessage**(`request_id`) → `true` if the request was received; best effort, a delivered/read message is not removed.

**RequestStatus**: `request_id`, `phone_number`, `request_cost` (number, credits), `remaining_balance` (only when a charge happened), `delivery_status{status: sent|delivered|read|expired|revoked, updated_at}`, `verification_status{status: code_valid|code_invalid|code_max_attempts_exceeded|expired, updated_at, code_entered?}`, `payload` (<=256 bytes), `is_refunded` (bool). Timestamps are Unix seconds. `delivered`/`expired`/`is_refunded` were added 2025-02-26 `[tg-search]`; older SDK enums lack them → do not hard-fail on unknown statuses.

## 3. Error codes (`error` string) `[sdk]`
`ACCESS_TOKEN_INVALID`, `ACCESS_TOKEN_REQUIRED`, `BALANCE_NOT_ENOUGH`, `CALLBACK_URL_INVALID`, `CODE_INVALID`, `CODE_EXPIRED`, `CODE_LENGTH_INVALID`, `CODE_LENGTH_REQUIRED`, `CODE_MAX_ATTEMPTS_EXCEEDED`, `MESSAGE_ALREADY_SENT`, `PAYLOAD_INVALID`, `PHONE_NUMBER_INVALID`, `PHONE_NUMBER_NOT_FOUND`, `PHONE_NUMBER_NOT_AVAILABLE`, `PHONE_NUMBER_MISMATCH`, `REQUEST_ID_INVALID`, `REQUEST_ID_REQUIRED`, `SENDER_USERNAME_INVALID`, `SENDER_NOT_VERIFIED`, `SENDER_NOT_OWNED`, `TTL_INVALID`, `UNKNOWN_METHOD`, `FLOOD_WAIT_<seconds>`. No source gives a meaning per code `[unverified]`; the union of the SDK lists is shown, the official page lists none `[tg-search]`. Branch on the exact string, treat unknown strings as generic failure.

## 4. Own code vs Telegram code
- **We can pass our own code** (`code`, digits only, 4–8) `[sdk, copied official docstring]`. Telegram then only *delivers* it; our backend keeps generating, hashing and verifying (no call to Telegram needed for correctness). Optional: `checkVerificationStatus(request_id, code)` after our own successful check, for Telegram's conversion stats.
- Consequences: code must be numeric 4–8 digits; Telegram sees the plaintext code (§9); Telegram does not track previously used codes (`[sdk]`, Flutter docs) → replay/attempt limits are ours; a retried send with the same code creates a **new** request (possible double charge) unless it reuses a `request_id` from `checkSendAbility`.
- Message wording/branding is Telegram's template; customisation `[unverified]`.

## 5. Delivery-report callbacks
- **Optional**: only if `callback_url` is set on the send. Telegram POSTs the `RequestStatus` JSON when delivery status changes. `[tg-search]` Which transitions fire a report: `[unverified]`.
- Your endpoint must return **HTTP 200**; any other status = failure, same report retried **up to 10 times** with increasing delays (schedule not stated), then considered lost. `[tg-search]`
- Headers: `X-Request-Timestamp` (Unix seconds), `X-Request-Signature` (hex).
- Signature `[tg-search]`, identical in 4 independent SDKs `[sdk]`: `expected = hex( HMAC_SHA256( key = SHA256(api_token) /*raw 32 bytes*/, msg = X-Request-Timestamp + "\n" + raw_post_body ) )`; compare with `X-Request-Signature` (constant time, over the **raw** body before JSON parsing).
- Freshness: docs say to check the timestamp against stale reports but give no number `[tg-search]`; `tgateway` SDK rejects when `|now - ts| > 300 s` `[sdk]`. Use 300 s. Handle duplicates idempotently (retries).
- Not needed for our flow (we only need "sent"); without callbacks the status can be read with `checkVerificationStatus(request_id)`.

## 6. Pricing and balance
- **$0.01 per delivered code** (landing page); "up to 50x cheaper than SMS"; Verification Platform 2.0 "20% more cost-effective" `[tg-search]`. Terms: price can change, "varies by recipient region and use case", shown in the interface; no per-country table found (so +998 price `[unverified]`).
- Pay only for delivered messages; not delivered within `ttl` → automatic refund; **no fee if the number is not linked to a Telegram account** `[tg-search]`. Per-code vs per-*verified*-code: only delivery is billed.
- **Test**: any message to the phone number of the Telegram account you logged in with is free; also stated as "always free when sending codes to your own number" `[tg-search][sdk]`.
- `checkSendAbility`: if sendable, you are charged **in advance** (even if you never send); the one following `sendVerificationMessage` with that `request_id` is free (one fee per request id); on error no charge. `[tg-search][sdk]`
- Credits are prepaid: purchases final and non-refundable, valid 3 years, not withdrawable/transferable, prices exclude taxes. `[tg-search]`
- Top-up: "Add Funds on Fragment" on the Gateway dashboard; payment processing is outsourced to Fragment (Fragment Corp). `[tg-search]` Fragment settles in TON / USDT-on-TON and some USDC/ETH networks; a third party says TON was renamed "Gram" in 2026 `[search]`. **Minimum top-up: `[unverified]`. Visa card straight into Gateway: `[unverified]`;** indirect route = buy TON by card in Telegram Wallet/TON Wallet through a partner (Mercuryo) `[search]`; whether that works for Uzbekistan-issued cards `[unverified]`.

## 7. Availability, Uzbekistan, "no Telegram"
- Sends only to numbers registered on Telegram; the user must have opted in by sharing the number with your service and agreeing to receive messages there. `[tg-search]`
- No country list found. ToS: Gateway "may not be available" to certain individuals, apps or regions because of regulation `[tg-search]`. **+998 support: `[unverified]`** → first real test with several +998 numbers/operators (Telegram user, non-user).
- Number without Telegram: documented as **not charged**. The exact error string/HTTP code is `[unverified]`; candidates in the SDK lists: `PHONE_NUMBER_NOT_FOUND` (most likely), `PHONE_NUMBER_NOT_AVAILABLE`. Adapter: map every `PHONE_NUMBER_*` error to one internal reason "channel unavailable" (→ SMS fallback or "use another method").
- Pre-check via `checkSendAbility` saves nothing (charged if OK, free if error, then the send is free): call `sendVerificationMessage` directly. *(recommendation)*
- Do not tell API clients whether a number is on Telegram (account enumeration): return the same neutral response as for any delivery failure. *(recommendation)*

## 8. Account, limits
- Sign-up `[tg-search]`: open `gateway.telegram.org`, log in with your Telegram phone number, answer "basic information about yourself and your business", fund the account, copy the token (`https://gateway.telegram.org/account/api` `[sdk]`).
- Legal-entity/business requirement: none found; the form asks about "yourself and your business"; ToS says some individuals may be excluded → individual allowed: `[unverified]`.
- Rate limits: no figure found; a `FLOOD_WAIT_<n>` error exists `[sdk]` → wait n seconds, do not retry blindly (each blind retry of a send may be billed).

## 9. Privacy / data operator
- Telegram receives: the recipient phone number, the **plaintext code** (when we supply it), `payload`, `callback_url`, send timing, our account identity. Telegram says it does not disclose user phone numbers to services. `[tg-search]`
- Terms require every number to come from a user who voluntarily gave it to us and agreed to receive messages, and that we can show that consent `[tg-search]` → privacy policy / login screen should name Telegram (Telegram Messenger Inc.) as a delivery channel and recipient of the phone number.
- Uzbek rules on personal data and cross-border transfer for this flow: not researched `[unverified]` (add to `docs/legal/pre-publication-checklist.md`).
- Never put PII in `payload`; never log the token, full phone numbers or codes; token only in the server env.

## 10. "What about WhatsApp?" (WhatsApp Business Platform, authentication templates)
All from third-party BSP docs `[search]`; Meta pages were unreachable. Nothing verified.
- Needs a Meta Business portfolio, a WhatsApp Business Account, a phone number dedicated to the API, and a Meta-**approved template of category Authentication**: fixed body "<CODE> is your verification code.", mandatory OTP button (copy code / one-tap Android / zero-tap), no URLs/media/emoji, code <=15 chars.
- Without Meta Business Verification the account is capped (reported: 250 business-initiated conversations per 24 h); verification (via a BSP) asks for legal-entity documents (registration certificate, licence, tax certificate) → an unregistered individual is likely **not** eligible (`[unverified]`; sole-trader registrations are accepted in some countries).
- Price: per delivered authentication message, set by recipient country (Meta rate card, some countries have special "authentication-international" rates) plus BSP markup. **Uzbekistan rate not found** `[unverified]`.
- Compared with Telegram Gateway: heavier onboarding (business verification, template approval, BSP), unknown price; Telegram: $0.01 and a simple token, but unverified for +998 and for individuals.

## 11. Adapter checklist (summary)
`POST https://gatewayapi.telegram.org/sendVerificationMessage`, header `Authorization: Bearer $YONDO_TELEGRAM_GATEWAY_TOKEN`, JSON `{"phone_number":"+998…","code":"<our digits>","ttl":300,"payload":"<opaque id>"}` (+ `callback_url` only if we implement the receiver). Timeout ~10 s; do not auto-retry a send; map `ok:false` strings (§3/§7) to internal reasons; `FLOOD_WAIT_n` → 429-style; `BALANCE_NOT_ENOUGH`/`ACCESS_TOKEN_*` → 503 "provider unavailable" + alert (never show as "wrong code").

## 12. Owner checklist (UZ)
1. `gateway.telegram.org` ga o‘z Telegram raqamingiz bilan kiring va so‘ralgan ma‘lumotlarni (o‘zingiz/biznes haqida) to‘ldiring.
2. Balansni to‘ldiring: "Add Funds on Fragment" (TON orqali). Minimal summani va karta bilan to‘lash mumkinligini o‘zingiz ko‘ring; boshida kam summa yetadi.
3. API tokenni `gateway.telegram.org/account/api` sahifasidan nusxalang.
4. Tokenni FAQAT Render → Environment ga `YONDO_TELEGRAM_GATEWAY_TOKEN` nomi bilan qo‘ying. Chatga, GitHub ga, skrinshotga hech qachon tashlamang.
5. Birinchi sinov: kodni o‘z raqamingizga yuboring (o‘z raqamingizga bepul) va Telegram ga kelishini tekshiring.
6. Keyin Telegram i bor boshqa +998 raqamga va Telegram i yo‘q raqamga sinab ko‘ring; menga xato kodini ayting (tokenni emas).
7. Token oshkor bo‘lib qolsa: akkauntda yangisini oling (imkon bo‘lsa) va Render dagi qiymatni almashtiring.

## 13. Open questions
1. Does Gateway deliver to +998 numbers on all operators? Country list and per-country price?
2. Exact error string and HTTP status for a number without Telegram; meaning of each error code; is `ok:false` ever sent with HTTP 4xx/5xx?
3. Minimum top-up; can a Uzbekistan-issued Visa/Uzcard/Humo card fund it (directly or via TON purchase)? Receipts for an individual?
4. May an individual (no company) open and use the account; what "business information" is required; can Telegram refuse?
5. Rate limits (requests/s, per-number cooldown) and `FLOOD_WAIT_n` semantics.
6. Callback timing (which transitions), retry schedule, tolerance; does a report always arrive for `read`?
7. Is the message text/sender/language customisable when `code` is ours? Does the user see "Verification Codes" sender?
8. Does sending to your own number work with a zero balance? Unit of "credits" vs USD?
9. `ttl` range: 30–3600 (changelog) vs 60–86400 (older SDK) — confirm on the live page.
10. Uzbek personal-data / cross-border transfer rules for sending phone numbers to Telegram.
11. WhatsApp: Uzbekistan authentication price, individual eligibility, BSP options.

## 14. Implementation (2026-10-28, part 2)
Code: `apps/api/src/yondo_api/auth/telegram_gateway.py` (adapter), selection in `main.select_otp_provider` (a configured token wins in every environment; the public demo harness pins the on-screen provider and ignores it), tests in `apps/api/tests/test_telegram_gateway.py` and `test_otp_delivery.py` (MockTransport only: **nothing was called against the live API**).

**Request.** One `POST {base}/sendVerificationMessage`, `Authorization: Bearer <token>`, JSON `{phone_number: "+998…", code: <our 6 digits>, ttl: 300, payload: <random id, no PII>}`. No `callback_url`, no `request_id`/`checkSendAbility`. Timeout from settings; exactly one request per send, **never retried** (a blind retry can be billed twice); a failed send writes no challenge and starts no resend cooldown.

**Error mapping** (table `ERROR_RULES` / `DEFAULT_RULE` at the top of the module; the strings are the unverified ones from §3/§7):
| Telegram answer | API result | Log |
|---|---|---|
| `ok:true`, HTTP 2xx | 202, `delivery_channel: "telegram"`, no `development_otp` | info |
| `ok:false`, `PHONE_NUMBER_*` | 422 `otp_channel_unavailable` | info |
| `ok:false`, `BALANCE_NOT_ENOUGH`, `ACCESS_TOKEN_*` | 502 `otp_delivery_failed` | **error** (owner must act: top up / new token) |
| `ok:false`, `FLOOD_WAIT_*`, `REQUEST_*`, anything else | 502 `otp_delivery_failed` | warning |
| non-JSON, no boolean `ok`, `ok:false` without an error string, `ok:true` on non-2xx, HTTP 5xx, timeout, connection error | 502 `otp_delivery_failed` | warning |

On a 4xx the body is read first, so `4xx` + `ok:false` + `PHONE_NUMBER_*` still gives 422 (the real status for an unknown number is undocumented); a 5xx is never trusted. Logs hold only the Telegram error string (strict `[A-Z0-9_]` check, else `UNPARSEABLE`), Telegram's `request_id` as `telegram_request_id`, the HTTP status, or the exception class name. The token, phone and code are in no log line, exception message or exception chain.

**Env vars.** `YONDO_TELEGRAM_GATEWAY_TOKEN` (secret, host environment only; empty = off), `YONDO_TELEGRAM_GATEWAY_BASE_URL` (default `https://gatewayapi.telegram.org`, must be https), `YONDO_TELEGRAM_GATEWAY_TIMEOUT_SECONDS` (default 10). Placeholders are in `.env.example`.

**Concurrency.** On PostgreSQL `issue_otp` first takes `pg_advisory_xact_lock(hashtextextended(<phone>, 0))`, so two simultaneous first requests for one number cannot both send a paid code and then collide on the primary key; the second gets the 429 cooldown. Verified against a real PostgreSQL 16 (3 concurrent requests: 1 send, 202 + 2x429; with the lock removed the same test fails with `IntegrityError`).

**Not done.** Delivery-report callback (and its HMAC check, §5); SMS or any other fallback when Telegram fails or the number has no Telegram; per-country/operator checks; `checkSendAbility`/`checkVerificationStatus`/`revokeVerificationMessage`; any customisation of the message text.

**Must be checked with the owner's real token (unverified):**
1. The exact `error` string (and HTTP status) for a +998 number **without Telegram**: the adapter assumes `PHONE_NUMBER_*`; if it is something else the user sees a 502 "try again later" instead of the 422. The error is logged (`telegram_gateway_rejected`, field `telegram_error`), so one test reveals it; then add it to `ERROR_RULES`.
2. That Gateway delivers to **+998** numbers on every operator, and what a code costs there (§6/§7).
3. That `ttl: 300` and a caller-supplied 6-digit `code` are accepted (§2, §4, open question 9).
4. That `ok:true` really arrives with HTTP 200 (a 2xx is required; anything else is treated as a failure).
5. That a send to the owner's own number works with a zero balance (§6, open question 8).
