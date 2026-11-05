# YONDO: manual gifts + offline CLICK Shop API test

## Operational owner

The project owner/operator personally handles gift preparation and delivery. The
admin account advances test orders through preparing, out_for_delivery and delivered.
This is manual fulfillment, not carrier/vendor dispatch or live order shipment.

The gift catalog still requires vendor-role creation and admin publication approval.
Customer delivery notes are available only to their account and admins. Avoid
collecting exact addresses until privacy rules are approved. Inventory is reserved
at order creation and restored upon pre-dispatch cancellation.

## CLICK: offline simulator, not a real sandbox connection

This is an **offline local simulator** of CLICK Shop API Prepare (action=0) and
Complete (action=1), with legacy signed form callback semantics. It never connects
to CLICK and never moves money. Every response explicitly says real_money_moved=false.
No real CLICK account, merchant secret, cards, invoices, captured payments,
refunds, commissions or payouts are activated.

The official CLICK testing tool and actual merchant test account require provider
onboarding/configuration; public example identifiers are not valid credentials.
Official documentation: https://docs.click.uz/ (Shop API, Prepare/Complete).

The existing real gift checkout and combined gift+booking checkout remain disabled.
Production CLICK integration is a separate, future security review.

## LOCAL test configuration

Provide these locally; DO NOT commit real secrets:

    YONDO_ENVIRONMENT=development
    YONDO_CLICK_TEST_ENABLED=true
    YONDO_CLICK_TEST_SERVICE_ID=726314
    YONDO_CLICK_TEST_SECRET=<new random secret with 32 or more characters>

The service ID 726314 is a fake example from our local tests, not a Click merchant ID.
Do not use real CLICK merchant keys as a local simulator secret.
A development or test environment is mandatory. Test-order and simulator endpoints
are disabled by default, and forbidden in staging/production.

## API test flow

1. Create a gift as vendor via POST /api/v1/gifts/vendor/products, then publish it
   via POST /api/v1/gifts/admin/products/{product_id}/publish (admin only).
2. Add it to a customer cart with PUT /api/v1/gifts/cart/{product_id}.
3. Create an OFFLINE test order as customer:

    POST /api/v1/gifts/test-orders
    Authorization: Bearer <customer token>
    {"delivery_method":"manual_delivery",
     "delivery_note":"Meet at the agreed collection point"}

   Alternative: pickup. Orders include snapshots of item names and prices.
   Status starts as awaiting_test_payment. Payable total and delivery fees are null
   because production price/fees are not approved.

4. Easiest simulator action, admin only:

    POST /api/v1/gifts/click-test/admin/orders/{order_id}/simulate
    Authorization: Bearer <admin token>
    {"result":"success"}

   For a simulated cancellation, use result=cancel. No real money is moved.

5. Advance manual delivery as admin:

    POST /api/v1/admin/gifts/test-orders/{order_id}/status
    {"status":"preparing"}
    {"status":"out_for_delivery"}
    {"status":"delivered"}

   Allowed in that order only. Pre-dispatch cancellation returns stock.
   Delivery does not occur automatically and the app does not contact a courier.

6. List customer orders at GET /api/v1/gifts/test-orders.
   Admin queue: GET /api/v1/admin/gifts/test-orders.

## CLICK-shaped Prepare/Complete protocol (local test mode)

POST /api/v1/gifts/click-test/prepare
POST /api/v1/gifts/click-test/complete

Content-Type: application/x-www-form-urlencoded.
Prepare fields: click_trans_id, service_id, merchant_trans_id (test order UUID),
amount, action=0, error=0, sign_time, sign_string.
Complete adds merchant_prepare_id and uses action=1.

The legacy CLICK signature is MD5 of the concatenation:
click_trans_id + service_id + local_secret + merchant_trans_id + amount +
action + sign_time. For Complete, insert merchant_prepare_id before amount.
The simulator interprets sign_time as UTC in YYYY-MM-DD HH:mm:ss format and
requires 10-minute freshness. Responses include test merchant_prepare_id or
merchant_confirm_id. Duplicate successful requests are idempotent. Bad
signatures, amounts, unknown orders and conflicting transactions fail closed.

The app stores amounts as integer minor units and this offline simulator
converts 100 minor units to one displayed UZS. Exact real merchant semantics
and fiscalization must be verified during Click onboarding.

## Outstanding production blockers

Real CLICK merchant test credentials / approved live integration, accepted delivery
fees and refund rules, genuine fiscalization and settlements, secure handling of
delivery addresses, customer support/on-call, real user-interface testing and beta
release operations remain undone.

## Validation

Regression tests cover test-only gating, signed prepare/complete, replays, amount
tampering, privacy, stock reservation/restoration, manual delivery transitions,
and invalid permissions. Ruff, full tests, migration upgrade/downgrade and
GitHub CI must pass before this development branch is accepted.
