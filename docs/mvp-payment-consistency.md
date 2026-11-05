# MVP payment reliability audit

This patch fixes two booking/payment races while **keeping actual financial operations unconfigured**.

- A successfully paid booking that is cancelled is marked `refund_required=True` for manual financial review. It **does not automatically refund money**.
- If a provider responds after the customer has cancelled the booking, its reference is saved for late webhook reconciliation, but the API returns 409 without exposing the checkout URL.
- Payment webhooks lock the booking before the payment, matching the cancellation lock order.
- Regression tests cover both situations.

Still required before real payments: approved cancellation/refund/fee policies, real provider adapters, provider-side session invalidation where supported, payout/dispute workflows and production reconciliation monitoring.

GitHub Actions API quality and PostgreSQL jobs provide validation. No production deployment or real transfers are authorized by this patch.
