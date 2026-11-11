# Yondo product decisions (approved by the owner)

**Source:** the owner's message of 2026-11-06, "YONDO — TASDIQLANGAN PRODUCT DECISIONS VA ISH TOPSHIRIG‘I". This file is the **primary source for product decisions**. Where an older decision in CLAUDE.md §7, TZ.md, the WORKLOG or a PR says otherwise, this file wins. Those places are updated to point here.

**Do not ask the owner again** about anything below: commission, retries, roles, mandatory password and its rules, PR #18 Q1–Q7, vendor approval, refunds, settlement. Raise a point only when there is a real security, legal or technical blocker, and then propose the best solution yourself.

## 1. Beta commission and payments

| Decision | Detail |
|---|---|
| Platform commission (beta) | **5%**, **deducted from the companion's side**: net = gross − 5%. The customer is not charged the commission on top. Integer tiyin, half-up rounding as `platform_fee()` does today. **This is a code change**: today `payments/router.py` sets `amount = price + fee` (the customer pays the fee on top) and the payout equals the subtotal (the companion gets 100%). Both must move to "customer pays the service amount, payout = gross − 5%". Setting `YONDO_PLATFORM_FEE_BPS=500` alone is not enough. |
| Taxes | Counted **separately** from the commission. No tax rate is defined yet, so no tax line is invented: a tax line appears only once a rate is configured. |
| Customer checkout | Show, simply and transparently: service price, discounts (if any), additional charges (if any), and the final amount to pay. Lines that do not exist are not shown. |
| Companion finances | Shown separately: **Gross** (service total), **Deductions**, **Commission** (5%), **Net** (what the companion receives). What counts as a deduction has **not** been defined by the owner yet, so it shows 0 until he defines it. |
| Real money | **Off.** Until a real payment integration and its settings are ready, use the payment **simulator / test mode** (the demo payment provider). Turning on real payments, including the manual card-transfer mode of PR #16, needs the owner's **separate** permission. |
| Failed payment | A **retry is allowed**. Each attempt is its own payment attempt or transaction record. Idempotency keys and a database constraint (at most one open or succeeded attempt per booking) prevent a double charge. This replaces the old "one payment per booking" rule (`uq_payment_single_booking`). |

## 2. Mobile app and roles

- **One** mobile app. Do not build a second "Yondo Partner" app.
- Roles in the app: **Customer**, **Companion**, **Vendor**, each with its own interface, navigation and permissions.
- A user sees only the features of their role(s). Permissions are enforced **in the backend**, not only in the UI.
- Admin works in the separate web dashboard (`apps/web/src/admin`).
- The existing backend and one shared database stay.

## 3. Authentication and password

**Ways to sign in:**
- Google sign-in.
- Telegram sign-in (Telegram Login).
- Registration and verification by phone number.

Google and Telegram are separate login providers. Sending OTP codes through Telegram is a separate mechanism.

**OTP:**
- In the demo stage, phone verification codes are sent by a **Telegram bot**. This is a different mechanism from Telegram Login.
- No SMS OTP now, and no paid SMS service. The architecture keeps a provider slot so an SMS provider can be added later (`OtpDeliveryProvider`).
- Codes are single-use, expire, and are stored only as hashes. The current pepper + hash scheme stays.
- **Technical constraint, with the chosen solution:** a Telegram bot cannot message a person by phone number. The person must open the bot first.
  1. The app shows a `t.me/<bot>?start=<one-time nonce>` link.
  2. The bot asks the person to share their contact (Telegram's "share phone number" button).
  3. The bot accepts the contact only when its phone matches the number being verified and the contact belongs to that Telegram user.
  4. It then sends the code. Later codes, such as password resets, go to the stored Telegram chat.
- The existing Telegram Gateway provider stays in the code as a paid option. It is used only with the owner's permission and is not the default in the demo. The development/demo harness may still show the code on screen, but only to fake test accounts and never to real users.

**Password (mandatory):**
- Every account must have a password before it is fully active:
  - after phone OTP verification at registration;
  - on the first Google or Telegram sign-in.
- After that, users sign in with their phone (or another verified login identifier) and password, from any device. They are never forced back through Google or Telegram.
- Rules:
  - 8–128 characters;
  - may not equal the phone number;
  - no forced upper-case, digit or symbol.
- Hashing: Python stdlib **`hashlib.scrypt`**, with a per-password random salt and parameters stored next to the hash. No new dependency. The plain password is never stored or logged.

**Security:**
- 5 wrong attempts lock that account's password login for **15 minutes**.
- Per IP address: **20 attempts per minute**.
- Changing the password signs out all **other** sessions.
- Resetting the password signs out **all** sessions.
- New device: **no** extra OTP for now.
- Forgotten password: reset by OTP. In the demo the code comes from the Telegram bot; an SMS provider can be added later.

## 4. Vendors and verification

- A vendor becomes active **only after admin approval**.
- A **shop profile is mandatory** for a vendor. A companion needs none.
- ID images are **deleted after the review decision** (identity image retention 0).
- The result, the reviewer and the decision time are kept for audit.
- ID images never go to ordinary logs or public storage. Access to them is restricted and audited (admin presigned URLs, audited views).

## 5. Refunds and companion settlement

- **No automatic refunds.** An admin reviews each cancellation or refund.
- An approved refund goes back to the original payment method.
- When the service is done and the booking is completed, the companion's **net = gross − 5% commission** (minus any deductions).
- In the beta an admin may run the settlement.
- Every financial operation is written to the audit log.
- No payout for **cancelled, disputed or refunded** bookings.
- No duplicate settlement or refund for one booking: idempotent operations plus unique constraints.

## 6. PR #18 (password-login plan): Q1–Q7, answered

| Q | Decision |
|---|---|
| Q1 | Password **mandatory**. Phone verification by OTP stays. The password is created at first registration. (This cancels the earlier "password optional" proposal.) |
| Q2 | 8–128 characters. The phone number itself is not allowed. No extra upper-case, digit or symbol rules. |
| Q3 | No extra OTP on a new device for now. |
| Q4 | 5 wrong attempts lead to a 15-minute lock. Per IP: 20 attempts per minute. |
| Q5 | Changing the password closes the other sessions. Resetting it closes all old sessions. |
| Q6 | The TZ.md amendment text in the PR is approved. TZ.md §42 is updated accordingly. |
| Q7 | `hashlib.scrypt` from the Python stdlib. No new dependency. |

## 7. Working rules for the team

1. Check the repository, branches, architecture, code and tests first.
2. Separate what is done from what is not.
3. Continue according to these decisions.
4. Do not stop to ask the owner about technical details you can decide yourself.
5. Run the relevant tests at every step, and write the results into `docs/WORKLOG.md`.
6. Do not break working features.
7. Add no unnecessary dependencies and no paid services.
8. Do not turn on real payment integrations or real payments without the owner's separate permission.
9. Never report unfinished work as done.

## What is already in the code (2026-11-06)

| Area | Status |
|---|---|
| 5% commission | `platform_fee()` exists, but the fee is added to the customer total and the payout is 100% of the subtotal. **To change**: deduct it from the payout. |
| Simulator payments | The demo payment provider (`infra/deploy/demo/demo_payment.py`) exists. |
| Manual card transfers | Built in PR #16, **off** by default; it needs the owner's separate permission. |
| TezCheck | The adapter is on main (`payments/tezcheck.py`). In `auto` mode it is used once a token is set. No live token in the beta (test tokens only, owner S32). |
| One payment per booking | Still enforced (`uq_payment_single_booking`). **To change**: allow retry attempts. |
| ID images deleted at decision | In PR #11 (owner commit `d45eb28`, retention default 0). |
| Admin bootstrap | PR #14 |
| Mobile app (customer flows) | PR #13. Companion and vendor modes still to do. |
| Password login | Plan only (PR #18). Code to do. |
| Telegram-bot OTP, Google login, Telegram Login | To do. |
| Vendor approval and shop profile | To do. Today the admin publishes products one by one. |
| Refund review and settlement records | To do. Today `CompanionPayout` is created at completion, and refund handling is a flag. |
