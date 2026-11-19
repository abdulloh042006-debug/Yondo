# Gifts (Sovg‘alar)

The owner decided on 2026-11-19: "Sovg‘a bo‘limini ham to‘liq qo‘shing". The CEO answered the open business questions the same day. Product decisions §4 (vendors) and CLAUDE.md §4 (gifts) apply.

## Phase A: backend (this PR)

**Vendor application with a mandatory shop profile**
- `PUT /gifts/vendor/shop` applies, or edits, the shop profile: name, description, city and delivery area (free text).
- `POST /gifts/vendor/shop/logo` adds an optional logo. It is a JPEG/PNG/WebP image, re-encoded without EXIF.
- Contact runs only through the app: no phone is stored in the shop.
- `GET /gifts/vendor/shop` returns the status (`pending`, `approved`, `rejected` or `suspended`), the admin's note and whether the ID check is done.
- After a rejection, editing the profile sends the application back to review. An approved shop can edit its profile; an admin can suspend it.

**Admin review**
- `GET /admin/vendors?status=` lists the shops.
- `POST /admin/vendors/{id}/decision {approve|reject, note}` decides an application.
  - Approval needs the existing **ID + selfie verification** to be `verified`. Those images are deleted at the identity decision (retention 0).
  - Approval grants the **Vendor** role. It also reinstates a suspended shop.
- `POST /admin/vendors/{id}/suspend {reason}` suspends a shop.
- Every decision and suspension is audited, and the vendor gets an in-app notice (`vendor_approved`, `vendor_rejected`, `vendor_suspended`).

**Who can sell and what customers see**
- The Vendor role can no longer be self-assigned: `PUT /auth/roles` answers `vendor_requires_approval`.
- Only an approved shop can add products.
- The catalogue shows a product only while its shop is approved: published, in stock, from an active account.

**Product moderation**
- `POST /gifts/admin/products/{id}/reject {note}` hides a product with a reason that the vendor sees. It is audited and the vendor is notified (`gift_product_rejected`).
- Publishing again clears the reason.

**Test orders, one per vendor**
- The test checkout splits a cart into **one order per shop**. `POST /gifts/test-orders` now returns a list.
- A shop sees its own orders (`GET /vendor/orders`):
  - shown: the items, the delivery method and the customer's own delivery note;
  - in place of the customer: **"Mijoz"** and a short number;
  - never shown: the customer's phone, user id or name.
- Status changes:
  - The shop moves its order (`POST /vendor/orders/{id}/status`): paid → preparing → out for delivery → delivered. It may cancel until delivered, with a required reason; stock is restored.
  - The customer may cancel only before the shop starts preparing (`POST /gifts/test-orders/{id}/cancel`).
  - The admin's manual override stays.
- Notices go to the customer for every step. The shop is told about new, paid and cancelled orders.

**Money**
- These are test orders: no money moves, so there is nothing to refund.
- `/vendor/earnings` stays **503 / "Aniqlanmagan"**: no vendor payout rule is defined.
- There is no delivery fee and no commission for gifts. Booking + gift checkout stays 503.

**DEMO**
- One approved "DEMO Sovg‘a do‘koni" with three neutral DEMO products: flowers, a book and a tea set.
- Its ID record is a clearly fake DEMO entry with no image.

## OPEN (owner decision before real orders)
- **How a shop contacts the recipient for a REAL delivery:** an in-app order chat, or a masked phone number. Nothing is built yet.
- Real payments, vendor payouts and a delivery fee for gifts.
- Gifts to companions: not built. Customers never receive a companion's user id.

## Next phases
- **B (web):** the catalogue, cart, test checkout (labelled as a simulation) and order tracking; vendor mode; the admin console.
- **C (mobile):** the customer and vendor flows.
