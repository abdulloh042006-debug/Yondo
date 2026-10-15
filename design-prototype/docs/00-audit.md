# YONDO — Phase 1 Audit (docs/00-audit.md)

Date: 2026-10-13. Method: read TZ.md, ROADMAP.md, README.md on `main`; cloned repo; inspected `main` and the most advanced branch `codex/mvp-safety-reconciliation` (113 files vs main). Labels: **Verified-by-reading** = I read the code. **Not run** = no test result claimed.

## 1. Repo state
- `main` (2 commits): docs + Phase 4 backend foundation only (health, users/roles, permissions). README status: "Planning / Pre-MVP".
- Branches ahead of main: `abdulloh…development-infrastructure` (OTP auth, Phase 6), `codex/phases-7-10`, `codex/phases-16-20`, `codex/mvp-safety-reconciliation` (newest; 1 open PR on repo).
- **No frontend exists** on any branch: `apps/mobile/README.md` and `apps/admin/README.md` are stubs. Design work is therefore greenfield; "working code" = FastAPI backend only.
- Docs on the advanced branch: companion-system, mvp-payment-consistency, mvp-safety-ops, phase6/11-15/16-20 validation.
- Priority applied: TZ.md > ROADMAP.md > code > README.

## 2. Findings that change the design (read before Phase 2)
1. **Backend states differ from the master prompt.** Booking enum: pending, accepted, confirmed, active, completed, cancelled, **no-show**, disputed (8, TZ §10). Prompt lists 7; prototype must include no-show.
2. **Payment is not live.** `PaymentProvider` is a Protocol; default `UnconfiguredPaymentProvider` raises. Provider choice is undecided (TZ §26). Payment statuses: creating/pending/succeeded/failed. UI must say "demo payment".
3. **Platform fee is undefined.** `platform_fee_bps` is nullable config; checkout preview returns `platform_fee_minor: None` and `delivery_fee_minor: None`. All UZS fee numbers in the prototype are DEMO.
4. **Cancellation percentages undefined** (TZ §21: set after business model). Refund on paid cancel is only flagged `refund_required` for manual reconciliation. UI must not promise automatic refunds.
5. **SOS stores an alert only.** Endpoint returns `emergency_service_contacted: false`; requires active booking + confirmation. No live tracking found. UI copy: "alert sent to Yondo review", never "help is on the way".
6. **Verification has three separate things in code**: identity status (unknown/pending/verified/rejected, via integration protocol), application status (draft/submitted/approved/rejected/withdrawn), content status (draft/pending/approved/rejected). Badge only on verified identity AND approved profile state.
7. **TZ vs brand brief conflict:** TZ §28 and README list "Romantic" gift category. The brief forbids romantic wording. Proposal: keep category internal name, display as "Maxsus kunlar" (special occasions); needs product-owner decision. Flagged, not silently resolved.
8. **Prices stored as `price_minor` + `currency`** (BigInt). Prototype should model UZS as integer minor units.
9. **Money/phone privacy:** phone is never in public schemas (ADR 0001, TZ §41); only approximate area for companions.

## 3. Status matrix
Legend — Specified: TZ/ROADMAP. Implemented: code on advanced branch. Tested: test files exist (118 test functions counted; **results not yet verified, see §5**). Design: status before this project.

| Feature | Specified | Implemented | Tested | Design status | Integration needed |
|---|---|---|---|---|---|
| Phone + OTP auth | TZ §42 | Yes (provider-agnostic) | tests/test_auth.py exists | None | SMS provider (not chosen) |
| Roles / permissions / account status | TZ §2,40 | Yes | test_permissions, test_models | None | — |
| Customer profile | TZ §3,36 | Partial (user model; no customer profile endpoints found) | — | None | — |
| Companion application/profile/services/availability/photos | TZ §4,8 | Yes | test_lifecycle, test_photos, test_resources | None | Identity verification provider (protocol only) |
| ID + selfie verification | TZ §4,14 | Protocol/status only | — | None | Provider not chosen |
| Search + filters + favorites | TZ §7,34 | Yes (discovery) | test_discovery | None | Distance needs maps provider |
| Home sections (Available Today, Nearby, Top Rated…) | TZ §6 | Not found as endpoints | — | None | Ranking rules undefined |
| Booking + state machine | TZ §9–10 | Yes (accept/decline/cancel) | test_bookings | None | — |
| Booking contract (two-party confirm) | TZ §11 | Not found | — | None | Spec needed |
| Check-in / start / end meeting | TZ §12 | Yes (meetings) | covered in lifecycle tests (unverified) | None | — |
| Payment + webhook | TZ §26 | Partial (provider-agnostic, unconfigured) | test_payments | None | Local provider |
| Companion payout/earnings | TZ §27 | `GET /earnings` exists; payout flow unverified | — | None | Payout provider |
| Chat (REST + socket ticket) | TZ §15 | Yes | test_chat | None | Contact-moderation deferred (TZ §15) |
| Ratings/reviews | TZ §13 | Yes (reviews) | in phases11_15 tests | None | — |
| Report / block | TZ §24–25 | Yes | test_phases11_15 | None | — |
| Trusted contacts | TZ §17 | CRUD exists | — | None | — |
| SOS | TZ §18 | **Alert record only** | test_safety_admin_ops | None | Emergency channel undefined |
| Dispute center | TZ §23 | Booking status only; no dispute endpoints found | — | None | Spec needed |
| Gifts catalog/cart/orders | TZ §28–29 | Partial (products, cart, orders, vendor create/publish) | test_phases16_20 | None | Delivery undefined |
| Gift order statuses (courier etc.) | TZ §31 | Not found | — | None | Courier out of MVP |
| Surprise Builder | TZ §32 | Not found | — | None | Future |
| Booking+gift checkout | ROADMAP P16 | Preview endpoint exists | test_phases16_20 | None | Fees undefined |
| Notifications | TZ §33 | Yes (in-app); push adapter protocol | test_phases16_20 | None | FCM not wired |
| Admin (moderation, reports, safety alerts, beta) | TZ §38–39 | API only; no admin UI | test_safety_admin_ops | None | Admin UI |
| Vendor panel | TZ §30 | API partial; no UI | — | None | — |
| Frontend (mobile/web/admin) | ROADMAP P3 | **None** | — | None | All |

## 3b. Screen → API mapping
Superseded by section 6 and `01-screen-api-mapping.md` (exact paths from `docs/openapi-v1.json`).

## 4. Assumptions (marked ASSUMPTION)
- ASSUMPTION: fee, delivery and cancellation numbers in UI are DEMO placeholders.
- ASSUMPTION: Uzbek Latin copy drafted by me; needs native review.
- ASSUMPTION: font choice must cover oʻ gʻ ʼ; to be tested in Phase 2.
- ASSUMPTION: "Romantic" category displayed as "Maxsus kunlar" pending owner decision.

## 5. Verification status
- Backend tests: **not verified.** A run was started (sqlite default per conftest) but dependency install had not completed at time of writing. Result will be appended to `/reports` if it finishes; until then no pass/fail is claimed.
- No production code was modified. Clone is read-only for this project; all work lives under `/design-prototype` outputs.
- Not reviewed: exact router prefixes, migration contents, CI workflows, full test bodies.

## 6. Update — branch `codex/notification-integration` (read 2026-10-13)
Sources read: `docs/frontend-api-integration.md` (90 lines) and `docs/openapi-v1.json` (OpenAPI for Yondo API 0.1.0: **104 paths, 77 schemas**). Reading only; no code run.
Corrections to earlier sections:
- Exact prefixes exist: `/api/v1/discovery/companions`, `/chat/bookings/{id}/messages`, `/meetings/bookings/{id}/check-in|start|end`, `/reviews/bookings/{id}`, `/payments/bookings/{id}`, `/safety/...`, `/notifications`, `/integration/bookings/{id}/preview|checkout`. The route list in section 3b was my guess and is replaced.
- New since earlier branch review: in-app notifications (13 kinds, inbox only, no push/SMS), offline gift **test** orders and a CLICK **test** flow, `vendor` summary/orders/earnings endpoints, `beta` endpoints. Still absent: dispute endpoints, no-show endpoints, booking contract UI flow, courier logistics.
- `BookingCreate` takes only service_id, starts_at, duration_minutes, meeting_place (free text), timezone. There is **no extras or gift field**: gifts go through cart + `/integration/bookings/{id}/checkout`.
- `CompanionCard` exposes `verified: boolean` (not the three raw statuses), nullable `rating`, `review_count`, services with `price_minor` and `unit_minutes`. `gender` is returned but the UI should not display it.
- `ProductRead.category` enum includes `romantic` — confirms the TZ conflict in finding 7. UI label stays "Maxsus kunlar" pending owner decision.
- Payment: `PaymentResponse` has `subtotal_minor`, `platform_fee_minor`, `checkout_url`, `status` (creating/pending/succeeded/failed), `refund_required`. 503 = unconfigured business rules, so the UI needs an "unavailable" state besides "failed".
- Contract rules to follow: drive logic from error `code`, not message; 401/403/404/409/422/503 semantics; never show CLICK test transactions as real money; never imply SOS reaches emergency responders; token is opaque Bearer.
- Prototype stays **offline with DEMO data** and mirrors these shapes; no network calls to the API were made.

## 7. Update — milestone 2 (read 2026-10-14)
- Backend on `codex/notification-integration` run locally: **200 passed / 0 skipped on PostgreSQL 16** (192 + 8 skipped on SQLite); OpenAPI contract check passes. Earlier §1 claim “no tests run” is superseded.
- Real findings that corrected the prototype: payment is only allowed for `accepted` bookings with an `Idempotency-Key`; combined booking+gift checkout is permanently 503; booking create has five fields; public availability is not exposed. See `docs/02-handoff.md`.
- The prototype now lives on branch `design/prototype` under `design-prototype/`.
