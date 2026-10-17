# Decisions D1–D5: implementation status, contract and evidence
Source of decisions: backend/product owner (current requirements). Labels: **REAL** = executed against the real FastAPI backend (SQLite and native PostgreSQL 16); **MOCK** = executed against the in-browser mock (`prototype/src/mockapi.js`), which mirrors the real behaviour but is not the backend; **BLOCKED** = could not be verified.

## D1 Platform fee and delivery fee
**Decision.** Fees are backend-configured and backend-calculated. The frontend displays what the API returns, never calculates or guesses a fee, and keeps delivery separate from the platform fee. Missing/invalid configuration fails safe (503).
**Backend reality (read from source, REAL tests).**
| Setting | Type / valid range | Default | Effect |
|---|---|---|---|
| `YONDO_PLATFORM_FEE_BPS` | integer 0..10000 (basis points), validated at startup (`ge=0, le=10000`); out of range fails settings validation | unset | unset ⇒ fee policy not configured ⇒ payment creation returns **503** (`payment_*`); no fee is computed |
| delivery fee | **no backend setting exists** | — | `delivery_fee_minor` is always `null`; gift+booking checkout is always **503 `combined_checkout_unavailable`** |
Fee rule implemented by the backend: `fee = (subtotal_minor × bps + 5000) // 10000` (integer, round half up); `amount_minor = subtotal_minor + platform_fee_minor`. REAL tests: 0, 1, 9, 10, 11, 50 000, 2^62 values, bps bounds (−1, 0, 10000, 10001, None), payment without policy = 503, payment with a test-fixture bps = exact integer result.
**Contract (as returned today).** `PaymentResponse`: `subtotal_minor`, `platform_fee_minor`, `amount_minor`, `currency`, `status`, `refund_required`. Booking+gift preview (non-empty cart): `checkout_available:false`, `platform_fee_minor:null`, `delivery_fee_minor:null`, `total_minor:null`; empty cart ⇒ 409 `cart_empty`. Platform and delivery fees are separate fields.
**Not invented.** No percentage, minimum, fixed amount or delivery price is defined anywhere in the prototype. A delivery-fee configuration schema must be specified by the backend owner (open item).
**Prototype.** Default state = policy **unconfigured** (payment shows the 503 “sozlamalari hali tayyor emas” state, no fee shown). ⚙ → “DEMO siyosat (soxta, biznes qoida emas)” loads a fixture (1000 bps) only to demonstrate the success path; it is labelled and off by default. The cart subtotal on the gifts page is labelled “taxminiy”.

## D2 Availability = full containment
**Rule.** Eligible iff `available_from <= requested_from AND available_until >= requested_until`.
**Timezone convention.** ISO-8601 instants **with** `Z` or an offset, compared as UTC instants. Naive timestamps are rejected. Both params required together; `until` must be after `from`; otherwise 422 `invalid_discovery_filter`.
**Backend reality (REAL).** Already implemented exactly this way, including excluding companions with a pending/accepted/confirmed/active booking overlapping the interval (half-open: touching boundaries do not conflict). Booking creation also requires containment (`409 availability_not_found`). **No backend change was needed.**
**Tests.** REAL (`tests/backend`): exact, inside, shared start/end, partial overlap before/after, request that contains the window (intersection would wrongly match), disjoint, touching both ends, `+05:00` notation, invalid (reverse, zero-length, one param, naive), booking-conflict exclusion and adjacency, bookings outside/partially outside the window. MOCK + pure logic: same matrix (`tests/run.js`). A general availability window is never treated as a confirmed slot.

## D3 Category label
`romantic` is shown as **“Maxsus kunlar”**. Identifier/API value unchanged (no migration). Applied to the gift list, vendor product form (option value `romantic`, label “Maxsus kunlar”), gallery/docs. Tests: label map, no visible “romantic”, option value preserved (node + Chromium).

## D4 UZS minor unit = integer tiyin (100 tiyin = 1 UZS)
- Frontend uses integers only: `money()` formats via BigInt; `toMinor()` parses typed amounts exactly (≤2 decimals, **no silent rounding**, no floats); `mulUnits()` multiplies exactly and refuses unsafe results; fees are never computed in the frontend.
- Defect found and fixed: the earlier float-based formatter printed int64 max as `…760,08`; it is now exactly `92 233 720 368 547 758,07 soʻm`.
- Limits: JSON numbers above 2^53−1 cannot be represented exactly in JavaScript, so such values are refused/shown as “Aniqlanmagan”. The backend stores 64-bit integers; **recommendation to backend owner:** cap prices or serialise large amounts as strings.
- Tests (node): conversion, 0, 1/5/100 tiyin, invalid (NaN, floats, text, negatives, `1e5`), too many decimals, 0.1+0.2 exactness, int64 max, MAX_SAFE±1, multiply overflow. REAL: `platform_fee` integer cases; `price_minor` 0/1 accepted, −1 and 100.5 and 2^63 rejected (never 5xx).
- No refund or payment operation was introduced. Cancellation percentage / refund amount: **not defined** (owner decision); UI states this and `refund_required` is only a flag.

## D5 `reported_user_id` is a USER id
**Findings (OpenAPI + REAL tests).**
1. The reporter is derived from the access token. A client-supplied `reporter_id` is rejected (`422 extra_forbidden`); reports are attributed to the authenticated user only.
2. `reported_user_id` must be an existing user: profile id ⇒ `404 reported_user_not_found` (block: `404 user_not_found`); own id ⇒ `422 invalid_report`/`invalid_block`; malformed ⇒ 422; no token ⇒ 401. With `booking_id` the target must be the other participant (`422 invalid_report_target`).
3. Public responses expose the companion **profile** id only. `CompanionCard` and `BookingResponse` carry no companion user id (verified: no `user_id` in card; owner user id absent from booking). No documented profile→user mapping exists.
4. Incidental leaks (not a mapping, not relied on): `ChatMessageResponse.sender_id` and `ReviewRead.reviewee_id` contain user ids. Privacy note for the backend owner.
**Prototype behaviour (changed).** It no longer sends a profile id. Customers cannot report/block a companion until a mapping exists (an explanatory dialog replaces the buttons). Companions can report/block a booking's customer using `booking.customer_id` (a real user id) with `booking_id`.
**Options for the backend owner (not implemented):** (A) accept a profile id field and resolve it server-side, (B) expose the counterparty user id to booking participants, (C) allow report/block by `booking_id` and derive the counterparty. Pick one and name the id types distinctly in `openapi-v1.json`.
**Proposed contract text:** `contract/openapi-v1.decisions.overlay.json` (description-only; 20 targets validated against `docs/openapi-v1.json` by `tests/run.js`). It is **not applied to the backend**.

## Mocked vs real
| Check | Backend (REAL) | In-browser mock |
|---|---|---|
| availability matrix, ID-type matrix, fee policy 503, integer fee, price limits | `tests/backend/test_decisions_contract.py` (50 tests, SQLite + PostgreSQL 16) | `tests/run.js` |
| payment provider, SMS, courier, refunds | not configured in the backend; simulated in the mock only | simulated |
| UI behaviour | — | Chromium (E2E + sweep) |
