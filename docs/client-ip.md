# Client IP for per-IP limits (proxy trust)

Per-IP limits (code requests, password sign-in, social sign-in) key on the client IP. A client must not be able to choose that key by sending its own `X-Forwarded-For`.

## How the API finds the client IP

`ClientIpMiddleware` (`apps/api/src/yondo_api/api/client_ip.py`) runs before everything else. uvicorn's own proxy-header handling is **off** (`--no-proxy-headers` in `apps/api/Dockerfile`, `proxy_headers=False` in the demo harness).

| `YONDO_CLIENT_IP_MODE` | Client IP | When to use |
|---|---|---|
| `peer` (default) | the TCP peer; no header is trusted | always safe. Behind a proxy, all visitors share the proxy's address, so the limits become global. |
| `xff` | the `YONDO_CLIENT_IP_XFF_HOPS`-th entry **from the right** of `X-Forwarded-For` | the proxies in front append to the header. Entries further left can be written by the client and are ignored. |
| `header` | the single value of `YONDO_CLIENT_IP_HEADER` | the edge sets that header itself and overwrites any value the client sent |

- A header is used only when the TCP peer is inside `YONDO_TRUSTED_PROXY_CIDRS` (default: private networks and loopback).
- An unparsable value falls back to the peer.
- Tests: `apps/api/tests/test_auth_hardening.py` (a forged header does not change the limiter key).

## DigitalOcean package

Caddy is the only proxy, and it overwrites `X-Forwarded-For` with the real client. `infra/deploy/digitalocean/docker-compose.yml` therefore sets `YONDO_CLIENT_IP_MODE=xff` (one hop).

## Render (the public demo): to be confirmed live

Render does not document its forwarding headers.
- A 2021 thread on Render's feedback board says Render **appends** to an incoming `X-Forwarded-For` rather than replacing it, so a client can put any value at the left: https://feedback.render.com/features/p/send-the-correct-xforwardedfor
- Render's edge is fronted by Cloudflare, and Cloudflare-style headers (`cf-connecting-ip`, `true-client-ip`) were reported in front of Render services: https://community.render.com/t/missing-x-forwarded-for-header-on-api-rewrites-to-backend/24481

Until this is confirmed, the demo stays on `peer`. That is safe, but all visitors share one bucket. To choose the mode:
1. Deploy, sign in as admin, and open `GET /api/v1/admin/diagnostics/client-ip`. It shows the TCP peer, the resolved IP and the forwarding headers of **your own** request.
2. Open it again with a forged header, for example `curl -H 'X-Forwarded-For: 6.6.6.6' -H 'Authorization: Bearer …' https://yondo-demo.onrender.com/api/v1/admin/diagnostics/client-ip`.
3. Pick the setting that shows your real address in both calls:
   - If `cf-connecting-ip` or `true-client-ip` holds your real address and the forged value does not appear there, set `YONDO_CLIENT_IP_MODE=header` and `YONDO_CLIENT_IP_HEADER=<that header>`.
   - Otherwise set `xff`, with `YONDO_CLIENT_IP_XFF_HOPS` = the position of your real address counted from the right (usually 1 or 2).
