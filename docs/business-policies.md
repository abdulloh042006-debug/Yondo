# Business policies: implemented placeholders awaiting approval

`TZ.md` leaves several numbers and rules to the business model ("Aniq foizlar biznes model
tasdiqlangandan keyin belgilanadi"). To make the product testable end to end, each one is
implemented as a **configurable setting with a placeholder default**. None of these values is a
final business decision. Change them with environment variables (see `.env.example`); no code
change is needed.

| Area | Setting (`YONDO_…`) | Placeholder | Where it applies |
| --- | --- | --- | --- |
| Accounts | `ACCOUNT_MIN_AGE` | 18 | Profile completion activates the account only at or above this age |
| Booking | `BOOKING_PLATFORM_FEE_BPS` | 1000 (10%) | Customer pays service + this fee (TZ §26) |
| Booking | `BOOKING_COMPANION_COMMISSION_BPS` | 0 | Deducted from the companion payout |
| Cancellation | `BOOKING_FREE_CANCELLATION_HOURS` | 24 | Full refund if the customer cancels this early |
| Cancellation | `BOOKING_LATE_CANCELLATION_REFUND_BPS` | 5000 (50%) | Refund for later cancellation before start; 0% after start |
| Cancellation | (fixed rule) | 100% | Companion or administrator cancellation refunds the customer in full |
| Booking | `BOOKING_MIN_LEAD_MINUTES` / `BOOKING_MAX_HORIZON_DAYS` | 60 / 60 | Earliest and latest bookable start |
| Booking | `BOOKING_MAX_DURATION_MINUTES` | 480 | Longest single booking |
| Booking | `BOOKING_REQUEST_TTL_MINUTES` | 120 | Companion must answer a request in this time |
| Booking | `BOOKING_PAYMENT_WINDOW_MINUTES` | 60 | Customer must pay after acceptance |
| Meeting | `MEETING_CHECKIN_WINDOW_MINUTES` | 30 | "I'm here" opens this long before start |
| No-show | `MEETING_NO_SHOW_GRACE_MINUTES` | 15 | No-show can be reported after this delay |
| Meeting | `MEETING_AUTO_COMPLETE_HOURS` | 2 | Active meetings nobody ended are completed automatically |
| Payout | `PAYOUT_RELEASE_DELAY_HOURS` | 24 | Hold after completion/delivery before a payout is due |
| Reviews | `REVIEW_WINDOW_DAYS` | 14 | Reviews accepted this long after the meeting |
| Disputes | `DISPUTE_WINDOW_DAYS` | 7 | Disputes accepted this long after the meeting |
| Reviews | `REVIEW_TAGS_FOR_COMPANION` / `_FOR_CUSTOMER` | 5 tags each | Quick-tag taxonomy (TZ §13) |
| Gifts | `GIFT_PLATFORM_FEE_BPS` / `VENDOR_COMMISSION_BPS` | 0 / 0 | Marketplace fee and vendor commission |
| Trust | `NEW_COMPANION_COMPLETED_BOOKINGS` etc. (code constants in `discovery/stats.py`) | New < 3, Trusted ≥ 10 and ★ ≥ 4.5 | Badges "Yangi" / "Ishonchli" (TZ §14) |

## Rule interpretations to confirm

1. **Booking order of steps.** TZ statuses `pending → accepted → confirmed` are implemented as:
   customer sends a request (pending) → companion accepts (accepted) → customer pays within
   the payment window (confirmed). Free (zero-price) services are confirmed on acceptance.
2. **Pricing unit.** A booking lasts a whole number of the service's pricing units
   (`unit_minutes`); no partial-unit rounding is invented.
3. **Late cancellation compensation.** When a customer cancels late, the companion receives the
   non-refunded share of their payout as compensation.
4. **No-show.** A party who checked in may report the other after the grace period; the booking
   becomes `no_show`, a dispute opens automatically and the payout is held until an
   administrator decides refund and payout amounts (TZ §22: "admin yoki avtomatik tizim").
5. **Gift orders on cancellation.** Gift orders the vendor has not started preparing (`new`,
   `accepted`) are cancelled and refunded with the booking; orders already in preparation are
   left for administrator handling.
6. **Who ends a meeting.** The companion starts the meeting after both check-ins; either party may
   end it (so a customer can leave for safety reasons).
7. **Account activation.** Phone OTP + complete profile (name, age, gender, city) + minimum age
   activates the account. ID/selfie verification is required for companions (activation gate)
   and optional for customers (badge).
8. **Suspension/ban.** Suspending or banning a user revokes their sessions and cancels their
   upcoming bookings with full refunds to the other party.
9. **Chat.** Chat is open from the request until the meeting ends; automatic phone/contact
   detection is left to a later phase as TZ §15 states.

## Not decided by code (needs product/legal input)

- Final payment provider (Payme, Click, Uzum, …) and payout method for companions/vendors.
- Terms of Service, Privacy Policy, Community Guidelines and the other TZ §20 documents
  (the app shows short rule summaries and contract snapshots only).
- Allowed currencies and price bounds (Phase 6 settings), photo retention period.
