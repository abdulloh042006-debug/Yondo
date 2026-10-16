# Screen → API mapping (docs/openapi-v1.json, branch codex/notification-integration)
Prefix `/api/v1`. The prototype calls these paths on an in-browser **mock** (`prototype/src/mockapi.js`) whose responses are validated against the OpenAPI schemas (see `reports/test-report.md`). **None of this has been run against the real server.**

| Screen (route) | Calls | Notes |
|---|---|---|
| Login (`#/login`) | POST /auth/otp/request, /auth/otp/verify, GET /auth/me | DEMO OTP 1234 |
| Roles (`#/roles`) | PUT /auth/roles | customer / companion / vendor |
| **01 Home** (`#/home`) | GET /discovery/companions, GET /bookings | sections are client-side views of one page of results (no server-side “top rated”/“new” endpoints exist) |
| **02 Search** (`#/search`) | GET /discovery/companions (q, service_code, language, rating_min, price_max_minor, limit) | debounce 250 ms; states: loading, empty, error+retry |
| **03 Profile** (`#/c/:id`) | GET /discovery/companions/{id}; POST /safety/reports; PUT /safety/blocks/{id} | badge from `verified`; report/block target must be a **user id** (backend decision, see handoff → Decisions); prototype sends the profile id until the API separates the id types |
| **04 Booking** (`#/book/:id`) | GET /discovery/companions (available_from/until pre-check); POST /bookings | body = exactly service_id, starts_at (UTC ISO), duration_minutes, meeting_place, timezone |
| Bookings (`#/bookings`) | GET /bookings | |
| **05 Chat / active booking** (`#/b/:id`) | GET /bookings/{id}, /payments/bookings/{id}, /chat/bookings/{id}/messages, /meetings/bookings/{id}; POST …/messages, /meetings/…/check-in\|start\|end, /bookings/{id}/cancel\|accept\|decline, /reviews/bookings/{id}, /safety/bookings/{id}/sos?confirmed=true, /safety/trusted-contacts | no websocket in prototype (manual refresh) |
| Pay (`#/pay/:id`) | POST /payments/bookings/{id} (Idempotency-Key), GET /integration/bookings/{id}/preview | only when booking is `accepted`; combined checkout is unavailable |
| **06 Flowers & gifts** (`#/gifts`) | GET /gifts/products, GET/PUT/DELETE /gifts/cart, POST/GET /gifts/test-orders | test orders only; `real_money_moved:false` |
| Companion status (`#/me`) | GET /companions/me/status, /application, /profile; POST application, submit, activate | blockers from API |
| Companion profile/services/availability | GET/POST/PUT /companions/me/profile, …/services, …/availability | photos: not wired (multipart) |
| Companion requests (`#/me/requests`) | GET /bookings; POST accept/decline | customer shown only as `#abcd` |
| Companion earnings (`#/me/earnings`) | none | no companion earnings endpoint; shown as “not live” |
| Vendor products (`#/v`) | GET /vendor/summary, GET/POST /gifts/vendor/products, PATCH /vendor/products/{id}, POST …/unpublish | publish is an admin action (DEMO button) |
| Vendor orders / earnings | GET /vendor/orders, GET /vendor/earnings | response schemas undocumented; earnings returns 503 `vendor_earnings_unavailable` |

Not in prototype: notifications inbox UI, favorites UI, dispute and no-show flows (no endpoints), photo upload, WebSocket chat, admin UI.
