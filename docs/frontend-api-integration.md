# YONDO — frontend/backend integration contract for Claude

Branch: codex/notification-integration
Base: codex/manual-gifts-click-test

## Basic rules

- API prefix: /api/v1; machine-readable schema: docs/openapi-v1.json
- Development OpenAPI runtime: /openapi.json.
- Regenerate after API changes: cd apps/api and run python export_openapi.py.
- CI checks freshness with python export_openapi.py --check.
- Auth: Authorization: Bearer <access_token>, opaque token (not assumed JWT).
- OTP endpoint: POST /api/v1/auth/otp/request; demo OTP only in development/test.
- Auth endpoints: /auth/otp/verify, /auth/refresh, /auth/logout, /auth/me.
- Never show test CLICK transactions as real payments or collected money.
- Offline gift test routes require a locally enabled test flag; hidden in production.
- Never imply recorded SOS calls emergency responders.
- No mobile/admin UI code was modified here.

## Unified in-app notifications

GET /api/v1/notifications?unread_only=false&limit=30&offset=0
GET /api/v1/notifications/unread-count
POST /api/v1/notifications/{notification_id}/read
POST /api/v1/notifications/read-all

Read-all returns {"marked_count": 0} when no unread messages remain.
Cross-user notification read requests return 404. Pagination is newest first,
ordered by creation time and UUID; supports limit 1..100 and offset >= 0.

NotificationRead:
- id: UUID
- booking_id: UUID|null
- gift_order_id: UUID|null
- kind: string
- details: object
- created_at: ISO 8601 datetime
- read_at: ISO 8601 datetime|null

Exactly one of booking_id / gift_order_id is non-null.
For a booking notice, open that booking in the mobile UI.
For a gift notice, use the test order detail ONLY in local testing.

Emitted kinds:
booking_requested, booking_accepted, booking_declined, booking_cancelled,
payment_confirmed, chat_message, review_reminder,
meeting_reminder_24h, meeting_reminder_1h,
gift_order_created, gift_test_paid, gift_preparing,
gift_out_for_delivery, gift_delivered, gift_cancelled.

Gift order creation notifies active admins; subsequent gift transitions
notify the customer. Gift notifications contain IDs, status and simulation
flags but NO private delivery notes, secrets or payment credentials.
review_reminder goes to both booking participants after meeting completion.

This is a durable in-app inbox, not a push/SMS/email system. Client updates
after mutations or via moderate foreground polling. Scheduled meeting reminders,
external notification delivery and FCM/APNs still require separate work.

## Suggested client integration sequence

1. OTP request, OTP verify, then /auth/me and roles.
2. /discovery/companions for list and companion details.
3. /bookings for role-scoped booking creation, acceptance and cancellation.
4. /chat/bookings/{booking_id}/messages and its WebSocket ticket workflow.
5. /meetings/bookings/{booking_id} for check-in/start/end.
6. /reviews/bookings/{booking_id} once a meeting is completed.
7. /notifications for user-visible events and unread badges.
8. In local CLICK test mode only, /gifts/test-orders and its admin order
   status endpoints. Clearly label simulated payments.
9. /admin/safety and /beta are protected; no client bypass of admin roles.

## API response semantics

401 means invalid/missing/expired bearer credentials.
403 means account/role restrictions; never fall back to admin.
404 means unavailable, missing, or intentionally hidden private resources.
409 means conflict/stale state; refresh the relevant resource.
422 means invalid inputs; surface validation errors.
503 means unavailable provider or unconfigured financial/business rules.

Structured error objects expose code, message and request_id.
Drive UI logic from code, not by matching the human-language message.
Clear notification caches and customer state when tokens/accounts change.

## Not completed by this integration

Actual mobile/web interface (Claude scope), real CLICK merchant sandbox,
live payment checkout, FCM/APNs, scheduled meeting/review pushes, SMS provider,
server deployment, real closed beta, emergency dispatch, and real gift logistics.
Do not merge into main or production without QA and integration agreement.
