# Web app and admin console — verified feature matrix

Scope: `apps/web` (React/TypeScript/Vite) on top of the existing FastAPI backend. No Supabase,
no second backend, no duplicate tables. Labels: PASS / NOT IMPLEMENTED / OUT OF SCOPE.

## Backend changes made for this work (all tested)

| change | why |
| --- | --- |
| `GET /api/v1/companions/admin/applications` (status / content_status filters, paging) | the admin had no way to *list* applications, only fetch by id. Returns lifecycle state only (no statement, no bio). |
| `GET /api/v1/admin/audit-events` (paging, `target_id`, `action_prefix`) | `admin_audit_events` existed but could not be read. |
| Companion application/content decisions and safety acknowledgements now write an `AdminAuditEvent` **in the same transaction** as the decision | before this only account-status changes were audited. Actions: `companion_application:{approve,reject}`, `companion_content:{approve,reject}`, `safety_{report,sos}:acknowledge`, `account_status:*`. |
| `GET /api/v1/admin/users`: masked phone (`phone_masked`), `roles`, `created_at`, `account_status` + `phone` filters, `offset` | admins need to find the right account without receiving raw phone numbers. |
| Typed responses for `/admin/summary` and `/admin/bookings` (+ `offset`) | contract was untyped. |
| `docs/openapi-v1.json` regenerated | CI keeps it in sync. |

No migration was needed (`admin_audit_events` already existed). Tests:
`apps/api/tests/companions/test_admin_console.py` (12 tests: anonymous/customer/companion denied on
every admin read, queue filters + privacy, audit rows per decision with actor/target/reason,
no audit row on failed (stale) decisions, self-approval denied and not audited, phone masking and
injection-shaped filters rejected, admin accounts protected, acknowledgement audited exactly once).

## Findings worth knowing

* **Nothing in the backend moves a user from `verification_pending` to `active` except an
  administrator** (`POST /admin/users/{id}/status`). Companion profiles are only publicly visible
  for `active` accounts, so this is an operational step; the Users screen supports it (filter
  "Tasdiq kutilmoqda").
* **There is no endpoint to create the first administrator** (and `PUT /auth/roles` refuses
  `admin`). Bootstrap once, directly in the database after that person has signed in by OTP:
  `INSERT INTO user_roles (user_id, role) VALUES ('<user uuid>', 'admin');` and set
  `users.account_status = 'active'`. This is deliberate; do not add a public path.
* Identity verification is `UnconfiguredIdentityEligibility` in production wiring: companions stay
  non-public until a real provider is integrated. The UI states that content approval is not
  identity verification and shows the server's `blockers` verbatim.

## Pages and journeys

| area | status |
| --- | --- |
| Sign-in (phone OTP, resend cooldown, dev OTP shown **only** if the API returns it), session refresh, sign-out | PASS (e2e) |
| Discovery: search, service chips, city, language, max price, rating, "show more" paging, URL-synced filters, empty/loading/error/503 states | PASS (e2e) |
| Companion profile: bio, languages, interests, services + prices (integer tiyin), rating only when real, verified badge only from API `verified: true`, photos via signed URLs | PASS (e2e; photo bytes served by a test double) |
| Booking request (exactly the 5 contract fields), server refusal shown, list, accept/decline/cancel | PASS (e2e) |
| Favorites (confirmed by server before UI changes) | PASS (e2e) |
| Settings (`/settings`): theme choice (Gul/Jurnal/Stone) lives only here, saved per device; linked from Account and Login | PASS (e2e: persists across reload, active on other pages, absent from top bar; axe) |
| Account: age/gender/city, role selection (customer/companion; admin cannot be self-assigned) | PASS (e2e) |
| Companion studio: application create/edit/submit/withdraw, profile, services, photo upload/delete, availability, status & blockers, activate/deactivate | PASS (e2e for application, profile, service, photo upload, status; activate/deactivate, availability and withdraw screens are **not** browser-tested; the underlying API is covered by backend tests) |
| Admin dashboard (real counters only) | PASS (e2e) |
| Admin applications queue + detail (content, services, photos, history), approve/reject with reason + confirmation, stale-revision refusal | PASS (e2e) |
| Admin safety: reports and SOS as *recorded signals*, acknowledge with note | PASS (e2e); SOS rows themselves need an active meeting, so only the empty state is e2e-tested |
| Admin users: filter, masked phone, status change with reason + typed-id confirmation; admins/self protected | PASS (e2e) |
| Admin bookings: read-only list | PASS (e2e) |
| Admin audit log: real server records | PASS (e2e) |
| Payments, chat, meeting check-in/SOS creation, reviews, notifications, trusted contacts, blocks/reports by customers | NOT IMPLEMENTED in this UI (endpoints exist). The Bookings page says so. |
| Gift cart/test orders, vendor screens, beta enrollment admin | NOT IMPLEMENTED in this UI (endpoints exist). The dashboard says so. |
| Admin management of bookings/payments/refunds | OUT OF SCOPE: the backend offers no such actions (no refund logic by design). |
| Photo re-ordering and captions in the studio | NOT IMPLEMENTED (endpoints exist). |

## Honest limits of the verification

* Backend tests ran on **SQLite**. PostgreSQL-only tests are skipped locally; CI's `postgres` job
  is the place they run. Do not read the numbers as PostgreSQL verification.
* The browser tests use the real FastAPI app on SQLite with three **test doubles** (in-memory
  object storage, "always verified" identity check, development OTP provider) because MinIO,
  an identity provider and an SMS gateway do not exist in the sandbox. They are in
  `apps/web/e2e/server.py` and never ship.
* Real-device testing (iOS Safari / Android), screen-reader testing and Firefox/WebKit were not
  performed. axe-core (WCAG 2 A/AA, serious+critical) was run on the listed pages in all three themes.
