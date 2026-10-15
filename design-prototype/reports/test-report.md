# Test report (final run for this milestone)
Branch `design/prototype` (from `origin/codex/notification-integration`). Environment: Linux sandbox, Python 3.12, Node 22, headless Chromium 153 (via `@sparticuz/chromium` + `puppeteer-core`), PostgreSQL 16. Statuses: PASS / FAIL / BLOCKED / NOT TESTED.

## PASS
| Suite | Result | How |
|---|---|---|
| Backend (existing, untouched) on **PostgreSQL 16** | **200 passed, 0 failed, 0 skipped** | `alembic upgrade head` (14 migrations) on a local disposable DB, `YONDO_TEST_DATABASE_URL` set, `pytest` (65 s) |
| Backend on SQLite (default) | 192 passed, 0 failed, **8 skipped** (all “requires PostgreSQL row locks / concurrent connections”) — the same 8 pass on PostgreSQL | `pytest -rs` |
| OpenAPI contract vs FastAPI | PASS | `python export_openapi.py --check` → “Frontend OpenAPI contract matches FastAPI.” |
| Logic + mock API + **schema contract** (Node) | **28 passed, 0 failed** | `node tests/run.js`: money, estimate, error-by-code, validators (limits from OpenAPI), status actions; mock flow vs backend rules; every mock response validated with Ajv against `docs/openapi-v1.json` schemas (BookingResponse, PaymentResponse, CompanionCard, ProductRead, TestOrderRead, MeetingState, ReviewRead, ProfileResponse, ServiceResponse, AvailabilityResponse, CompanionStatus, ChatMessageResponse, ReportRead, ContactRead, TokenResponse, CartRead, DiscoveryPage, ApplicationResponse) |
| **Real-browser responsive sweep** | **63 assertions passed, 0 failed** | 9 configurations (360, 375, 390, 430, 768, 1024, 1440 + dark at 360 & 1440) × 20 views = **180 view measurements**; 7 checks each: renders real content (not an error page), no horizontal overflow, touch targets ≥44 px, no clipped controls, measured text contrast (computed colours with alpha blending, 4.5:1 / 3:1 large), no control hidden behind fixed bars, **axe-core WCAG 2.0/2.1/2.2 A+AA + best-practice** |
| **Real-browser E2E flows** | **36 passed, 0 failed** (+1 “real fonts loaded”) | login/OTP/roles, search+filters+empty/reset, verified-badge rule, booking validation, availability pre-check, create booking (exact 5 fields, UTC), server conflict recovery, pay-before-accept blocked, **503 ≠ failed**, fees-unconfigured, provider decline → retry → success, combined-gift preview unavailable, meeting too-early / check-in / start / SOS honest copy / end, chat, review (duplicate blocked), cancel, gifts (out-of-stock, delivery-note, test-order flags), companion flow, requests accept, vendor flow, role guard + server 403 codes, offline+retry, skeleton, keyboard (skip link, focus-not-stolen on load, dialog focus/Tab wrap/Esc/restore, inert background), reduced motion (≈0 ms) and spec durations (200/300 ms), 6 standalone screen files, no JS/console errors |
| Component gallery | 5 passed | overflow/targets/clipping/contrast at 360, 360-dark, 768, 1440, 1440-dark |

Measurements were repeated with the **real Inter and Space Grotesk fonts** loaded from local files (the first runs used fallback fonts because Google Fonts is unreachable in the sandbox).

## Harness validity
The measurement harness was proven to detect defects: injected a 500 px element, a 30 px button, a clipped label and low-contrast text → all flagged (overflow 140 px, small target, clip, ratio 2.32). This also exposed that overflow detection was **blind in mobile emulation** until bound to the emulated width; earlier PASS results from that period were discarded and re-run.

## Defects found and fixed in this milestone (each now covered by a test)
1. Prototype paid **before** the companion accepted and put gifts into the booking total — contradicts the backend (`booking_not_payable`; combined checkout always 503). Flow redesigned.
2. Mock `vendor_id` not a UUID (caught by schema validation).
3. Programmatic-focus ring around every page heading.
4. Timeline label “Kutilmoqda” broke mid-word at 360 px (global `overflow-wrap:anywhere`).
5. Initial page load moved focus to the heading, bypassing the skip link (double routing at boot).
6. Fixed bottom nav could hide the focused control → `scroll-padding` (WCAG 2.4.11).
7. Dialog Tab order could escape the modal → explicit focus wrap.
8. Payment-503 “Retry” reloaded the page instead of retrying the payment.
9. Invalid typed date crashed availability form (`Invalid time value`).
10. Chat screen seed hard-coded a day that can be closed; now tries days.
11. axe: skip link outside a landmark; empty-state heading order.

## BLOCKED
- **Git push**: no credentials in the environment (no token, `gh`, or stored credentials). Commit is local only.
- Real payment provider, SMS/OTP provider, push notifications, courier/delivery: not selected/implemented in the backend; cannot be tested.

## NOT TESTED
- Real devices; Safari/iOS WebKit; Firefox; real Android budget-device performance (animations were only checked for spec durations, not frame rate).
- Screen readers (VoiceOver, TalkBack, NVDA). axe-core automated rules cover only part of WCAG.
- Prototype against the **real running API** (it uses the mock; contract shape is validated, behaviour is not). Backend business rules that I could only infer: cancellation windows, refund rules, availability-filter semantics, report target id.
- Human usability testing; native-speaker review of Uzbek copy; trademark/similarity search for the logo.
- Photo upload, WebSocket chat, notifications UI, dispute/no-show (no endpoints).
