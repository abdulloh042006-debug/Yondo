# ADR 0002: Marketplace MVP architecture (Phases 7–18)

- Status: Accepted
- Date: 2026-11-04

## Decisions

- **Modular monolith continues.** New domains live beside `companions`: `discovery`,
  `bookings` (+ `meeting`), `payments`, `chat`, `reviews`, `safety`, `gifts`, `notifications`,
  `admin`. Shared helpers are in `core`; router registration and integration defaults in
  `wiring.py`.
- **Canonical public gate.** Discovery uses `public_profile_conditions()` (SQL form of the Phase 6
  gates) plus the identity adapter. Identity comes from Trust & Safety verification records
  (`DatabaseIdentityEligibility`), replacing the always-unknown default.
- **Double booking** is prevented twice: row locks on both users (sorted order) and PostgreSQL
  exclusion constraints over `tstzrange(starts_at, ends_at)` for held statuses
  (`accepted`, `confirmed`, `active`), per companion and per customer.
- **Booking contract** is an immutable JSON snapshot (parties, service, time, place, price,
  cancellation policy, rules) accepted by the customer at request and the companion at accept.
- **Payments** are provider-agnostic (`PaymentProvider`). A local-only sandbox provider with
  HMAC-signed webhooks enables end-to-end testing. Idempotency keys, one live payment per
  booking (partial unique index), webhook event de-duplication, amount verification and
  automatic refunds of late/duplicate money protect against double charging.
- **Outbox pattern** for side effects: refunds and push notifications are rows processed by the
  worker; realtime events are published only after commit.
- **Realtime** uses one authenticated WebSocket per user with Redis pub/sub fan-out (in-memory in
  tests); credentials are sent in the first message, not the URL.
- **Money** is integer minor units everywhere, fees in basis points with integer half-up
  rounding.
- **Policies are configuration.** Every unapproved business number is a setting with a
  placeholder default (`docs/business-policies.md`).
- **Clients**: a Vite/React admin+vendor panel and an Expo mobile app with a dependency-light
  in-house navigation, both talking only to the public API.

## Consequences

The product works end to end in development with sandbox integrations. Production requires
real SMS, payment, payout and push providers (see `docs/deployment.md`); they plug into the
existing protocols without changes to domain logic.
