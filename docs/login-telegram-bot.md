# Login codes through the free Yondo Telegram bot

Owner decision (2026-11-14): login codes go through **our own free Telegram bot** (Bot API
`sendMessage`). The paid Telegram Gateway (`auth/telegram_gateway.py`) stays in the code, **off**
unless the owner enables it. A paid channel is **never** an automatic fallback. Local Uzbek SMS is
a future integration point (checklist at the end). WhatsApp: out of scope. The public demo keeps
the on-screen code (`YONDO_OTP_PROVIDER=auto`, development/test environment); production never
shows a code.

## 1. How it works

```
Browser                         Backend (this repo)                    Bot service (owner's VPS, aiogram)
POST /auth/telegram/link/start  -> challenge (hash only), poll token
   <- deep link t.me/<bot>?start=<challenge>, poll_token (once)
user opens the link  ---------------------------------------------->  /start <challenge>
                                                                       asks for the contact (request_contact)
                                                                       checks contact.user_id == from.id
                                POST /auth/telegram/link/complete  <-  (header X-Yondo-Bot-Secret)
                                stores phone <-> Telegram link,
                                sends the code with sendMessage  ---->  (user sees the code in the bot chat)
GET /auth/telegram/link/status (header X-Yondo-Link-Poll) -> otp_sent
POST /auth/otp/verify {phone_number, code} -> tokens (unchanged)
```

Later logins of a linked phone: `POST /auth/otp/request` sends the code to the linked chat at once.
The backend registers **no webhook** and never calls `getUpdates`: the bot service owns the updates.

Rules the code enforces:
- Challenge: 43 random URL-safe characters (fits Telegram's 64-character `start` limit), only its
  SHA-256 stored, single use, 10-minute lifetime (`YONDO_TELEGRAM_LINK_LIFETIME_SECONDS`),
  at most 5 starts per phone per 10 minutes.
- Status is readable only with the poll token returned once to the browser that started the flow.
- Only private chats: `telegram_chat_id` must equal `telegram_user_id`.
- One Telegram account <-> one phone. A Telegram account already linked to another phone is
  refused (`telegram_account_linked_elsewhere`). The same phone verified again from a new Telegram
  account replaces its link (only after this verified flow).
- The code itself uses the existing OTP rules (6 digits, 5 minutes, 3 tries, 60-second resend).
  A failed send stores nothing: no "code sent" state, no resend cooldown, no paid fallback.
- "Bot blocked / chat not found" = `telegram_bot_unreachable` (422); other failures = `otp_delivery_failed` (502).
- Account deletion removes the phone's Telegram link and challenges.
- `GET /auth/telegram/link/config` tells the web app whether to show the Telegram button.

`/auth/telegram/link/start` returns `already_linked` so the client can go straight to "send code".
That tells a caller whether a number has linked Telegram (accepted trade-off, rate-limited).

## 2. Contract for the bot service: `POST /api/v1/auth/telegram/link/complete`

Request (JSON, `Content-Type: application/json`):

| Header / field | Value |
|---|---|
| `X-Yondo-Bot-Secret` | the shared secret: `YONDO_BOT_SHARED_SECRET`, the same value in the bot's `.env` and on the backend host |
| `challenge` | the `/start` payload, unchanged (string, `^[A-Za-z0-9_-]{1,64}$`) |
| `phone_number` | the shared contact's number; the bot sends it normalised as `+998XXXXXXXXX` (the backend also accepts it without `+`) |
| `telegram_user_id` | `message.from_user.id` (integer; must equal `contact.user_id`, checked by the bot) |
| `telegram_chat_id` | `message.chat.id` (integer; private chat, so equal to the user id) |

Responses (errors are `{"code": ..., "message": ..., "request_id": ...}`; branch on `code`):

| HTTP | Body / code | Bot should tell the user |
|---|---|---|
| 200 | `{"status": "linked"}` | Success: return to YONDO, the server sends the code. If sending fails, the link still counts and the website shows "code not sent, request again". |
| 200 | `{"status": "already_linked"}` | Success: an identical repeat of an already completed challenge by the same Telegram user (no second code). |
| 401 | `invalid_bot_secret` | nothing (configuration error: check the secret) |
| 404 | `telegram_link_invalid` | "Havola yaroqsiz. Saytda qaytadan boshlang." |
| 409 | `telegram_link_used` | same as 404 |
| 409 | `telegram_phone_mismatch` | "Bu Telegram raqami saytda kiritilgan raqamga mos emas." |
| 409 | `telegram_account_linked_elsewhere` | "Bu Telegram hisobi boshqa raqamga ulangan." |
| 410 | `telegram_link_expired` | "Havola eskirgan. Saytda yangisini oling." |
| 422 | `telegram_chat_not_private`, validation errors | only private chats are supported |
| 503 | `telegram_bot_unavailable` / `telegram_bot_secret_unset` | bot login is switched off, or `YONDO_BOT_SHARED_SECRET` is unset or shorter than 32 characters |

Request headers: `X-Yondo-Bot-Secret`, `Content-Type: application/json`, `Accept: application/json`.
The endpoint answers directly (no redirect; the bot does not follow redirects): use the exact
path `/api/v1/auth/telegram/link/complete` on the https origin. The handler sends the code with a
5-second timeout, well inside the bot's 30-second call. Error bodies hold only a stable `code`,
a generic `message` and a `request_id`. Retry only on network errors or 5xx, at most once, with the
same body.

## 3. Owner steps (BotFather and settings)

1. In Telegram open **@BotFather** → `/newbot` → name "Yondo" → a username ending in `bot`.
   BotFather shows the **token**: copy it straight into the host settings (below), never into chat.
2. `/setdescription` and `/setabouttext`: short Uzbek text ("Yondo kirish kodlari").
3. Backend host (e.g. Render → Environment), set:
   - `YONDO_OTP_PROVIDER=telegram_bot`
   - `YONDO_TELEGRAM_BOT_TOKEN=<token from BotFather>`
   - `YONDO_TELEGRAM_BOT_USERNAME=<bot username, without @>`
   - `YONDO_BOT_SHARED_SECRET=<long random string, 32+ characters>` (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
4. Bot service on the VPS: fill its `.env` (section 3a); the same `YONDO_BOT_SHARED_SECRET` value
   goes on both sides.
5. Run `python -m yondo_api.doctor` on the host: "Telegram bot (login codes, free)" must be OK.
6. Test with your own number: open the site → "Telegram orqali davom etish" → "Telegram botni
   ochish" → Start → share the contact → the code arrives in the bot → type it on the site.

**The live bot ↔ backend test is NOT done yet**: it needs the owner's VPS bot configured. Until
then everything is tested with mocked Telegram responses.

Note: the on-screen code exists only with `YONDO_OTP_PROVIDER=auto` (the default) in a
development/test environment, as the public demo runs today; nothing about it changed. Setting
`YONDO_OTP_PROVIDER=telegram_bot` on the demo host switches **real numbers** to the bot, while the
seeded DEMO numbers and the demo harness's own logins keep the on-screen code (`DemoOtpProvider` in
`infra/deploy/demo/demo_app.py`), so the demo still seeds and its sample accounts stay usable.

## 3a. VPS bot `.env` (the owner's aiogram service, not in this repo)

| Variable | Value |
|---|---|
| `YONDO_TELEGRAM_BOT_TOKEN` | the BotFather token (the same token the backend uses for `sendMessage`) |
| `YONDO_TELEGRAM_BOT_USERNAME` | the bot username, without @ |
| `YONDO_API_BASE_URL` | the backend's public https origin, today `https://yondo-demo.onrender.com` |
| `YONDO_BOT_SHARED_SECRET` | 32+ characters; **the same value** as `YONDO_BOT_SHARED_SECRET` on the backend host |
| `YONDO_LINK_COMPLETE_PATH` | `/api/v1/auth/telegram/link/complete` |
| `YONDO_BOT_DB_PATH` | the bot's own local database file (the bot's setting) |
| `YONDO_LINK_TTL_SECONDS` | `600` (matches the backend's `YONDO_TELEGRAM_LINK_LIFETIME_SECONDS`) |
| `YONDO_API_TIMEOUT_SECONDS` | `30` |
| `YONDO_LOG_LEVEL` | e.g. `INFO` |

The bot uses long polling and calls `deleteWebhook` at start: never set a webhook for this token
anywhere. Secrets go only into the host settings / `.env` on the server, never into chat or git.

## 4. A leaked token or secret

- Bot token: @BotFather → `/revoke` → select the bot → new token; replace it on the backend host
  and the VPS; restart both. The old token stops working at once.
- Shared secret: generate a new value, set it on both sides, restart both.
- The token is never logged: the Bot API URL contains it, so the `httpx`/`httpcore` loggers are kept
  at WARNING (`yondo_api/logging.py`), and our errors never chain HTTP exceptions.

## 5. Enabling the paid Telegram Gateway later (owner's decision only)

Set `YONDO_OTP_PROVIDER=telegram_gateway` and `YONDO_TELEGRAM_GATEWAY_TOKEN` (see
`docs/login-telegram-gateway.md`). It replaces the bot as the channel; there is no automatic fallback.

## 6. Future: local Uzbek SMS (research checklist, nothing built)

Integration point: a new class implementing `OtpDeliveryProvider.deliver(phone, code)` in
`auth/providers.py`, selected by a new `YONDO_OTP_PROVIDER` value. Before choosing a provider, check:
- service/OTP route (not advertising SMS), and its terms for login codes;
- coverage of all Uzbek operators;
- sender ID ("Yondo") registration and how long it takes;
- contract type (individual or company), documents, payment in UZS;
- delivery reports (callback or polling) and failure codes;
- price per message and any monthly fee.
