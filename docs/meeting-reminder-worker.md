# YONDO — automatic meeting reminders (backend)

Branch: codex/scheduled-meeting-reminders, based on codex/notification-integration.

## Implemented

- For CONFIRMED bookings only, queue an in-app notice for customer and companion
  approximately 24 hours and 1 hour before the meeting.
- Supported kinds: meeting_reminder_24h, meeting_reminder_1h.
- Every notice contains the booking UUID, UTC starts_at, meeting timezone and
  minutes_before_start (1440 or 60). No meeting-place text, phone, sensitive
  coordinates, or personal contact details are in the notice.
- Accounts of both participants must be ACTIVE; cancelled, unconfirmed,
  completed, suspended-party and past meetings are excluded.
- One reminder per recipient per booking and lead time; repeated sweeps are
  safe through unique database constraints and ON CONFLICT DO NOTHING.
- PostgreSQL SELECT FOR UPDATE SKIP LOCKED prevents two overlapping workers
  from processing the same booking, and serializes against cancellation.
- Transactions commit per booking; a failed sweep can be retried.

## Scheduling and execution

The reminders are not emitted by the web API automatically. A separate worker
must be configured and **running** in the chosen environment.

For a one-off test/scheduled cron run from apps/api after migrations:

    python -m yondo_api.notifications.reminder_worker --once

For a long-running worker, controlled by the deployment's service supervisor:

    python -m yondo_api.notifications.reminder_worker --loop --interval-seconds 300

The runner queries YONDO_DATABASE_URL and uses existing notification tables.
Use only one supervised worker in normal deployments; parallel PostgreSQL runs
are nevertheless deduplicated by the database. Keep the loop running under a
service manager that restarts it on failure. Do not run an unmanaged loop from
a terminal used for production maintenance.

The worker considers a 10-minute "due" interval near each 24h/1h lead. A
five-minute loop tolerates small delays. It does NOT send stale reminders
after a missed window; missed runs may cause no reminder. Polling every
60–600 seconds is supported, and the window is at most 30 minutes.

There is a 5000-booking-per-window scan cap per sweep. Monitor backlog and
resize/split the worker if the product grows beyond this volume.

## Frontend interface / Claude

The existing inbox endpoints require the authenticated user's bearer token:

- GET /api/v1/notifications
- GET /api/v1/notifications/unread-count
- POST /api/v1/notifications/{id}/read
- POST /api/v1/notifications/read-all

New kinds do not change the OpenAPI shapes. For both kinds, open the matching
booking; render the timezone appropriately using booking.starts_at and
booking.timezone. The "24h"/"1h" labels reflect the scheduled lead, not
an assertion of precisely-timed user-visible push delivery.

## NOT included

No FCM/APNs, SMS, Telegram alerts, external push credentials, server deployment,
or running production scheduler. Notifications are durable in the database only.
No automatic meeting check-in, unauthorized status changes, or safety dispatch.
The production environment and user consent/privacy policies still require
approval. Test and CI passing does not mean this job has been deployed.

## Verification

- SQLite upgrade/check/downgrade and PostgreSQL migration consistency.
- 24h and 1h window tests; retries and no stale notifications.
- Role/account isolation and canceled booking exclusions.
- PostgreSQL parallel sweep test verifies exactly-once rows.
- Ruff, Pytest suite, CLI smoke and existing OpenAPI contract check.
