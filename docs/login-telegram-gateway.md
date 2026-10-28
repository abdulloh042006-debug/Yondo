# Login codes through Telegram (Telegram Gateway)

Status: **adapter implemented (S35), tested only against a mocked HTTP transport; never called the real gateway.** Reference: <https://core.telegram.org/gateway> and `/gateway/verification-tutorial` (read 2026-10-28). Code: `apps/api/src/yondo_api/auth/telegram_gateway.py`; plugs into `OtpDeliveryProvider` (`auth/providers.py`), chosen by `default_otp_provider` in `main.py`.

## Why
The public demo shows the login code on screen, so anyone can sign in as any phone number: acceptable for a labelled demo, never for real users. Owner decision (2026-10-28): real users get the code via Telegram (WhatsApp later or never); SMS stays a possible fallback. No password system for now (phone + code, 30-day sessions).

## How it behaves
- `YONDO_TELEGRAM_GATEWAY_TOKEN` set → Telegram delivery (also in development/test, so the owner can try it against his own number). Not set → on-screen code in development/test, **503 "otp_delivery_unavailable" in staging/production** (never an on-screen code there).
- `checkSendAbility` first; a number without Telegram gets **422 `otp_telegram_unavailable`** with a clear message in uz/ru/en (nothing is sent, nothing charged beyond what Telegram bills for the check). Then `sendVerificationMessage` with **our** code, `ttl` 300 s (= our challenge lifetime) and the `request_id` from the check. Any other failure → 503 `otp_delivery_unavailable`.
- Our server still generates, hashes and verifies the code (rate limits, resend cooldown and attempt blocking unchanged). The code is never logged and never returned to the browser.
- The public demo harness always keeps the on-screen code (`demo_app.py` passes `DevelopmentOtpProvider`), whatever token the environment holds.

## Owner steps (you sign in and pay; never paste the token in chat)
1. gateway.telegram.org → log in with your Telegram number → create the account (form: account name, company full name, e-mail, phone, country, city; the docs do not say whether individuals are accepted: if rejected, ask Telegram support).
2. Fund the balance: the quick-start says "Add Funds on Fragment" (Fragment is Telegram's TON platform; card payment is not mentioned). Test messages to **your own** Telegram number are free, so test first.
3. Copy the API token from the account's API settings (you can restrict it to the server's IP) and set `YONDO_TELEGRAM_GATEWAY_TOKEN` in the **production** host's environment (not in the demo).
4. Try a login with your own number; tell the assistant what happened (error strings are logged as `tg_error`, never the phone or the code).

## Price and limits (Telegram's pages, not verified in practice)
About **$0.01 per delivered code** (marketing page: "up to 50× cheaper than SMS"); you pay for codes delivered within the time you set; `checkSendAbility` is free if the user cannot be reached, otherwise one message is charged in advance; revoked codes are not refunded; undelivered codes are refunded automatically per the marketing page (the terms are stricter: read them).

## Not verified / follow-ups
- Whether Uzbek numbers and individuals are served, the exact error strings and response shapes, the allowed `ttl` range, whether the API takes JSON bodies as assumed (the first live call will show it).
- Telegram-only login excludes people without Telegram: keep an SMS fallback (Eskiz or similar) for the public launch; decide per user in the login screen.
- `checkVerificationStatus` and the delivery-report callback are not used (Gateway statistics will be less accurate).
- The login screen texts no longer say "SMS" (`login.lead`); no other login text mentions SMS (checked in uz.ts).
