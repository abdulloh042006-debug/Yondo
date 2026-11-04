# Yondo Panel (admin + vendor)

React + TypeScript (Vite) web panel for administrators (TZ §38–§39, ROADMAP Phase 14) and
vendors (TZ §30, ROADMAP Phase 17). Sign-in uses the same phone OTP as the mobile app; the
sidebar shows the sections allowed by the account's roles.

## Run locally (Windows PowerShell or POSIX shell)

```text
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000
```

Start the API first (see `docs/development.md`). To point the dev proxy at another API, set
`YONDO_API_ORIGIN` (PowerShell: `$env:YONDO_API_ORIGIN="http://host:8000"`).

For a separately hosted panel set `VITE_API_URL` at build time and add the panel origin to the
API's `YONDO_CORS_ALLOW_ORIGINS` (JSON array).

## Checks

```text
npm run typecheck
npm test
npm run build      # outputs dist/ (static files)
```

## Sections

- Admin: dashboard (MVP metrics), users and moderation, companion application/content queues,
  ID/selfie verification, bookings, payments/refunds/payouts, reports, disputes, reviews, SOS,
  vendors, products, gift orders and the audit log.
- Vendor: shop profile/application, products with images and stock, order status flow,
  earnings and ratings.

The first administrator is created with `python -m yondo_api.cli grant-admin <phone>` after
that person has signed in once.
