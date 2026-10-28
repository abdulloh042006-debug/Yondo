# YONDO — Phase 16–20 validation and beta readiness

## Branch and isolation

Working branch: codex/phases-16-20, based on 527dc0c from codex/phases-7-10.
No production data, real provider keys, hosting, payments, or public-beta access were enabled.
The earlier Phase 11–15 source checkout is preserved.

## Delivered backend foundations

### 16 — Booking + Gift integration
- Customer-only quote composed from an accepted booking and a live gift cart.
- Booking and gift currency mismatch, missing availability, stale stock, and integer overflow fail closed.
- No fake all-in price: platform fee, delivery fee, and payable total remain null.
- Combined checkout returns 503 until payment, fulfillment, cancellation and refund rules are approved.

### 17 — Vendor panel API
- Role-protected inventory edits, ownership constraints, vendor summary and voluntary unpublication.
- Stock-only edits preserve existing public approval; changes to public descriptions and prices require admin re-approval.
- Orders, fulfillment, delivery, vendor earnings and storefront UI are NOT implemented and report unavailable.

### 18 — Notifications
- Durable in-app inbox with unread count and owner-only read acknowledgements.
- Same-transaction records for booking request/accept/decline/cancel, new chat messages and confirmed payment.
- Source-id uniqueness limits duplicate events; no FCM, SMS, email or delayed reminders are delivered yet.

### 19 — Testing
- New authorization, pricing, status, event-deduplication and beta enrollment regression tests.
- CI branch build and a dedicated PostgreSQL migration/concurrency job.
- SQLite migration and schema-diff verification. Native PostgreSQL validation requires GitHub Actions or a running Linux engine.

### 20 — Closed Beta
- Admin-managed test-user cohort and authenticated feedback intake.
- User cannot join or submit feedback without explicit admin enrollment.
- Admin-only readiness report defaults to ready: false and beta_live: false.
- Does not invite real testers, launch a real beta or approve the current payment/privacy/safety gaps.

## Mandatory beta go/no-go checks

1. Approved identity/selfie verification provider and privacy/consent review.
2. Approved cancellation, refund, dispute, platform fee and gift shipping policies.
3. Combined checkout provider, vendor orders, fulfillment, delivery tracking, payout safeguards.
4. PostgreSQL concurrency tests, migration rollback rehearsals, and race-condition review.
5. Redis fan-out, push notifications, scheduling and delivery monitoring.
6. Moderation operations, on-call handling, safety escalation and no-show processes.
7. Mobile/device usability, accessibility, signed webhook and replay defenses.
8. Test data privacy, monitoring, rollback plan, beta invitations and written user consent.

### Proposed closed-beta cohort (roadmap)

Only AFTER gates are approved: 20–50 customer volunteers, 10–20 vetted companions and
a few approved vendors. Start with controlled test flows and no live charge capability
unless the full payment policy/provider integration has been verified. Collect booking,
safety, UX, cancellation, pricing and support feedback. No external outreach was performed.

## Remaining work / limitations

This is NOT a production-ready Phase 20 beta launch.
The main remaining scope is actual combined payment and order fulfillment, vendor UI and
settlements, push/meeting/review reminders, live safety operations and formal beta operations.
Do not equate endpoint implementations with completed user-facing product phases.

## Verified local checks (2026-10-13)

- Phase 11–15 predecessor suite: 165 passed, 6 skipped (PostgreSQL-only), exit 0.
- Phase 16–20 initial five regressions: 5/5 passed.
- Phase 16–20 expanded eight regressions: 8/8 passed.
- Ruff across API source, tests and migrations: PASS.
- Python compileall across API source, tests and migrations: PASS.
- SQLite Alembic upgrade to 20261013_0011: PASS.
- SQLite Alembic downgrade by one revision, upgrade again and schema check: PASS.
- Python wheel using pip isolated build: PASS; no-build-isolation failed on an older venv without setuptools.build_meta.
- Local Docker Linux service is stopped; native PostgreSQL tests await CI.
- CI YAML adds branch builds and PostgreSQL migration/exclusion/concurrency job; unverified until GitHub Actions executes.
- Final full-suite rerun with all eight new tests: **173 passed, 6 skipped**, exit code 0; only a Starlette/httpx deprecation warning remained.

## GitHub Actions follow-up

- Initial run for commit c21031c: PostgreSQL migrations/schema/concurrency PASS; Linux API 172 passed, 6 skipped, and one failing chat chronological-order assertion.
- Root cause: SQLite second-resolution database defaults created timestamp ties; random UUID tie-breaking could reorder chat messages.
- Fix: explicit UTC microsecond timestamps for system/user messages and in-app notifications; stronger chronological regression assertion.
- After fix, targeted chat + Phase 16–20 suite: 10 passed, Ruff PASS. Follow-up Linux CI required.
