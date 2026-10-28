# Cancellation tracking and abuse prevention (closed beta)

Status: implemented, **all numbers are PLACEHOLDERS awaiting the owner's approved policy**.
Owner decisions (2026-10-28): track cancellations, last-minute cancellations and no-shows; restrictions
only after admin review; no monetary penalties; emergencies are not penalised automatically; everything audited.

## What is NOT done (on purpose)
No fee, penalty, refund or any money logic (`payment.refund_required` on cancel is the existing manual flag).
No automatic restriction: a threshold only opens a review case; only an admin creates a restriction.
No public "policy" endpoint (the numbers are unapproved). `booking.status = disputed` stays unused; disputes
are event-level. Discovery does not hide restricted companions. Booking-attempt throttling counts created
requests only (DB-based, no Redis); failed attempts are not counted.

## Data model (migration `20261028_0018`, additive)
- `cancellation_events`: one row per cancel / decline / no-show / system expiry. Who (`party`: customer, companion,
  admin, system; `actor_user_id`), counted against (`subject_user_id`, `subject_role`), when (`occurred_at`),
  `lead_seconds` to `starts_at`, `last_minute`, `reason`, `excuse_state` (none, claimed, granted, rejected),
  `review_state` (none, open, reviewed), dispute and review notes. Unique per (booking, kind, subject).
- `cancellation_cases`: "needs admin review" (trigger: cancellations, last_minute, no_shows, emergency_claims). One
  open case per user+role+trigger. Closing a case moves the counting baseline of that trigger forward.
- `booking_restrictions`: admin-made, temporary (`ends_at`), role `customer` (cannot create requests) or `companion`
  (cannot accept requests; customers cannot request them). Active = not lifted and not ended. Reason is internal.
- `cancellation_audit_entries`: append-only trail (action, actor, subject, previous_state, new_state, reason,
  time). Admin actions are mirrored into the console-wide `admin_audit_events` (`booking_restriction:*`, ...).
- `user_notifications`: new kinds `booking_no_show`, `cancellation_warning`, `booking_restricted`,
  `booking_restriction_lifted` (the last two have no booking).

## Rules
- Counted: a `cancelled` event whose booking was `accepted`/`confirmed` (withdrawing a pending request is recorded, not
  counted, unless configured), and a `no_show`. Never counted: declined, expired, `granted` excuses. A claimed
  emergency is not counted until an admin rules (`uphold` makes it count, `excuse` excuses it); piling up claims opens
  its own case. Counting window is rolling; counts are per user and role.
- Last-minute = `lead < cancellation_last_minute_hours` (exactly on the deadline is on time; after the start counts).
- No-show: nothing set `no-show` before; an admin records it (`confirmed` booking, start passed); it sets the status.
- Warning notice when the counted cancellations reach the warning threshold; review case at the review thresholds.
- Restricted customer: `POST /bookings` -> 403 `booking_restricted` with `details.ends_at` (never the reason).
  Restricted companion: accept -> 403 `booking_restricted`; new requests to them -> 409 `companion_not_accepting_requests`.
  Cancelling, declining and reading are never blocked. Account erasure clears the user's own free text.
- Spam: existing slot overlap check (`booking_time_unavailable`) + PG exclusion constraint kept; new rate limit
  (429 `booking_rate_limited`) and open-request caps (409 `booking_open_limit_reached`,
  `booking_open_limit_per_companion_reached`). The limiter is injected (`app.state.booking_rate_limiter`).

## Config (`YONDO_` env prefix, defaults are placeholders; 0 = off for thresholds/limits)
`CANCELLATION_TRACKING_ENABLED=true`, `CANCELLATION_LAST_MINUTE_HOURS=24`, `CANCELLATION_WINDOW_DAYS=30`,
`CANCELLATION_COUNT_PENDING_REQUESTS=false`, `CANCELLATION_WARNING_THRESHOLD=3`, `CANCELLATION_REVIEW_THRESHOLD=5`,
`CANCELLATION_LAST_MINUTE_REVIEW_THRESHOLD=3`, `CANCELLATION_NO_SHOW_REVIEW_THRESHOLD=2`,
`CANCELLATION_EMERGENCY_CLAIM_REVIEW_THRESHOLD=3`, `BOOKING_RESTRICTION_DEFAULT_DAYS=7`,
`BOOKING_RESTRICTION_MAX_DAYS=30`, `BOOKING_REQUESTS_PER_HOUR_LIMIT=20`, `BOOKING_OPEN_REQUESTS_LIMIT=10`,
`BOOKING_OPEN_REQUESTS_PER_COMPANION_LIMIT=3`. Validated at start (warning <= review, default <= max days).

## Endpoints (`/api/v1`)
User: `GET /cancellations/me/events`, `GET /cancellations/me/restrictions`, `POST /cancellations/me/events/{id}/dispute`
(note + optional emergency claim; 404 unless it is the caller's own event; 409 `dispute_already_open`,
`event_already_reviewed`). `POST /bookings/{id}/cancel` accepts `reason` and `emergency`. Users never get user ids.
Admin (`/admin/cancellations`, 401/403 for non-admins): `GET events|cases|restrictions|audit`, `GET users/{id}/summary`,
`POST events/{id}/review` (`excuse|uphold` + note), `POST bookings/{id}/no-show` (201; 409 `no_show_too_early`,
`no_show_already_recorded`, `invalid_booking_transition`), `POST cases/{id}/close`, `POST restrictions` (201; 422
`restriction_too_long`, `restriction_role_mismatch`; 409 `restriction_already_active`), `POST restrictions/{id}/lift`
(409 `restriction_not_active`). Notes and reasons are 8-2000 characters.

## Needs the owner
Real values for every placeholder above (especially what is "last-minute", the thresholds, restriction durations); whether
a still-pending withdrawal should count; whether claimed emergencies should count until reviewed; whether a user may appeal
a restriction in-app (today: the support form); whether companions should be hidden from discovery while restricted.
