# From public demo to closed beta (and public launch): what to remove, what to keep, and whether a sandbox stays

Scope: Yondo (companion discovery/booking, Uzbekistan, Tashkent first). Research date 2026-10-28. Repo facts were read directly from `D:\Yondo` (links are `file:///` paths). Web facts carry a URL. Items marked "(search summary only)" come from a search result digest; the page itself was not fetched or the fetch did not return the relevant section. Everything under "Inferences" is my judgment, not a sourced fact. Business rules (fee, cancellation, refund, payout, SOS response times, amount limits) are never proposed as values: they are listed as OWNER DECISIONs.

---

## 1. What do successful marketplaces do between demo, closed beta and public launch?

### Takeaway
The recurring pattern is: seed the hard side (supply) in one small, dense slice first, keep test and live environments strictly separate (test users and data are never migrated into live), open to small invited groups in waves, and widen only after the live system has proven itself on a small share of traffic. The sourced evidence is strongest for "supply first, one narrow atomic network" (Chen) and "separate test vs live, private beta in waves" (Sharetribe, Stripe); evidence for exact numeric launch thresholds in marketplaces is thin.

### Cited Findings
- Chen: every network has an "easy side" and a "hard side"; a launch works only if the product solves a real need for the hard side, and for most consumer marketplaces the sequence is "supply, demand, supply, supply, supply". Atomic networks "start small, in a niche, and then expand". — [Andrew Chen, Cold Start Problem](https://andrewchen.com/solve-a-hard-problem-cold-start-problem/)
- Chen's example: in a given Uber market "Power Drivers" are about 20% of supply but create about 60% of trips, i.e. a small slice of supply carries the marketplace. — [Andrew Chen](https://andrewchen.com/solve-a-hard-problem-cold-start-problem/)
- Chen's advice (via a secondary summary): "Your product's first atomic network is probably smaller and more specific than you think." — [Chen summary, productandrew substack](https://productandrew.substack.com/p/product-31) (search summary only)
- Geography is the most common constraint: each new city needs its own critical mass; Uber launched city by city (secondary summary). Counter-example: Thumbtack's founder said they launched all categories and geographies at once and would not have survived otherwise. — [echai.ventures summary](https://echai.ventures/startingup/build-mvp/i-m-a-solo-technical-founder-how-do-i-mvp-a-two-sided-marketplace-when-i-need-both-buyers-and-sellers-before-it-works-at-all) (search summary only; secondary)
- Sharetribe (marketplace platform vendor) recommends a "pre-launch onboarding mode": providers sign up and create listings first (they usually have more incentive to join), customers see only their own profile, you can approve listings before they publish, and you export emails to announce launch. — [Sharetribe help: pre-launch onboarding mode](https://sharetribe.com/help/en/articles/10153415-how-to-set-up-a-pre-launch-onboarding-mode)
- Sharetribe also suggests a private beta: grant viewing rights to small groups of early adopters, gather feedback, repeat before full launch. — [Sharetribe help](https://sharetribe.com/help/en/articles/10153415-how-to-set-up-a-pre-launch-onboarding-mode)
- Sharetribe keeps Test and Live as separate environments: settings are changed in test then copied to live, and "users and listings created in Test or Dev can't be moved to Live". — [Sharetribe help](https://sharetribe.com/help/en/articles/10153415-how-to-set-up-a-pre-launch-onboarding-mode)
- Stripe: sandbox is "an isolated test environment" that does not affect the live integration; live and sandbox "function as similarly as possible"; switching is "mostly a matter of swapping your API keys"; sandbox objects "aren't usable in live mode", which "prevents your test data from being inadvertently used in your production code". — [Stripe go-live checklist](https://docs.stripe.com/get-started/checklist/go-live)
- Stripe go-live items relevant to Yondo: test incomplete, invalid and duplicate data; have someone who is not a developer test it; distinguish a card decline from a backend error in what users see; do not log sensitive data; register production webhooks and handle delayed, duplicate and out-of-order notifications; rotate keys that may have been saved outside the codebase during development and make sure code contains no keys. — [Stripe go-live checklist](https://docs.stripe.com/get-started/checklist/go-live)
- Google SRE: a canary is "a partial and time-limited deployment of a change in a service and its evaluation"; keep the canary population small because impact on the error budget is proportional to exposed traffic (5% canary with 20% errors adds about 1% overall error rate); use early stages with small populations and larger ones as confidence grows; run only one canary at a time; metrics should start from SLIs (error codes and latency are strong for frontends) and must be broken down canary vs control because whole-service metrics hide a canary failure. — [Google SRE Workbook ch.16](https://sre.google/workbook/canarying-releases/)
- Google SRE on isolation: canary and control usually share backends and data stores, so isolation is rarely perfect; a bad canary can harm the control and a healthy canary can look bad because of shared infrastructure. — [Google SRE Workbook ch.16](https://sre.google/workbook/canarying-releases/)
- Feature-toggle taxonomy (Fowler/Hodgson): release toggles are transitional and short-lived; ops toggles (kill switches) change quickly without a release; permissioning toggles expose features to specific users (paying customers, internal testers) and "can last years". Toggles are inventory with a carrying cost: add a removal task when creating a release toggle, set expiry dates, use "time bombs", cap the number of active toggles. The article links Knight Capital's costly failure to poor flag management. — [martinfowler.com Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
- Twelve-Factor: keep development, staging and production as similar as possible; "resists the urge to use different backing services" between environments (e.g. a lightweight local database vs a robust production one causes code that passed in dev to fail in prod). — [12factor.net dev/prod parity](https://12factor.net/dev-prod-parity)
- Yondo's own roadmap already encodes this pattern: Phase 19 Testing ends with a "Closed Beta build"; Phase 20 Closed Beta = 20-50 customers, 10-20 companions, a few vendors, watching booking, UX, safety, cancellation, pricing, behavior; Phase 21 MVP Launch = Tashkent only; Phase 22 metrics = registrations, verified users, active companions, booking requests, conversion, completed bookings, cancellations, reports, repeat bookings, revenue, gift attach rate. — [ROADMAP.md](file:///D:/Yondo/ROADMAP.md)
- Yondo already has an invite-only mechanism for feedback, not for sign-up: `/beta` router ("Invite-only beta feedback; does not activate public services"), `BetaEnrollment` per user, feedback categories bug/usability/safety/pricing/other with 1-5 rating; `require_enrolled` is used only by `GET /beta/me` and `POST /beta/feedback`, so enrollment does not restrict who can register or book. Admin enrollment endpoints exist (`PUT /beta/admin/enrollments/{user_id}`) but the admin console has no UI for them (its own text says it has no interface for gift test orders, vendors, beta access and payment management). — [apps/api beta/router.py](file:///D:/Yondo/apps/api/src/yondo_api/beta/router.py), [apps/web en.ts `admin.dash.unconnectedBody`](file:///D:/Yondo/apps/web/src/i18n/en.ts)

### Inferences
- Yondo's "hard side" is companions (supply) and, additionally, trusted supply (verified, photographed, available). Following Chen and Sharetribe, wave 1 of the beta should onboard and approve companions first (10-15), then invite customers; the roadmap's 20-50 customers : 10-20 companions is a reasonable ceiling, but the first atomic network should be narrower than that (one or two Tashkent districts, 2-3 service types, overlapping availability) so that a customer search returns several bookable companions.
- "Invite-only" is not enforced anywhere in sign-up today. With a real SMS provider and a public URL, anyone could register. A permissioning toggle (allow-list of phone numbers or required `BetaEnrollment` at OTP request/booking) must be built before the beta, and the admin UI for enrollment should be added (currently API only).
- The SRE material argues for a small exposed share and a sequence of waves; in a marketplace the "canary" is a cohort of users, and the matching metrics (booking completion, payment/webhook success, SOS/report handling time, error rate) must be reported per cohort, not just overall.
- A runtime "demo mode" toggle inside the production code would be a long-lived, high-risk toggle (Fowler's carrying-cost argument and the Knight Capital example); separate environments and separate build artifacts are safer than flipping demo behaviour with a flag in the production deployment.

### Gaps
- I did not find primary a16z/NFX/Lenny/First Round essays with concrete beta-to-launch thresholds for marketplaces (search returned secondary summaries). The a16z cold-start essay was not retrievable; Chen's own site was used instead.
- No marketplace post-mortem with data on "how long demo wording stayed" was found; that question has no sourced answer.

---

## 2. How long should a closed beta run, how large, and what defines "ready"?

### Takeaway
General beta-testing guidance says 2-12 weeks with most betas 4-8 weeks, planned by number of learning goals (about one week per goal) and ended by pre-agreed exit criteria, not by the calendar. Marketplace-specific numeric exit thresholds were not found in reliable sources, so the thresholds below are proposals for the owner to set.

### Cited Findings
- Centercode: betas run 2 to 12 weeks, most 4 to 8; plan one week of testing per goal (1.5 weeks per goal if running alone); a small tester pool calls for a longer test; for long feedback periods split into phases with one or two week breaks to reduce burnout and bring in fresh testers. The article gives no formal exit criteria. — [Centercode: how long should my beta test be](https://centercode.com/blog/how-long-should-my-beta-test-be)
- Joel Spolsky: a full beta cycle takes at least eight to ten weeks; avoid new builds more often than every two weeks; restart the clock when a feature is added mid-beta. This is an opinion piece. — [Joel on Software: Beta Test](https://www.joelonsoftware.com/articles/BetaTest.html) (search summary only)
- A tool vendor's playbook suggesting 10-30 participants and ending on exit criteria exists but is a template, not research; not used. — (search result only, not cited)
- Yondo roadmap sizes the beta at 20-50 customers and 10-20 companions plus a few vendors, with the beta result defined as "real feedback". — [ROADMAP.md Phase 20](file:///D:/Yondo/ROADMAP.md)
- Yondo's Phase 19 test list: signup, booking, payment, cancellation, chat, review, report, gift, admin, security, duplicate payment, double booking, timezone, concurrency. — [ROADMAP.md Phase 19](file:///D:/Yondo/ROADMAP.md)
- Existing tested capabilities relevant to readiness: 220 API tests on PostgreSQL including 4 concurrency tests; a DB-level overlap guard (PG exclusion) and booking `expired` status; web e2e 59/59 on the real API with test doubles; hourly jobs for booking expiry and account erasure (`python -m yondo_api.jobs`, systemd timer in `infra/jobs/`, not installed anywhere yet). — [docs/WORKLOG.md S25, S31](file:///D:/Yondo/docs/WORKLOG.md), [infra/jobs](file:///D:/Yondo/infra/jobs/README.md)
- Google SRE's rule of thumb that canary duration must be long enough to be representative and include peak load; for Yondo's low volume this implies the beta must include weekends/evenings when bookings happen. — [Google SRE Workbook ch.16](https://sre.google/workbook/canarying-releases/)

### Inferences
- Proposed beta length: 4 weeks minimum per wave, 6-8 weeks total in two waves (wave 1: 10-15 companions + 10-20 customers; wave 2: up to 20 companions + 50 customers), with a 1-week fix-and-review gap between waves. The roadmap's five observation areas (booking, UX, safety, cancellation, pricing) are about five learning goals, which at ~1 week per goal gives ~5 weeks; with two waves 6-8 weeks fits Centercode's range. Marked as judgment.
- Exit criteria should be written before wave 1 and measured on the live system with real SMS and real money. Proposed criteria (numbers are placeholders for the owner to calibrate, not business rules): (a) a stated number of complete lifecycles request -> accept -> pay -> meet -> review with real payments (suggest a few dozen), (b) zero open safety incidents of high severity and every report and SOS record acknowledged within the SLA the owner defines, (c) 100% payment reconciliation: every Click/Payme transaction matches a booking and every booking in `confirmed` has a transaction, (d) no data-loss or double-booking/double-charge incident, (e) error rate and webhook failure rate within a target, (f) deletion job and expiry job ran on schedule for the whole period, (g) restore from backup tested at least once, (h) the Phase 22 metrics are measured without manual SQL, (i) support requests answered within the SLA the owner defines.
- Because the product has a safety dimension (in-person meetings), exit gating should weight safety readiness over growth metrics: a beta that has good conversion but unmanaged SOS handling is not ready.
- Do not add new features during a wave (Spolsky's "restart the clock"); fixes only.

### Gaps
- No reliable source for marketplace-specific "ready" thresholds (e.g. liquidity, repeat rate) at 20-50 user scale; any such number would be invented. Roadmap Phase 22 lists metrics but not targets (owner decision).
- Joel on Software was not fetched (search digest only).

---

## 3. Should a separate always-on demo/sandbox remain, and how should production data be protected from demo data?

### Takeaway
Yes: keep one separate, clearly bannered sandbox with its own domain, database, secrets and test-mode partner keys. Platform vendors (Stripe, Sharetribe, Click's emulator) all treat test and live as separate worlds and never migrate test data. The current Render + Neon demo is a workable minimal sandbox, but the free tier is unsuitable for production and weak for partner callbacks, so production must be a different deployment.

### Cited Findings
- Stripe and Sharetribe separate test/sandbox from live and do not transfer test objects/users to live (see section 1). — [Stripe](https://docs.stripe.com/get-started/checklist/go-live), [Sharetribe](https://sharetribe.com/help/en/articles/10153415-how-to-set-up-a-pre-launch-onboarding-mode)
- Click (Uzbek payment provider) offers a test emulator for suppliers: the supplier configures the software and runs pre-given scenarios step by step; required fields are Prepare and Complete URLs, service ID, merchant user ID and secret key issued at registration. The page does not describe how to move to production. — [Click docs: Testing](https://docs.click.uz/en/?p=12) (search result summary; the fetch returned only the overview page)
- Click overview: services are paid via CLICK SuperApp, my.click.uz, USSD or a Telegram bot once the provider implements Prepare and Complete requests described in the SHOP API section. — [Click docs overview](https://docs.click.uz/en/)
- Payme Business (Paycom): cashboxes exist as three types (with billing, without billing, on-site); billing and no-billing cashboxes require integration setup; only legal entities (IE, private companies, LLC, JSC, state unitary enterprises, JV, non-profit educational organizations) can use cashboxes; navigation lists a "Sandbox" page (content not retrieved). — [Payme Business docs](https://developer.help.paycom.uz/)
- Render free web services: spin down after 15 minutes of inactivity (about a minute to wake), 750 free instance hours per month per workspace, local filesystem lost on redeploy/restart/spin-down, and Render describes free instances as "not for production applications". Free Postgres: 1 GB, expires 30 days after creation with a 14-day grace period before deletion, no backups. — [Render free tier docs](https://render.com/docs/free)
- Neon Free: 1 GB per project, 100 CU-hours per project per month, autosuspend after 5 minutes (cannot be disabled), 6 hours of history and 1 manual snapshot; Launch: restore window up to 7 days, storage $0.35/GB-month, compute $0.106/CU-hour, scale-to-zero can be disabled; Scale: up to 30 days restore window, $0.222/CU-hour, the only plan with an uptime SLA. The page does not explicitly prohibit production on Free. — [Neon plans](https://neon.com/docs/introduction/plans)
- Yondo demo as built: one container with the real API + web app; doubles for OTP (code on screen), photos (in memory), identity (always verified), payment (DEMO provider, no money, DEMO fee 0), throw-away SQLite or optional persistent PostgreSQL via `YONDO_DEMO_DATABASE_URL`; the demo harness runs the API with `Settings(environment='test', ...)`; in persistent mode every phone number, booking and chat stays in the DB; the README states that anyone can sign in as any phone number because the OTP is on screen, so no real data may be entered. — [infra/deploy/README.md](file:///D:/Yondo/infra/deploy/README.md), [demo_app.py](file:///D:/Yondo/infra/deploy/demo/demo_app.py)
- `render.yaml` deploys branch `design/prototype` on every push on the free plan, service name `yondo-demo`. — [render.yaml](file:///D:/Yondo/render.yaml)
- The production API is already fail-closed on OTP exposure: `development_otp` is returned only when `environment` is `development` or `test`; there is a test `test_production_never_exposes_development_otp`; staging/production refuse to start with a weak OTP pepper; CLICK test mode requires a local environment; gift test orders are disabled outside local environments. — [auth/router.py](file:///D:/Yondo/apps/api/src/yondo_api/auth/router.py), [config.py](file:///D:/Yondo/apps/api/src/yondo_api/config.py), [04-staging-readiness.md](file:///D:/Yondo/design-prototype/docs/04-staging-readiness.md), [tests/test_auth.py](file:///D:/Yondo/apps/api/tests/test_auth.py)
- Yondo's staging doc concludes that no staging environment, URL, test accounts or payment sandbox are documented; it lists what staging needs (approved fee policy, SMS or approved test-login path, payment sandbox). — [design-prototype/docs/04-staging-readiness.md](file:///D:/Yondo/design-prototype/docs/04-staging-readiness.md)
- Fail-closed pattern already used in this repo: if `YONDO_DEMO_ADMIN_PHONE` is unset on a non-loopback bind, the admin gets a random unknown number (S28 found live that the well-known admin number worked on the public demo). — [docs/WORKLOG.md S28](file:///D:/Yondo/docs/WORKLOG.md)

### Inferences
- Benefits of keeping a sandbox: (1) sales/investor/partner demonstrations without real money or SMS cost; (2) tester onboarding and training of moderators/support on realistic data; (3) support reproduction of bugs with synthetic data; (4) Click/Payme integration testing, which needs a stable public HTTPS callback URL (Click's emulator calls your Prepare/Complete URLs; a free instance that sleeps for ~1 minute is a poor target); (5) pre-release regression on a PostgreSQL schema identical to production (Twelve-Factor parity; Yondo's SQLite default skips PG-only tests).
- Costs: small but non-zero: a second paid database/instance if the free tiers are outgrown, duplicate secrets and sandbox accounts to maintain, one more thing to patch and to keep from becoming a data-leak path (the on-screen OTP makes it an open door by design). Paid prices for Render instances were not checked; Neon paid prices above are from its docs.
- Minimal setup that protects production:
  1. Different registrable domain or at least a different host with host-only cookies/tokens (e.g. `demo` on a separate domain), so no browser storage or cookie is shared with production.
  2. Separate database project and credentials; never restore production dumps into the sandbox (use synthetic data); never point the sandbox at production Redis/storage buckets.
  3. Separate secrets (OTP pepper, signing keys, DB URL, webhook HMAC): the demo's secrets are treated as exposed and are never reused in production (Stripe: rotate keys that may have been saved outside the codebase during development).
  4. Sandbox-only partner keys (Click/Payme test, SMS test); production keys exist only in the production host's environment.
  5. A persistent "DEMO / test data / no real money / do not enter personal data" banner on every sandbox page, driven by server-reported environment (not by a build-time string that could ship to production), plus `noindex`.
  6. A production startup guard (the same pattern as the existing OTP-pepper validator): when `environment=production`, refuse to start if any test double is wired (dev OTP, `AlwaysVerified`, in-memory storage, DEMO payment provider, `click_test_enabled`, SQLite URL, empty OTP provider).
  7. Production image built from a separate Dockerfile that does not contain `infra/deploy/demo/` or dev extras (`httpx`, `aiosqlite`), deployed from a tagged release branch with manual approval; the sandbox may keep auto-deploying `design/prototype`.
  8. Optional scheduled reset of the sandbox (weekly) for investor demos; keep persistent mode for the staging role. One instance can serve both roles at first; split when partner callbacks need stability.
- Free tiers are acceptable for the sandbox but not for the production beta: Render Postgres free has no backups and expires after 30 days; Neon Free keeps only 6 hours of history. A beta with real bookings and payments needs at least a tier with a multi-day restore window and a restore drill.

### Gaps
- Click's production onboarding/go-live steps and Payme's sandbox page contents were not retrievable; lead times and contract requirements are unknown. Payme's note that only legal entities can use cashboxes is from the intro page only.
- Render paid-plan pricing and Render regional options were not checked.

---

## 4. Which demo remnants exist in the repo, and what is the right treatment for each?

### Takeaway
Most demo content already lives outside the production API package (`infra/deploy/demo/`), which is the right shape. What remains in the shipped web bundle and legal pages is small and listed below. The treatment rule: anything that fakes SMS, payment, identity, storage or data stays only in the sandbox; anything shipped to production that mentions DEMO or draft must be removed or replaced at the moment real users arrive.

### Cited Findings
Evidence from the repository (greps and reads on 2026-10-28):
- API: `development_otp` appears in `auth/router.py` (conditional on `environment in {'development','test'}`), `auth/schemas.py` (optional field) and tests; the web Login shows a banner only if the server returned `development_otp` (`Login.tsx`), using i18n keys `login.devBefore/devAfter` ("Faqat işlab çiqiş muhitida: kod …"). — [auth/router.py](file:///D:/Yondo/apps/api/src/yondo_api/auth/router.py), [Login.tsx](file:///D:/Yondo/apps/web/src/pages/Login.tsx), [uz.ts](file:///D:/Yondo/apps/web/src/i18n/uz.ts)
- Web bundle: `DemoPay.tsx` + route `demo-pay/:reference` in `App.tsx` + 3 `demoPay.*` groups in each of `uz.ts`, `ru.ts`, `en.ts` ("DEMO" badge, "Confirm payment (DEMO)", "Reject (DEMO)", "This is not a real payment…"); the server endpoints for it exist only in the harness (`demo_payment.py`) and accept only the paying customer. — [App.tsx](file:///D:/Yondo/apps/web/src/App.tsx), [DemoPay.tsx](file:///D:/Yondo/apps/web/src/pages/DemoPay.tsx), [en.ts](file:///D:/Yondo/apps/web/src/i18n/en.ts)
- Legal: `legal.draftBanner` shown on `/terms`, `/privacy` and Settings; `terms.md` line "Xizmat operatori: hali ko‘rsatilmagan"; versions `2026-10-23-draft` in both `apps/web/src/legal/versions.ts` and `apps/api/.../account/legal.py` (a unit test keeps them equal); checklist items 1 (operator name) and 3 (backup retention, job scheduling) OPEN; privacy §10 "fonts" bullet is untrue since fonts were self-hosted (S28), and SMS/payment/identity/storage/push/hosting providers are not yet listed because none is connected. — [pre-publication-checklist.md](file:///D:/Yondo/docs/legal/pre-publication-checklist.md), [versions.ts](file:///D:/Yondo/apps/web/src/legal/versions.ts), [terms.md](file:///D:/Yondo/apps/web/src/legal/terms.md)
- Seed/fixtures: names "DEMO Madina", "DEMO Jasur", "DEMO Sevara", "DEMO: Magic City kafesi", "DEMO shikoyat", a DEMO confirmed booking "DEMO: Yunusobod bog‘i (tasdiqlangan)", DEMO fee `platform_fee_bps: 0` set only when the DEMO payment provider is on — all inside `infra/deploy/demo/demo_app.py`, not in the API package. — [demo_app.py](file:///D:/Yondo/infra/deploy/demo/demo_app.py)
- Test doubles injected by the harness: `AlwaysVerified` identity (`IdentityStatus.VERIFIED`), in-memory storage, on-screen OTP, DEMO payment provider; the API's own default treats unknown/unavailable identity as not verified (`identity_not_verified` blocker; "Unknown/unavailable is never verified"). — [demo_app.py](file:///D:/Yondo/infra/deploy/demo/demo_app.py), [companions/service.py](file:///D:/Yondo/apps/api/src/yondo_api/companions/service.py)
- Env/infra: `YONDO_DEMO_HOST/ADMIN_PHONE/DATABASE_URL/PUBLIC_URL`, `PERSISTENT_MODE`, `demo_seed_state` table, `render.yaml`, `infra/deploy/Dockerfile` (demo image), `apps/web/e2e/server.py` (thin entry to the same harness; the e2e suite depends on the on-screen OTP), `marketing/ad-video/server_video.py` (separate seeds without DEMO prefix for the promo video). — [infra/deploy](file:///D:/Yondo/infra/deploy/README.md), [WORKLOG S31](file:///D:/Yondo/docs/WORKLOG.md)
- Missing integrations (no production implementation): OTP delivery provider (protocol only), object storage (protocol only; photo upload says unavailable), payment provider (protocol; platform fee unset ⇒ 503), identity provider (protocol only; companion cannot become eligible without VERIFIED), realtime chat (needs Redis; web polls every 8 s). No monitoring/error-tracking library (Sentry, Prometheus, OpenTelemetry, StatsD) appears in `apps/api` sources, its `pyproject.toml` or `apps/web/package.json` (grep returned nothing). — [WORKLOG S28-S30](file:///D:/Yondo/docs/WORKLOG.md), [infra/deploy/README.md](file:///D:/Yondo/infra/deploy/README.md)

### Inferences
Treatment table (category -> action):

| # | Remnant | Treatment | When |
|---|---|---|---|
| 1 | On-screen OTP (`development_otp`, Login banner) | Keep code (already gated by environment and tested). Run production with `environment=production` and a real `OtpDeliveryProvider`; add a startup guard that fails if a no-op/console provider is configured in production. Optionally remove the banner strings from the production bundle, or leave (harmless: renders only if server returns a code). | Before beta (blocker) |
| 2 | DEMO payment: `DemoPay.tsx`, `/demo-pay/:reference`, `demoPay.*` keys | Exclude from the production build (build flag or dynamic import behind a flag that is false in production) or delete once the real Click/Payme page flow exists; keep in the sandbox build. Never wire `demo_payment.py` in production. | Before beta (cleanup; low risk because server endpoints are absent) |
| 3 | DEMO fee 0 | Sandbox only. In production leave `YONDO_PLATFORM_FEE_BPS` unset until the owner decides; payments then answer 503 by design. | Owner decision, blocker for paid beta |
| 4 | Seed users/places/bookings labelled DEMO | Stay in `infra/deploy/demo/` only. Production DB starts empty plus a bootstrapped first admin (DB insert per `docs/web-and-admin.md`); real companions come through the existing application -> admin approval flow. Never run the seeder against the production URL (add a guard that refuses a non-demo DB). | Before beta |
| 5 | `AlwaysVerified` identity | Sandbox only. Production needs a real adapter or a documented manual-verification adapter that returns VERIFIED only after an admin check (owner decision). Fail-closed default already exists. | Blocker for companions |
| 6 | In-memory photo storage | Sandbox only. Production needs an S3-compatible adapter (not built); decide where photos are stored. | Blocker for companions |
| 7 | Legal draft banner, "draft" versions, operator "hali ko‘rsatilmagan" | Replace with the real operator and contact, effective date and non-draft versions in `versions.ts` and `legal.py` together; every user re-consents. Remove the draft banner. Fix privacy §10 (fonts) and list SMS/payment/identity/storage/hosting providers and hosting location. | Before beta (blocker; consent is recorded at login) |
| 8 | `YONDO_DEMO_*`, `render.yaml`, demo Dockerfile | Keep for the sandbox; add separate production deploy files; rename the sandbox clearly (`demo`) so nobody mistakes it for production. | With environment split |
| 9 | e2e harness (`apps/web/e2e/server.py`) | Keep in CI; make sure it can never be pointed at production (it relies on the on-screen OTP, which production does not have, so it would fail closed). | Ongoing |
| 10 | Promo-video seeds (`marketing/ad-video`) | Not production; leave. If real people appear in future ads, get their consent (outside this research). | Later |
| 11 | "Beta" wording | Add deliberately (not DEMO): a neutral "Yopiq beta" label in login/help/footer and in Terms; keep until exit criteria are met. | At beta start; remove at public launch |
| 12 | Admin console missing beta-enrollment UI and payment management UI | Build the minimum (enroll/unenroll, list, export feedback) before wave 1. | Before beta |

Rule of thumb for what stays in code: "capabilities the product will really use" (beta enrollment, feedback, support form, account deletion) stay; "fakes" (demo payment, always-verified, in-memory storage, seeds) are physically separated from the production artifact. Never rely on an in-production DEMO flag.

### Gaps
- I did not inspect `ru.ts` and `en.ts` for other hidden demo/test wording beyond the greps (3 `DEMO` hits per locale file, all in `demoPay.*`); no separate scan of `docs/` or `design-prototype/` DEMO usage was done because the prototype is not a deployment target.
- Whether the web production build can be configured to drop `DemoPay` was not tested (inference from the Vite setup only).
- How the companion `verified` flag is set by an admin in production without a provider (is there an admin override?) was not established; only the fail-closed default was confirmed.

---

## 5. External go-live gates: evidence and owner decisions (SMS, payments, identity, data law, hosting, backups, security, safety operations)

### Takeaway
The hard gates for a real-money, real-people beta are: a real OTP channel with abuse controls, a real payment provider with an approved fee/cancellation/refund policy and a legal entity behind the merchant account, a defined way to mark companions "verified", photo storage, production-grade hosting with tested backups, final legal pages, and an operating procedure for SOS and reports. Uzbekistan's personal-data rules changed in 2026 (localization narrowed), which makes foreign hosting possible but adds transfer, biometric and breach-reporting obligations.

### Cited Findings
SMS/OTP and authentication:
- NIST SP 800-63B-4 classifies SMS and phone-delivered codes as "restricted" authenticators because of SS7 interception, SIM swap and number porting; OWASP advises documenting risk acceptance if SMS is the only factor, enforcing per-account rate limits, limiting message volume so attackers cannot exhaust messaging costs, strict limits on verification attempts, short time-to-live, single-use, cryptographically secure random codes, new code on resend, and a migration plan to TOTP/push/WebAuthn. — [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- Twilio guidance against SMS pumping (toll fraud): enable fraud guard, disable countries you do not serve and build allow/block lists from phone country codes, use relaxed limits where real users are expected and stricter ones elsewhere, monitor the ratio of verified to sent OTPs and alert on drops; it states no provider-side solution can guarantee 100% protection (a Twilio fact sheet claims 100% for Fraud Guard: marketing wording, contradicted by its own guide). — [Twilio: preventing toll fraud](https://www.twilio.com/docs/verify/preventing-toll-fraud), [Twilio: preventing messaging fraud](https://www.twilio.com/docs/messaging/guides/preventing-messaging-fraud)
- Alphanumeric sender IDs are typically up to 11 characters and some destination networks require pre-registration; transactional OTP messages benefit from it (Uzbekistan-specific rules not found). — [Twilio error 30018](https://static1.twilio.com/docs/api/errors/30018) (search summary only)
- Uzbek SMS providers Eskiz, PlayMobile, TextUp and Sayqal are wrapped together in a community PHP package; no official Eskiz sender-name or template-moderation documentation was found. — [uzbek/laravel-sms](https://root.packagist.org/packages/uzbek/laravel-sms) (search summary only; community project)
- Yondo OTP today: code expires in 300 s, resend after 60 s (response fields), max 3 failed attempts then 60-second lockout per challenge; the only rate-limit hook with an implementation is a Redis counter keyed per minute for the whole provider (`yondo:otp:provider:{minute}`, "otp_rate_limited" 429 when the global count exceeds a setting), i.e. a global quota, not per phone number or per IP; with the setting at 0 or without Redis a no-op hook is used. The demo has no Redis. — [auth/service.py](file:///D:/Yondo/apps/api/src/yondo_api/auth/service.py), [auth/providers.py](file:///D:/Yondo/apps/api/src/yondo_api/auth/providers.py), [main.py](file:///D:/Yondo/apps/api/src/yondo_api/main.py)

Payments:
- Click requires the supplier to implement SHOP-API Prepare/Complete and has a test emulator (see section 3). Payme Business cashboxes are for legal entities only (see section 3). — [Click docs](https://docs.click.uz/en/), [Payme docs](https://developer.help.paycom.uz/)
- Stripe's go-live list (idempotency/duplicates, webhooks, error handling that separates declines from backend errors, logging without sensitive data) maps directly to Yondo's rules (503 is never "declined", `Idempotency-Key` required). — [Stripe go-live checklist](https://docs.stripe.com/get-started/checklist/go-live)
- Yondo today: payment provider is a protocol; `YONDO_PLATFORM_FEE_BPS` unset ⇒ payments 503; CLICK test mode only in local environments; the owner said he will provide real Click/other keys later. — [04-staging-readiness.md](file:///D:/Yondo/design-prototype/docs/04-staging-readiness.md), [WORKLOG S29](file:///D:/Yondo/docs/WORKLOG.md)

Identity verification:
- MyID (UZINFOCOM) offers facial recognition, liveness and document comparison for banks, payment systems and telecoms; the vendor claims 22+ million users and 300+ connected projects (unverified vendor claims); biometric data are part of the State Personalization Center's information system; no public API reference, sandbox or pricing was found. — [myid.uz](https://myid.uz/en/) (search summary only)
- Third-party Didit describes a PINFL (14-digit personal ID) + liveness selfie matched to the government photo flow for Uzbekistan, with REST API/SDK. — [Didit blog](https://didit.me/de/blog/non-doc-verification-uzbekistan/) (search summary only; vendor marketing)
- Yondo today: identity provider is a protocol (`IdentityStatus`), the harness injects `AlwaysVerified`; a companion cannot meet activation conditions without VERIFIED (`identity_not_verified`). — [companions/service.py](file:///D:/Yondo/apps/api/src/yondo_api/companions/service.py), [demo_app.py](file:///D:/Yondo/infra/deploy/demo/demo_app.py)

Uzbek personal-data law (not legal advice):
- Amendments signed 26 March 2026 narrowed data localization: mandatory domestic storage now applies only to biometric data, genetic data and telecom subscriber data; other personal data may be processed abroad if the destination is on the approved adequate-protection list, or standard contractual clauses / corporate rules / approved international standards apply. — [Kun.uz, Aug 2026](https://kun.uz/en/news/2026/08/04/uzbekistan-approves-49-countries-for-simplified-personal-data-transfers); [Legal500 summary of Law No. 1125, 26 Mar 2026](https://www.legal500.com/developments/thought-leadership/personal-data-compliance-in-uzbekistan/) (search summary only)
- A Cabinet resolution of 29 July 2026 lists 49 countries/territories with adequate protection; the article names the United States, United Kingdom, Canada, Japan, South Korea, Singapore, Russia, Germany, France, Italy, Spain, the Netherlands, Switzerland, Norway, Sweden, Finland, Brazil, Argentina, Israel, New Zealand (only part of the list). Transfers to listed jurisdictions need no notification of the authorized body; a breach during a cross-border transfer must be reported to the competent authority within 24 hours with a follow-up within 72 hours; standard contractual clauses are still to be approved by named bodies. — [Kun.uz](https://kun.uz/en/news/2026/08/04/uzbekistan-approves-49-countries-for-simplified-personal-data-transfers)
- Before 2026: operators had to register personal databases in the State Register (notification via pd.gov.uz, Regulation No. 71 of 8 Feb 2020, 15-day review, free of charge). I could not confirm whether registration survives the 2026 amendments. — [DLA Piper Uzbekistan](https://www.dlapiperdataprotection.com/?c=UZ&t=law), [Gratanet](https://gratanet.com/news/the-procedure-for-registration) (search summaries only; pre-2026)
- Yondo's privacy and deletion design (30-day erasure, consent versions) is already built; backup retention is undefined because no backup infrastructure exists; hosting abroad (Render, Neon) is not mentioned in Privacy §10. — [pre-publication-checklist.md](file:///D:/Yondo/docs/legal/pre-publication-checklist.md)

Hosting and backups: see Render and Neon facts in section 3.

Safety operations:
- Uber's emergency button connects to local emergency services (RapidSOps-based data hand-off in some US cities, private security responders in South Africa) and Uber's support team follows up with a check-in; the sources do not say whether support is staffed 24/7. — [Uber newsroom: emergency button](https://www.uber.com/us/en/newsroom/emergencybutton/) (search summary only)
- Yondo SOS design: a recorded alert for manual review; never claims emergency services, trusted contacts or tracking were notified; 112 and trusted contacts via the user's own phone (`tel:`/`sms:`); location only after a tap and only into the SMS text; the moderator signal is sent only for an active meeting; reports by `booking_id` with the server deriving the counterparty. — [CLAUDE.md sections 4 and 7](file:///D:/Yondo/CLAUDE.md), [WORKLOG S25](file:///D:/Yondo/docs/WORKLOG.md)
- Yondo support is an in-app request form only (no e-mail; response time/hours not defined). — [CLAUDE.md section 7 (S24)](file:///D:/Yondo/CLAUDE.md)
- Account-deletion and booking-expiry jobs need scheduling on the production host (`infra/jobs/`), and the owner said server/deploy work comes last. — [CLAUDE.md section 7 (S25, S26)](file:///D:/Yondo/CLAUDE.md), [infra/jobs](file:///D:/Yondo/infra/jobs/README.md)

### Inferences
- OTP abuse risk is higher once SMS costs money: add per-phone and per-IP/device throttles, resend cooldown enforced server-side, a daily SMS budget cap, a +998 country-code allow-list, and an alert on the verified/sent ratio. The existing global per-minute quota protects spend but also lets one attacker block everyone's login (it is a shared counter); this is an observation from reading the code, not a tested exploit.
- Redis becomes a production dependency (OTP quota; realtime chat later). Plan it with hosting.
- Photos of companions are personal data; plain photos are probably not "biometric" data unless processed for face recognition, but a face-biometric identity provider means biometric data handling: Yondo should store only the verification result/reference, not images or templates, and ask the provider where its data lives (MyID says it is hosted in the UZINFOCOM data center). This is my reading of the 2026 amendments, not legal advice.
- Because foreign hosting is now allowed for ordinary personal data, Render/Neon-type hosting is not blocked by law, but Privacy §10 must disclose providers and location, and the owner should decide whether to host in-country (some Uzbek cloud) vs abroad; breach reporting within 24/72 hours means an incident runbook is needed.
- Payment merchant onboarding probably requires a registered legal entity or individual entrepreneur (Payme says so; Click's requirement unknown), which couples three blockers: operator name in Terms/Privacy, merchant contract, and (probably) SMS sender registration. Start this paperwork first because its lead time is outside the team's control.
- Safety operating procedure is a closed-beta blocker: an "alert for manual review" is only meaningful if someone reviews it in a stated time. Options the owner must choose from (not decided by me): staffed hours with meetings allowed only in those hours, on-call rota with phone escalation, or limiting beta to daytime public-place meetings. The UI wording must match the real coverage and must not imply 24/7 if it is not.
- A reasonable security pass for a payments + PII product: OWASP ASVS-based review of auth (OTP, sessions, admin), authorization (customer never sees companion user id; chat privacy), payments (webhook signature, idempotency, replay), file upload, CORS (policy is an open decision), secrets rotation, dependency scan, admin hardening. I did not fetch ASVS text; this is a recommendation, not a cited finding.
- Monitoring minimum: uptime check on `/health`, error-rate alert, webhook failure alert, job heartbeat for `python -m yondo_api.jobs` (a silently stopped erasure/expiry job is a compliance and booking problem), OTP delivery ratio, backup success alert. Error tracking abroad (e.g. hosted Sentry) is a data-transfer disclosure item; first-party logs avoid it.
- Analytics: Yondo currently has zero external services (fonts self-hosted), which is a privacy asset. Prefer server-side first-party metrics for Phase 22 during beta; add third-party analytics only with consent and a privacy-policy update (public launch).
- PWA/app-store: `apps/mobile` is a stub; the web app works on mobile browsers. For beta, mobile web (optionally "add to home screen") is enough; store submission is a later item (not researched).

### Gaps
- Click production go-live process, Payme sandbox/test cashbox process, Eskiz/PlayMobile sender-ID and template-moderation rules, and MyID API terms were not found; each needs a direct inquiry to the provider.
- The 2026 law: full text of Law No. 1125 and whether database registration (pd.gov.uz) still applies were not verified; the owner said legal review is not required, but this single question is cheap to confirm with the Personalization Agency.
- Whether Uber/Airbnb-style safety lines are staffed 24/7 was not established; no Uzbek-specific benchmark for SOS handling was found.
- OWASP ASVS and Atlassian feature-flag/rollout guidance were not fetched.

---

## 6. Communication to early users (beta wording, expectations, feedback channel, data handling)

### Takeaway
Replace "DEMO" (meaning "fake") with "Yopiq beta" (meaning "real but early") in production, say plainly what is real (real people, real money, recorded SOS alerts, 30-day deletion) and what is not yet there, and give testers a single feedback path that already exists in the product. No sourced research on marketplace beta wording was found, so this section is mostly judgment built on Yondo's existing features.

### Cited Findings
- Sharetribe's private-beta advice (small groups, gather feedback, repeat) and the pre-launch onboarding mode (customers see only their own profile until launch) imply that beta participants are told they are early and invited. — [Sharetribe help](https://sharetribe.com/help/en/articles/10153415-how-to-set-up-a-pre-launch-onboarding-mode)
- Yondo already ships: Help -> "Fikr bildiriş (yopiq beta)" feedback form for enrolled users (category, 1-5 rating, 10-2000 characters), in-app support request form, report-a-problem by booking, SOS dialog with honest wording, account deletion with the 30-day period, versioned consent at login. — [uz.ts help.feedback.*](file:///D:/Yondo/apps/web/src/i18n/uz.ts), [WORKLOG S23-S25](file:///D:/Yondo/docs/WORKLOG.md)
- Owner rules constrain wording: no e-mail contact for now; never claim emergency services, trusted contacts or tracking were notified; never show a 503 as "payment declined"; mark verified only from API `verified: true`; no romantic imagery or wording. — [CLAUDE.md sections 4 and 7](file:///D:/Yondo/CLAUDE.md)

### Inferences
- Labels have different meanings and should not be mixed: DEMO = fake data/no real money/OTP on screen (sandbox only); BETA = real service, limited audience, may change; no label = general availability.
- What to tell early users (content checklist): (1) You are in the Yondo closed beta in Tashkent; features may change and some are missing (for example no mobile app, chat refreshes by polling). (2) Payments are real; state amount limits, fee, cancellation and refund rules only after the owner decides them. (3) Safety: the SOS button records an alert for our team to review and is not a substitute for calling 112; state the real hours/coverage. (4) Verified badge means identity checked by the method the owner adopts; say which. (5) Data: what is collected, where hosted, who the operator is, retention and the 30-day deletion; feedback and chats can be reviewed by moderators for safety. (6) Feedback: in-app form and support request; what response time to expect (owner decision). (7) Your data and bookings will not be reset (a promise that differs from the demo, whose data may vanish); the demo URL is a separate toy.
- Draft banner line (Uzbek in the 2026 alphabet, illustrative, needs native review; add through `apps/web/src/i18n` in uz/ru/en): "Yondo hozir yopiq beta bosqiçida: ilova sinovdan ötmoqda va ba'zi imkoniyatlar özgariş mumkin." Where: login screen, Help, Terms preamble; not in the top bar on every page.
- Demo testers: send them to the sandbox with a clear banner and tell them accounts there are disposable; do not promise their demo bookings will move to production.
- Invite mechanism: personal invitations (phone numbers enrolled by admin) rather than a public sign-up link; a waitlist form can be added later.

### Gaps
- No sourced examples of marketplace beta banners or consent copy; no evidence on how users react to "Beta" labels in Uzbekistan.
- Response-time and hours commitments for support and moderation are undefined by the owner.

---

## 7. Direct answer to the owner's question

### Takeaway
Remove the demo things from production at the moment real users start; do not let them stay "until demo users have used it for some time". Keep the demo as a separate sandbox; time-box the word "Beta", not the word "DEMO".

### Cited Findings
- (answer rests on findings in sections 1-6; no new sources)

### Inferences
1. Demo wording and fakes (on-screen OTP, DEMO payment, DEMO seeds, always-verified, in-memory photos) must not exist in the production environment from the first real SMS or real payment; in a real-money environment a "DEMO" label either misleads users about their money or hides that a feature is fake (Stripe: test objects must not be usable in live; Sharetribe: test users are never moved to live).
2. The current demo does not "end": it becomes the sandbox on its own domain and database with a visible banner; demo users keep playing there, and nothing from it is migrated.
3. Production gets a deliberate "Yopiq beta" label instead, kept for roughly 6-8 weeks (4-8 is the typical range) until pre-agreed exit criteria are met, then removed at public launch in Tashkent.
4. Order: environment split and production guards first, then SMS, payment, identity and storage, then legal pages and safety procedure, then invite 10-15 companions, then customers.

### Gaps
- None beyond those listed in sections 1-5.

---

## 8. Go-live gate checklist (numbered; blocker for closed beta / before public launch / later)

### Takeaway
Items 1-16 block a closed beta with real SMS, real money and real people; 17-26 can follow during the beta but must be done before public launch; 27-33 are later. Tags: [OWNER] = owner decision or action, [BUILD] = engineering, [OPS] = infrastructure/process, [LEGAL] = documents/compliance.

### Cited Findings
- The checklist is a synthesis; its factual basis is in sections 1-6 (Stripe go-live list, OWASP/Twilio OTP guidance, Uzbek 2026 data-law changes, Render/Neon limits, ROADMAP phases 19-22, repo state).

### Inferences
A. BLOCKERS for the closed beta (do in this order)
1. [OWNER][LEGAL] Decide the operator entity (company or individual entrepreneur) and a contact route. It unlocks the payment merchant contract, the operator name in Terms/Privacy and probably the SMS sender registration. Start provider applications (Click and/or Payme, SMS provider, identity provider) now because lead times are unknown.
2. [OWNER] Decide business rules, none invented here: platform fee, delivery fee (if gifts stay), cancellation percentages, refund amounts and timing, payout rules, maximum booking amount during beta, whether gifts/vendors are in or out of the beta (suggest out: booking+gift checkout is always 503 in the product rules and the roadmap's beta text lists vendors only as "a few"). Until decided, payments stay 503 by design.
3. [BUILD][OPS] Split environments: production on its own domain, database, Redis, storage bucket, secrets and deploy pipeline (tagged releases, manual approval); sandbox/staging keeps `design/prototype` auto-deploy. Production Dockerfile without `infra/deploy/demo/` and dev extras.
4. [BUILD] Production startup guard (same pattern as the OTP-pepper validator): with `environment=production` refuse to start if dev OTP, a no-op OTP provider, in-memory storage, `AlwaysVerified`, DEMO payment, `click_test_enabled`, SQLite, or missing fee/payment config for a payments-enabled deployment is detected; seeder refuses non-demo databases. Add a CI test that production boot with demo settings fails.
5. [BUILD][OPS] Real OTP delivery: provider adapter (Eskiz, PlayMobile or similar; sender name/template registration), OTP never in responses or logs in production, per-phone and per-IP throttles, server-enforced resend cooldown, +998 allow-list, daily spend cap, delivery-ratio alert, fallback contact route for users who do not receive SMS.
6. [BUILD][OWNER] Real payment provider adapter behind the `PaymentProvider` interface with the owner's merchant keys in host env vars; run the provider's test scenarios against the sandbox; webhook signature verification, duplicates/out-of-order handling, reconciliation report; 503 handling remains "unavailable", never "declined"; refund procedure defined before the first real payment.
7. [OWNER][BUILD] Companion verification path: a real identity adapter or a documented manual verification performed by an admin that sets VERIFIED; define what the "Verified" badge promises; avoid storing face images/templates in Yondo.
8. [BUILD] Photo storage: S3-compatible adapter, bucket policy, size/type limits, deletion on account erasure; choose location and record it in Privacy.
9. [OPS] Production hosting with managed PostgreSQL 16 (the product's tests and exclusion constraints target PG), Redis, TLS, at least a multi-day restore window (Neon Launch offers up to 7 days; Render free Postgres has no backups) and one tested restore. Backup retention should be no longer than the 30-day deletion promise, or the privacy text must say backups are overwritten on a stated schedule.
10. [OPS] Install and monitor the hourly job (`python -m yondo_api.jobs`: booking expiry and account erasure) on the production host; heartbeat alert if it stops.
11. [LEGAL][OWNER] Final Terms and Privacy: operator name and contact, effective date, non-draft version in both `versions.ts` and `legal.py`, draft banner removed, providers and hosting location listed (fix the fonts bullet), beta status stated, deletion/backup retention stated, breach handling; verify with the Personalization Agency whether database registration is still required under the 2026 amendments.
12. [OWNER][OPS] Safety operating procedure: who reads SOS and report alerts, in what hours, with what response time, escalation to a phone; moderator on-call rota; template messages; a rule for temporarily suspending a user; UI wording matched to real coverage. Support request SLA defined and published.
13. [BUILD] Closed-beta access control: allow-list or `BetaEnrollment` required to request an OTP or to create bookings; admin UI for enrolling users and exporting feedback; city restricted to Tashkent in discovery for beta.
14. [BUILD][OPS] Observability minimum: structured logs without OTP/PII, uptime check, error-rate and webhook-failure alerts, an error tracker (decide hosted vs self-hosted given data-transfer disclosure), a daily check of the Phase 22 core metrics from the database.
15. [BUILD] Remove or isolate production demo remnants: exclude `DemoPay` route and `demoPay.*` strings from the production build, confirm no "DEMO"/"draft" string reaches production pages (grep gate in CI), add the "Yopiq beta" label.
16. [OPS] Dress rehearsal on staging with real PostgreSQL and provider sandbox keys: full lifecycle (signup -> companion approval -> booking -> pay -> meet -> review -> report -> SOS -> deletion), restore drill, first-admin bootstrap, secrets rotation (no secret from the demo is reused), basic security pass on auth, payments webhook, admin, uploads and chat privacy.

B. BEFORE PUBLIC LAUNCH (can run during the beta)
17. [OWNER] Written exit criteria evidence from the beta (section 2) and sign-off; remove the "Beta" label only after two consecutive clean weeks.
18. [BUILD][OPS] Load and concurrency test beyond beta scale (booking races, webhook bursts, OTP bursts); Redis-backed realtime chat if polling proves poor.
19. [OPS] Formal security review against OWASP ASVS Level 1-2 with remediation; dependency and image scanning; CORS policy decided; admin accounts hardened; penetration test if budget allows.
20. [LEGAL][OWNER] Optional external legal review of Terms/Privacy against Uzbek law (owner says not required; recommended once, before leaving beta); consent texts reviewed in uz/ru/en by native speakers.
21. [OWNER][OPS] Moderation and support capacity plan for expected volume; templates; escalation to authorities; incident postmortem process; breach notification runbook (24 h / 72 h for cross-border transfers).
22. [BUILD][OWNER] Analytics with consent, if wanted: consent banner, privacy update; otherwise keep first-party metrics only.
23. [BUILD] Native-speaker review of Uzbek (2026 and 1995 alphabets), Russian and English copy; real-device iOS Safari/Android and screen-reader tests.
24. [OPS] Paid, SLA-backed hosting tier and capacity plan; status page; cost monitoring (SMS spend).
25. [OWNER] Public-launch payment edge cases: chargebacks/disputes process, payout schedule to companions, tax/receipt obligations (owner/legal to define; not researched).
26. [BUILD] Decide about companion vendor/gift flows for public launch (roadmap Phase 21 lists flowers/gifts; product rule says booking+gift checkout is 503); vendor onboarding if kept.

C. LATER
27. [BUILD] Native mobile apps or PWA install flow and store listings (`apps/mobile` is a stub).
28. [BUILD] Realtime chat, push notifications, richer maps (roadmap V2).
29. [OPS] Multi-city rollout (Samarqand, Andijon, etc.) only after Tashkent density criteria are met.
30. [BUILD] Referral/waitlist tooling, A/B experiments (experiment toggles; remove stale toggles on a schedule).
31. [OPS] Uzbek-hosted or multi-region setup if regulators or partners require it; SCC/transfer paperwork once the authorized bodies publish approved clauses.
32. [OWNER] Revisit default Uzbek alphabet around 2027-04-22 (law in force date recorded in the repo) and legal text spelling.
33. [OPS] Retire the sandbox only if replaced by a better staging; otherwise keep indefinitely.

### Gaps
- Items 25 and 31 depend on regulations and provider terms not researched (tax/receipts, payout flows, SCC approval).

---

## 9. Recommended timeline (weeks; W0 = week of 2026-10-28; estimate, assumes a small team and provider approvals that are outside the team's control)

### Takeaway
About 4 weeks to be ready for a first closed-beta wave if provider paperwork starts immediately, 6-8 weeks of beta in two waves, then 3-4 weeks of public-launch preparation: roughly 13-16 weeks from now to a Tashkent public launch, shortened or stretched mainly by Click/Payme and identity-provider onboarding.

### Cited Findings
- Beta length basis: Centercode 2-12 weeks, most 4-8 weeks; one week per goal; phases with 1-2 week breaks. — [Centercode](https://centercode.com/blog/how-long-should-my-beta-test-be)
- Roadmap order: Testing -> Closed Beta -> MVP launch (Tashkent) -> Metrics. — [ROADMAP.md](file:///D:/Yondo/ROADMAP.md)
- The owner decided "Serverni oxirida qilamiz" (server/deploy last), so production hosting work is now the critical path. — [CLAUDE.md section 7 (S26)](file:///D:/Yondo/CLAUDE.md)

### Inferences
- W0 (this week): owner decisions 1-2 and 12 (entity, business rules, SOS/support SLA); submit applications to Click/Payme, SMS provider and identity provider; choose hosting and region; write exit criteria.
- W1-W2: engineering: production guard (4), environment split (3), SMS adapter and throttles (5), photo storage (8), beta access control and admin UI (13), observability (14), remove demo remnants (15). Payment adapter (6) starts as soon as sandbox keys arrive.
- W3: staging dress rehearsal (16): real PostgreSQL, provider sandboxes, restore drill, security pass, final legal documents (11), jobs installed (10), internal dogfood with team and friends under the beta label with test payments.
- W4: Beta wave 1 (go-live gate sign-off): 10-15 approved companions first, then 10-20 customers by personal invitation; daily review; fixes only.
- W5-W7: Wave 1 continues for at least 4 weeks total; mid-point review at end of W6.
- W8: Fix-and-review gap (1 week); decide on wave 2.
- W9-W12: Wave 2: up to 20 companions and 50 customers (roadmap size); weekly metrics; exit criteria evaluated.
- W13-W16: public-launch preparation in parallel from W9: load test (18), security review (19), analytics/consent (22), capacity plan (21); remove "Beta" label after two clean weeks at the end of wave 2; announce Tashkent public launch.
- If payment onboarding slips, run wave 1 as a "limited functionality beta" only if the owner explicitly accepts a booking flow without online payment (not currently implemented; the product rule is that pay-after-accept leads to `confirmed`); otherwise the beta waits for payments.
- Keep the demo sandbox running throughout; announce to demo testers that production beta is separate.

### Gaps
- Provider lead times (Click/Payme merchant approval, SMS sender approval, identity provider contract) are unknown and dominate the schedule; the timeline is an estimate and not sourced.
