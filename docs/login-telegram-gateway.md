# Login codes through Telegram (Telegram Gateway)

Status: **adapter implemented (S35 live-checked it; S36 merged the two versions into one); live test PASS on 2026-10-28** with the owner's own Uzbek number (free test path): `checkSendAbility`, then `sendVerificationMessage` with our code, `ttl` 300 and the `request_id` from the check, JSON request bodies; the code arrived in Telegram and matched. Unit tests use a mocked transport (`apps/api/tests/test_telegram_gateway.py`). Reference: <https://core.telegram.org/gateway> and `/gateway/verification-tutorial` (read 2026-10-28). Code: `apps/api/src/yondo_api/auth/telegram_gateway.py`; plugs into `OtpDeliveryProvider` (`auth/providers.py`), chosen by `select_otp_provider` in `main.py`. The researcher's fact sheet (API details, price, error candidates, open questions) is `docs/otp-telegram-gateway.md`; its §14 holds the same live findings.

## Why
The public demo shows the login code on screen, so anyone can sign in as any phone number: acceptable for a labelled demo, never for real users. Owner decision (2026-10-28): real users get the code via Telegram (WhatsApp later or never); SMS stays a possible fallback. No password system for now (phone + code, 30-day sessions).

## How it behaves
- `YONDO_TELEGRAM_GATEWAY_TOKEN` set → Telegram delivery in every environment (also in development/test, so the owner can try it against his own number). Not set (or empty) → on-screen code in development/test, **503 `otp_delivery_unavailable` in staging/production** (never an on-screen code there). Optional: `YONDO_TELEGRAM_GATEWAY_BASE_URL` (default `https://gatewayapi.telegram.org`, must be https) and `YONDO_TELEGRAM_GATEWAY_TIMEOUT_SECONDS` (default 10).
- **Two requests at most per code** (JSON bodies, `Authorization: Bearer <token>`), never retried:
  1. `checkSendAbility` with `{phone_number}`. If Telegram says the number cannot be reached (`PHONE_NUMBER_*`), the API answers **422 `otp_channel_unavailable`** and **nothing is sent** (no code, no challenge, no resend cooldown).
  2. Only after `ok:true`: `sendVerificationMessage` with `{phone_number, code, ttl: 300 (= our challenge lifetime), payload (opaque random id), request_id (from the check)}`.
  Any other failure of either call (Telegram error, empty balance, bad token, malformed answer, non-2xx, 5xx, timeout) → **502 `otp_delivery_failed`** with a neutral message; Telegram's reason is only in the server log (`telegram_gateway_rejected`: fields `telegram_method`, `telegram_error`, `http_status`, never the token, the phone or the code). The error mapping is the table `ERROR_RULES` at the top of the adapter.
- Success: **202** with `delivery_channel: "telegram"` and **no** `development_otp`. Our server still generates, hashes and verifies the code (rate limits, resend cooldown and attempt blocking unchanged); the code is never logged and never returned to the browser. On PostgreSQL a per-phone advisory lock makes two simultaneous first requests send exactly one code.
- Web (`apps/web/src/pages/Login.tsx`): the Telegram screen (title "Code sent to Telegram", the number, a hint to open the «Verification Codes» chat, a "no code?" hint and an expandable "I don't have Telegram" explanation) appears **only** when the response says `delivery_channel == 'telegram'`; the development banner and the generic screen are unchanged otherwise. The errors show localised texts (uz/ru/en: `err.otp_channel_unavailable`, `err.otp_delivery_failed`, `err.otp_delivery_unavailable`) and are chosen by error `code`, never by message text. The login copy does not mention SMS.
- The public demo harness always keeps the on-screen code (`demo_app.py` passes `DevelopmentOtpProvider`), whatever token the environment holds.

## Owner steps (you sign in and pay; never paste the token in chat)
1. gateway.telegram.org → log in with your Telegram number → create the account (form: account name, company full name, e-mail, phone, country, city). **An individual account was accepted** (2026-10-28).
2. Fund the balance: the quick-start says "Add Funds on Fragment" (Fragment is Telegram's TON platform; card payment is not mentioned). Test messages to **your own** Telegram number are free, so test first.
3. Copy the API token from the account's API settings (you can restrict it to the server's IP) and set `YONDO_TELEGRAM_GATEWAY_TOKEN` in the **production** host's environment (not in the demo).
4. Try a login with your own number; tell the assistant what happened (the gateway's error string is logged as `telegram_error` together with `telegram_method`, never the phone or the code).

## How to test (live call, free)

Use the Telegram number you logged in to the Gateway with (test messages to it are free). Leave "IP address restrictions" empty while testing from a laptop; set it to the production server IP later.

```
D:/Yondo/.venv/Scripts/python.exe D:/Yondo/apps/api/try_telegram_gateway.py +998XXXXXXXXX
```

The script reads `YONDO_TELEGRAM_GATEWAY_TOKEN` or asks for the token with hidden input (not stored), sends a random code through the real adapter (both steps), prints only the Telegram method and error string on a failure, and checks the code you type back. Exit 0 = OK, 1 = failed or mismatch. Never run it in CI.

## Price and limits (Telegram's pages, not verified in practice)
About **$0.01 per delivered code** (marketing page: "up to 50× cheaper than SMS"); you pay for codes delivered within the time you set; `checkSendAbility` is free if the user cannot be reached, otherwise one message is charged in advance and the following send with that `request_id` is not charged again; revoked codes are not refunded; undelivered codes are refunded automatically per the marketing page (the terms are stricter: read them).

## Not verified / follow-ups
- **Verified live (own number, 2026-10-28):** the two-step flow works, JSON bodies are accepted, `ttl` 300 is accepted, our own code is delivered and matches, an Uzbek (+998) number works, the account was created by an individual.
- **Not verified:** sending to OTHER users' numbers (needs a funded balance, Fragment/TON); the gateway's error strings for a number without Telegram and for an empty balance (they are logged as `telegram_error`; the mapping to 422 vs 502 is a guess until seen); the `payload` field (the live run did not send it; our adapter does, as documented); that a successful answer arrives with an HTTP 2xx (our adapter requires it); the allowed `ttl` range; delivery speed and refunds in practice; **the sender name the user sees**: the login copy (`login.tg.open`, `login.tg.noCode`) names the «Verification Codes» chat and that name is unconfirmed.
- Telegram-only login excludes people without Telegram: keep an SMS fallback (Eskiz or similar) for the public launch; decide per user in the login screen.
- `checkVerificationStatus` and the delivery-report callback are not used (Gateway statistics will be less accurate).
