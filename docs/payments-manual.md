# Manual card-transfer payments (beta)

Owner decision, 2026-11-05: for roughly the first month, with few users, payments are taken without a payment API and without extra cost. The customer transfers the money to the owner's card, and the owner confirms it by hand. When users grow, switch to TezCheck by changing one setting (`docs/payments-tezcheck.md`).

## How it works

1. A booking is `accepted`. The customer presses **Go to payment**. The amount is the booking price plus `YONDO_PLATFORM_FEE_BPS`; no other amount is used.
2. The app opens `/pay/<code>`. This page shows:
   - the configured cards;
   - the exact amount;
   - a code such as `YND-7KQ2-9MX4`, which the customer types into the transfer comment.
   Only that customer sees the cards; everyone else gets "not found". The cards are shown only while the booking is `accepted` and its start time has not passed. Otherwise the page says the payment is no longer open.
3. The customer pays from their own bank app (Uzcard, Humo or Visa). The app moves no money and promises no confirmation time.
4. The admin opens **Admin → Payments**. When the bank shows that exact amount with that code, the admin presses **Money received** and confirms. The booking becomes `confirmed` through the same idempotent path a provider webhook uses. Pressing twice does nothing more, and an admin cannot confirm their own payment. Each confirmation is audited (`manual_payment_received`).
5. If the booking was cancelled before the money was confirmed, or its start time has passed (the confirmation expires it first, as the hourly job would), the payment is marked **refund needed**. The customer's page then says that, never "confirmed". The refund is made by hand. An admin cannot confirm a payment for a booking in which they are the customer or the companion.

No "not received" button exists. A booking that stays unpaid expires at its start time, as before.

## Setup (the owner's step; host environment only, never in the repository, which is public)

```
YONDO_PAYMENT_PROVIDER=manual
YONDO_PUBLIC_WEB_URL=https://<your web domain>
YONDO_MANUAL_PAYMENT_CARDS=[{"label":"Uzcard","number":"<16 digits>","holder":"<Name S.>"},{"label":"Humo","number":"<16 digits>","holder":"<Name S.>"}]
YONDO_PLATFORM_FEE_BPS=<your decision, e.g. 0 for no fee in the beta>
```

The API refuses to start in manual mode without at least one card and an https web URL. Card numbers are shown in groups of four.

## Switching to TezCheck ("one button")

Set the TezCheck keys (`docs/payments-tezcheck.md`), then change `YONDO_PAYMENT_PROVIDER=manual` to `tezcheck` and restart. New payments then go to TezCheck, and manual payments that are still open can still be confirmed in **Admin → Payments**.

## Known limits and risks

- **One payment per booking.** The database rule `uq_payment_single_booking` allows only one payment per booking. A payment cannot be retried with another code: confirm the one that is open.
- **Personal cards.** Receiving business payments on personal cards can hit bank limits or blocks, and has tax and legal questions. This setup is temporary; check it with your bank and accountant.
- **Payouts.** Paying companions is done outside the app. No payout or fee rule is computed beyond `YONDO_PLATFORM_FEE_BPS`.
