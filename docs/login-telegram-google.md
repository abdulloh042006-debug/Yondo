# Sign in with Telegram and Google

Approved on 2026-11-06 (product decisions §3) and confirmed by the owner on 2026-11-18. Apple sign-in comes later: the tables and code are generic (`provider` in `telegram`, `google`, `apple`), but no Apple code exists yet.

## Rules

- **Accounts stay phone-anchored.** Every account has a verified phone.
  - **Telegram:** an ID token with `phone_number_verified: true` and an Uzbekistan number counts as phone proof. It signs in to the account that has this phone and links the Telegram `sub`. If no account has this phone, it creates one.
  - **Google, or Telegram without a verified phone:** the user proves a phone with a code from the normal code step (Telegram bot; in the demo, shown on screen). Only then is the identity linked or the account created (`POST /auth/social/complete`). No account is ever created without a phone.
- **Never linked by e-mail.** A provider is never linked to an existing account without that account's phone proof (anti-takeover). Google is identified by `sub` only.
- **The password gate is unchanged.** A first social sign-in on an account without a password answers `password_setup_required: true`, and the web shows the username + password screen. Social sessions (`via` = `telegram` / `google`) may complete that step, like a code sign-in. Password sign-in and sliding sessions are unchanged.
- **Settings → Linked accounts:**
  - a signed-in user links Telegram or Google;
  - unlinking needs a password (`password_not_set`, 409);
  - one account per provider (`provider_already_linked`);
  - an identity belongs to one Yondo account (`identity_in_use`).
- **Deleting the account** deletes its identities and pending challenges.
- **Not configured** = `503 provider_not_configured`, and the web hides the button. It is never shown as broken.

## Telegram Login (OpenID Connect, oauth.telegram.org)

Telegram's new login is OIDC: the ID token is a JWT, RS256 by default (ES256 also accepted). The server checks:
- the signature against `https://oauth.telegram.org/.well-known/jwks.json` (cached 1 hour, refetched on an unknown key at most once a minute);
- `iss = https://oauth.telegram.org`;
- `aud` = the Client ID (the bot's numeric ID);
- `exp` (60 s clock skew).

The legacy widget (HMAC of the bot token) is archived and **not** built. Never use samples that check `hash` with the bot token.

**Web: the official JS library** (`https://oauth.telegram.org/js/telegram-login.js?6`), as the owner chose in the BotFather button builder:
1. The page asks `POST /auth/social/telegram/nonce` for a single-use nonce (10 minutes). It asks before the tap, so the popup opens inside the tap and is not blocked.
2. Tapping Telegram's round button (`class="tg-auth-button" data-style="icon"`) calls `Telegram.Login.auth({client_id, request_access: ['phone', 'write'], nonce, lang})`. Telegram shows the "phone number" consent and the "Xabarlarga ruxsat" (direct messages) toggle. The library returns `{id_token}`.
3. `POST /auth/social/telegram {id_token}` (or `/telegram/link` from Settings). The server verifies the token and **requires** the nonce claim to match an unused nonce, which it then marks used.
   - A link nonce is tied to the signed-in user and cannot sign anyone in.
   - The Client Secret is not needed for this flow.
4. **Bot chat:** when the token carries a verified phone equal to the account's phone, the server records the bot chat (`telegram_links`, chat = Telegram `id`). Later codes (reset) then reach the user without pressing Start in the bot.
   - The ID token does not say whether the user switched "Xabarlarga ruxsat" off.
   - If the bot cannot write, a later code answers `telegram_bot_unreachable`, and the usual bot link (`/start`) repairs it.

**Code flow (kept for the mobile app, phase 2):** `POST /auth/social/telegram/start` → oauth.telegram.org (code + PKCE S256, state, nonce) → `/auth/callback/telegram?code&state` → `POST /auth/social/telegram/exchange {code, state, flow_token}`.
- The server exchanges the code with the Client Secret (HTTP Basic, server-side only).
- State and the browser flow token are single-use (10 minutes).
- It needs `YONDO_TELEGRAM_LOGIN_CLIENT_SECRET` and redirect URIs. Without them it answers 503, and the web does not use it.

**COOP:** the site must not send `Cross-Origin-Opener-Policy: same-origin`, because it breaks the popup. The demo sends no COOP header.

## Google (Google Identity Services, ID token)

- The web loads `https://accounts.google.com/gsi/client` only when a client ID is configured.
- It renders Google's own round icon button (`type: icon`, `shape: circle`, `theme: outline`, `size: large`). This is Google's branded button, so its brand rules are met.
- `POST /auth/social/google {credential}`. The server verifies the token against `https://www.googleapis.com/oauth2/v3/certs`:
  - `iss` = `accounts.google.com` or `https://accounts.google.com`;
  - `aud` in `YONDO_GOOGLE_CLIENT_IDS`;
  - `exp`.
- No redirect URI and no client secret are needed.

## Brand

- Our own controls stay ink/paper/carrot.
- The provider marks keep their official colours, as each provider's brand rules require: Telegram's blue round button from its library, and Google's multicolour "G". These are the only non-palette colours, and only inside those two marks.

## Security

- Rate limit: 20 requests per minute per IP on every new endpoint (`rate_limited`, the password limiter's setting).
- No tokens, codes, ID tokens or nonces are logged.
- Only SHA-256 hashes of the state, flow token, nonce and sign-up token are stored. The PKCE verifier is stored for at most 10 minutes. Rows expired for more than a day are deleted on the next start.
- Errors are codes:
  - `provider_not_configured`;
  - `social_state_invalid`;
  - `social_token_invalid`;
  - `social_code_invalid`;
  - `social_provider_unreachable` (503);
  - `identity_in_use`;
  - `provider_already_linked`;
  - `identity_not_linked`;
  - `signup_token_invalid`;
  - `invalid_redirect_uri`;
  - `password_not_set`.
- Secrets live only in the host's environment.

## Owner checklist (Render → yondo-demo → Environment)

| Variable | Value | Needed for |
|---|---|---|
| `YONDO_TELEGRAM_LOGIN_CLIENT_ID` | the bot's Client ID from BotFather (the numeric bot ID; public) | Telegram button on the web |
| `YONDO_GOOGLE_CLIENT_IDS` | the Web client ID (`….apps.googleusercontent.com`); later add the Android client ID after a comma, web first | Google button |
| `YONDO_TELEGRAM_LOGIN_CLIENT_SECRET` | the Client Secret from BotFather → Login Widget (a secret) | only the mobile code flow (phase 2); the web does not need it |
| `YONDO_TELEGRAM_LOGIN_REDIRECT_URIS` | leave empty (default `<YONDO_PUBLIC_WEB_URL>/auth/callback/telegram`) | only the code flow |

1. **BotFather → your bot → Bot Settings → Login Widget → Allowed URLs.** The JS library sends the page address (`origin + path`) as its redirect, so add:
   - `https://yondo-demo.onrender.com`
   - `https://yondo-demo.onrender.com/login`
   - `https://yondo-demo.onrender.com/settings`
   - `https://yondo-demo.onrender.com/auth/callback/telegram` (code flow)

   The bot token that was shown in chat on 2026-11-18 is being revoked. After a revoke, check whether the Login Widget Client Secret changed, and paste the new one only into Render.
2. **Google Cloud console** (the same project as the Firebase project "Yondo"; stay on Spark, **never** Blaze):
   1. OAuth consent screen: app name Yondo, support e-mail, the scopes `openid`, `email`, `profile` (basic scopes, no Google verification).
   2. While it is in **Testing**, only the listed test users can sign in. Press **Publish app** ("In production") so everyone can.
   3. Credentials → the Web OAuth client: Authorized JavaScript origins = `https://yondo-demo.onrender.com` (done). No redirect URI is needed, so the placeholder `/api/auth/google/callback` can be deleted.
   4. Paste the client ID into `YONDO_GOOGLE_CLIENT_IDS`.
3. Redeploy, then open `/login`: the round Telegram and Google buttons appear.

**BLOCKED until the keys are set:**
- the buttons (hidden);
- a live check with a real Telegram / Google account;
- whether Telegram really echoes the `nonce` claim (the docs promise it; the server requires it).

If the live check shows tokens without a nonce, tell the agents; do not turn the check off.
