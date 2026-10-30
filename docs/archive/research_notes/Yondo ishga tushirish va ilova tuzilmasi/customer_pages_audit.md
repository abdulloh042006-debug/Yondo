# Yondo customer-facing pages: UX audit against comparable products, with owner questions

Scope: code-read audit of `apps/web` (React/TS/Vite) as of 2026-10-28, branch `design/prototype` (HEAD `efb9f3a`). No live browser walk-through, no real-device test, no measured layout: everything under "Today (code)" is read from source. TZ.md is the functional source of truth. Business rules (fees, cancellation %, refunds, payouts, response windows) are NOT invented here: they appear only as owner decisions.

Label convention used in the Inferences section: **[S#]** = claim backed by a cited source in the Cited Findings lists; **[K]** = general product knowledge about a comparable product that I did NOT re-verify in this session (treat as hypothesis, not citation); **[I]** = my inference from the code.

---

## Q1. What do comparable products and the Uzbekistan context say that is relevant to Yondo's customer screens?

### Takeaway
Marketplace UX evidence points to: ask for login only when the user commits (Yondo already does), show applied filters and filters for the attributes shown on cards, show cancellation terms and response windows before the user commits (Airbnb, TaskRabbit, Booksy all do), and give safety tools server-side reach (Uber/Yango share trips with trusted contacts; Rover has a 24/7 Trust and Safety team). Context: Uzbekistan is mobile-first (92% of population has a mobile connection), Telegram is the dominant messenger, and the payments market is led by Paynet/Payme/Click, so SMS-only OTP and in-app-only notifications are the weakest links for Yondo.

### Cited Findings
- Baymard's 2025 mobile product-list benchmark rates 78% of mobile e-commerce sites "poor" to "mediocre" (58% on desktop); typical mobile failures are repeated trips between the list and a separate filter UI, overlong filter lists, and interfaces that obscure which filters are active (figures as reported in search summaries of Baymard pages; a secondary WisePim post repeats 78%) — [Baymard mobile filtering benchmark](https://baymard.com/mcommerce-usability/benchmark/mobile-page-types/filtering-options), [Baymard: current state of product list and filtering](https://baymard.com/research-articles/current-state-product-list-and-filtering)
- Baymard: 28% of benchmarked sites show no overview of applied filters (a Baymard blog index says 32%, so the exact number is unclear) — [Baymard: how to design applied filters](https://baymard.com/research-articles/how-to-design-applied-filters)
- Baymard: 38% of e-commerce sites lack filters for all attributes displayed in list items; users who see an attribute in the list often want to filter by it — [Baymard: have filters for list-item info](https://baymard.com/research-articles/have-filters-for-list-item-info)
- NN/g: login walls annoy users more than most other problems in usability tests; users often delete an app rather than register; do not put a login wall on first access, require login when the user commits (NN/g contrasts oDesk with TaskRabbit); typing credentials on mobile is tedious — [NN/g Login Walls](https://www.nngroup.com/articles/login-walls/)
- Airbnb: for homes without Instant Book the host has 24 hours to accept or decline a request to book — [Airbnb Help 88](https://www.airbnb.com/help/article/88); per Airbnb help pages (seen in search snippets of regional copies) a guest is not charged if the host declines or lets the request expire, and the dates are free to book elsewhere — [Airbnb Help 3702](https://www.airbnb.com/help/article/3702)
- TaskRabbit cancellation policy: a client can cancel any time, but a fee applies within 24 hours of the scheduled time or on a no-show (greatest of 1 hour at the Tasker's rate plus fees, or a task-type minimum); no fee if cancelled within 5 minutes of booking or if the Tasker does not show; fees are visible in Transaction History / Payments tab — [TaskRabbit cancellation policy](https://support.taskrabbit.com/hc/articles/360035010972)
- TaskRabbit: if a Tasker cancels, the client can rebook and find a new Tasker (search summary of the help article) — [TaskRabbit: My Tasker canceled](https://support.taskrabbit.com/hc/en-us/articles/360036115891)
- TaskRabbit own page: choose task and location, compare Taskers by rate, skills and reviews, book through chat, pay in the app after the task, book up to 14 days ahead; a third-party review claims a one-hour deposit at booking, which conflicts with TaskRabbit's own wording (verify in app before relying on either) — [TaskRabbit how it works](https://www.taskrabbit.com/how-it-works), [Clark.com review](https://clark.com/save-money/taskrabbit-review/)
- Booksy lets each business choose which services need a deposit or cancellation fee, the percentage, and the notice window for free cancel/reschedule; deposits are taken at booking — [Booksy No-Show Protection](https://biz.booksy.com/en-us/features/no-show-protection)
- Rover: all reviews come from people who completed a booking; sitters pass third-party identity verification; "Rover Guarantee" and "Booking Protection" (help finding a new sitter after a last-minute cancel); 24/7 Trust and Safety support; block and report for everyone (regional wording differs) — [Rover safety](https://www.rover.com/safety)
- Uber Safety: up to five Trusted Contacts, option to share trip data, in-app emergency button to call police — [Uber safety measures](https://www.uber.com/gb/en/blog/uber-safety-measures/); Yango (a ride-hailing brand, not confirmed to equal Yandex Go) describes a Safety Center with SOS to local authorities, Share Route and up to three trusted contacts, sharing automatic or manual — [ProPakistani on Yango](https://propakistani.pk/2024/06/27/yango-celebrates-pakistan-safety-awareness-month-through-its-latest-campaign/)
- Yandex Go in Uzbekistan: passenger/driver insurance applies to all Yandex Go rides since 2023 and support is reachable in-app; I found no source for trusted-contact or SOS features in the Uzbek version — [Afisha.uz](https://www.afisha.uz/ru/gorod/2023/04/11/yandex-go)
- Wolt Drive customers automatically receive a live tracking link with courier location and ETA (merchant documentation) — [Wolt Drive web](https://merchant.wolt.com/hr/hrv/learning-center/wolt-drive-web)
- Preply: a trial lesson with a refund or replacement teacher if the user is unhappy (2021 review, dated) — [TopTenReviews](https://www.toptenreviews.com/preply-review); Superprof: first lesson "often free, set by the tutor" and a paid Student Pass to contact tutors (comparison-site claim) — [Superprof comparison](https://www.superprof.com/blog/superprof-preply-tutoring-platforms/)
- Empty states: pair the explanation with one primary next action and keep copy short (one-line headline, description of three lines or less) — [Carbon empty-states pattern](https://carbondesignsystem.com/patterns/empty-states-pattern/), [SAP Fiori empty states](https://www.sap.com/design-system/fiori-design-web/v1-120/foundations/best-practices/global-patterns/designing-for-empty-states), [NN/g video on empty states](https://www.nngroup.com/videos/empty-states-in-application-design-guidelines/)
- OTP forms: `autocomplete="one-time-code"` helps on Safari/iOS only; Chrome on Android needs the WebOTP API and an SMS ending with the site's domain prefixed `@` and the code prefixed `#` — [web.dev SMS OTP form](https://web.dev/articles/sms-otp-form)
- Telegram Gateway: verification codes sent through Telegram at a listed $0.01 per code ("up to 50x cheaper than SMS"), refunded if undelivered within the TTL, prices may vary by country and change without notice — [Telegram Gateway](https://core.telegram.org/gateway), [Gateway ToS](https://telegram.org/tos/gateway)
- WCAG 2.2 SC 2.5.8: pointer targets at least 24 by 24 CSS px (spacing exception) — [W3C Understanding 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html); Google recommends at least 48dp touch targets with 8dp spacing — [Android touch target size](https://support.google.com/accessibility/android/answer/7101858)
- Uzbekistan, early 2025: population 36.7M; 32.7M internet users (89%); 33.9M mobile connections (92.2% of population); median mobile download 37.82 Mbps; 50.7% urban — [DataReportal Digital 2025: Uzbekistan](https://datareportal.com/reports/digital-2025-uzbekistan); the national statistics committee reports 99.3% of people aged 10+ used a mobile phone in 2025 (different base) — [stat.uz](https://stat.uz/en/press-center/news-of-committee/68714-zbekistonliklarning-99-3-foizi-telefondan-fojdalanadi-4)
- Telegram: 76% reach (UzDaily headline) and 70% of Uzbek respondents prefer Telegram as messenger (CA Barometer survey); both seen only as search snippets — [UzDaily](https://www.uzdaily.uz/en/telegram-76-reach-youtube-no-1-e-commerce-on-the-rise-inside-uzbekistans-digital-landscape/), [CA Barometer](https://ca-barometer.org/en/publications/which-messaging-apps-are-popular-in-uzbekistan-kyrgyzstan-and-kazakhstan)
- Payments: Kun.uz (May 2026) ranks Paynet first by Q1 2026 net revenue (558.5bn UZS), then Payme (230.1bn) and Click (209.4bn); Paynet acquired Humo; ~90% of revenue is transaction commissions; the article gives no user counts — [Kun.uz](https://kun.uz/en/news/2026/05/19/how-do-people-in-uzbekistan-pay-and-who-leads-the-market); a vendor guide (commercial source) names Payme and Click as the essential wallets and Uzcard/Humo as core domestic cards — [CartDNA Uzbekistan guide](https://cartdna.com/nl-nl/shopify-payment-guide/asia-central/uzbekistan)
- Repo facts used throughout: notifications are an in-app inbox only, no push/SMS/e-mail, scheduled meeting reminders not built, "real CLICK merchant sandbox" and live checkout not completed — [docs/frontend-api-integration.md](file:///D:/Yondo/docs/frontend-api-integration.md); identity verification is `UnconfiguredIdentityEligibility` in production wiring, so companions stay non-public until a real provider exists — [docs/web-and-admin.md](file:///D:/Yondo/docs/web-and-admin.md)

### Inferences
- [I] Yondo's anonymous browsing plus login at "Book" matches NN/g; the weak spots are after login (blind time entry, no external notifications, tokens in `sessionStorage`).
- [I] Because Paynet leads by revenue and Click/Payme follow, "Click and Payme" is a reasonable but not proven shortlist; the repo already models CLICK (test mode), which is the pragmatic first provider.
- [I] The cancellation/response/payment-hold windows are the single biggest block of missing policy; the comparables show two models: platform-set (TaskRabbit) and provider-set (Booksy). Yondo has to pick one (owner).

### Gaps
- Android vs iOS share in Uzbekistan: not found (DataReportal page has no device data). "Often low-end Android" in the brief is unverified by me.
- Could not verify that 112 is the operative single emergency number in Uzbekistan (search quota ended before the check). The repo copy asserts it ("the single emergency number"); owner/ops should confirm.
- Yandex Go (Uzbekistan) trusted-contact/SOS features: not confirmed; Yango results are a different brand.
- Thumbtack, Glovo, Meetup, Superprof/Preply flow details: not researched with sources; any statement about them below is tagged [K].
- Airbnb "guest not charged" line comes from regional help copies seen in search snippets; I fetched only article 88 directly, which states only the 24 h window.
- Baymard percentages come from search summaries of Baymard article pages, not the paywalled full text.
- Real SMS deliverability to Ucell/Beeline/Mobiuz/UzMobile and Telegram Gateway price for +998: not found.

---

## Q2. Page-by-page audit of the customer-facing pages

### Takeaway
The pages are functionally complete for a demo and honest about payment/SOS limits, but the customer journey has seven structural weaknesses: (1) booking time is entered blind (no availability shown, no time filter although the API supports one); (2) nothing outside the app tells the customer that a companion accepted, so the accept-to-pay loop depends on the user returning; (3) bookings do not show who the companion is; (4) the booking page shows six stacked sections regardless of state; (5) policy text says "not defined yet" in FAQ, cancel dialog and support page; (6) glass blur plus animated background plus motion has no low-power fallback for low-end Android; (7) tokens live in `sessionStorage`.

### Cited Findings
Code facts (repo files; line numbers omitted because the files are short):
- Discovery has filters `q, city, service_code, language, rating_min, price_max`; no time filter, no sort, no result count — [Discovery.tsx](file:///D:/Yondo/apps/web/src/pages/Discovery.tsx). The generated API schema has `available_from` / `available_until` query params on discovery — [schema.d.ts](file:///D:/Yondo/apps/web/src/api/schema.d.ts). Profile copy tells users "To see free times, filter by time on the discover page" — [uz/en i18n `profile.availabilityNote`](file:///D:/Yondo/apps/web/src/i18n/en.ts), so the copy promises a control that does not exist.
- The Discovery "Language" filter label reuses `settings.language` (the UI-language label) and is free text with placeholder "uz, ru, en"; City is free text with a hard-coded "Toshkent" placeholder — [Discovery.tsx](file:///D:/Yondo/apps/web/src/pages/Discovery.tsx).
- Each card photo triggers its own `GET .../photos/{id}/download` request for a signed URL (cached in a module Map) — [companionParts.tsx](file:///D:/Yondo/apps/web/src/pages/companionParts.tsx). The heart renders only for signed-in customers (`HeartButton` returns null otherwise).
- Profile shows rating and review count but no review texts, no completed-meetings count, no availability, no report entry; the headline line is `age · city · gender` — [Profile.tsx](file:///D:/Yondo/apps/web/src/pages/Profile.tsx). TZ section 8 lists reviews, completed bookings, availability and Report on the profile — [TZ.md](file:///D:/Yondo/TZ.md).
- Booking dialog: service, free `datetime-local`, duration 1-4 units, free-text place (min 3 chars), "estimated price" banner; start is sent as `+05:00` instant; on success a toast then navigation to `/bookings` — [Profile.tsx](file:///D:/Yondo/apps/web/src/pages/Profile.tsx). TZ section 9 describes Extras, Gift, Summary, Rules, Payment steps — [TZ.md](file:///D:/Yondo/TZ.md).
- `BookingResponse` carries `profile_id`, `service_code`, `service_description`, price, times, status, but no companion name or photo — [schema.d.ts](file:///D:/Yondo/apps/web/src/api/schema.d.ts); the Bookings and BookingDetail pages therefore never show who the companion is — [Bookings.tsx](file:///D:/Yondo/apps/web/src/pages/Bookings.tsx), [BookingDetail.tsx](file:///D:/Yondo/apps/web/src/pages/BookingDetail.tsx).
- Bookings card actions: Accept/Decline (companion), Cancel, Details, Report, Block/Unblock, SOS (confirmed/active); cancel/decline send `reason: ''`; list capped at 50; no Upcoming/Past split; no "Book again" anywhere in `src` (TZ section 35 requires it) — [Bookings.tsx](file:///D:/Yondo/apps/web/src/pages/Bookings.tsx).
- BookingStatus has no distinct "declined"; a decline can only be told apart through the `booking_declined` notification kind — [labels.ts](file:///D:/Yondo/apps/web/src/lib/labels.ts), [Notifications.tsx](file:///D:/Yondo/apps/web/src/pages/Notifications.tsx).
- BookingDetail renders Payment, Meeting, Chat, Review and Safety sections for every status; chat polls every 8 s; payments are re-fetched only when `booking.id`/`status` change (no polling after returning from a provider); idempotency key kept in `sessionStorage` — [BookingDetail.tsx](file:///D:/Yondo/apps/web/src/pages/BookingDetail.tsx).
- Notifications show only a kind label and time; gift notices have no link; the unread badge exists only inside the Account menu, the bottom dock has no Notifications entry — [Notifications.tsx](file:///D:/Yondo/apps/web/src/pages/Notifications.tsx), [Account.tsx](file:///D:/Yondo/apps/web/src/pages/Account.tsx), [Layout.tsx](file:///D:/Yondo/apps/web/src/ui/Layout.tsx).
- Tokens live in `sessionStorage` ("cleared with the tab") — [client.ts](file:///D:/Yondo/apps/web/src/api/client.ts), [README](file:///D:/Yondo/apps/web/README.md).
- FAQ/support/cancel copy: "No payment provider is connected yet ... fees and refund rules are not defined yet", "Cancellation terms and refund amounts are not defined yet", "Response time and working hours are not defined yet" — [en.ts](file:///D:/Yondo/apps/web/src/i18n/en.ts). Payment 503 copies: `payment_provider_unavailable`, `payment_configuration_unavailable` ("service fee is not configured") — same file.
- Terms/Privacy are Uzbek-only Markdown with a "Draft: not in force yet" banner and "service operator: not yet indicated"; Terms section 6 says provider not connected and fee/cancel terms not defined — [terms.md](file:///D:/Yondo/apps/web/src/legal/terms.md), [LegalPage.tsx](file:///D:/Yondo/apps/web/src/legal/LegalPage.tsx). TZ section 20 lists ten documents (cancellation, refund, no-show, payment terms, community guidelines, prohibited services, ...) — [TZ.md](file:///D:/Yondo/TZ.md).
- SOS text to trusted contacts is only "I need help (Yondo SOS)" plus optional coordinates; no place/time of the booking — [Sos.tsx](file:///D:/Yondo/apps/web/src/ui/Sos.tsx).
- Settings offers 5 themes (Yondo day, Yondo night, Gul, Jurnal, Stone) — [theme.tsx](file:///D:/Yondo/apps/web/src/ui/theme.tsx). `styles.css` has 9 lines with `backdrop-filter` and an animated "aurora" background; a grep found no `deviceMemory`, `Save-Data` or `hardwareConcurrency` fallback in `src` — [styles.css](file:///D:/Yondo/apps/web/src/styles.css).
- `index.html` has viewport, theme-color and description only: no `og:*` tags and no web app manifest; `public/` has icons only — [index.html](file:///D:/Yondo/apps/web/index.html).
- Touch targets in CSS: `.btn` 48 px, `.btn.sm` 44, `.chip` 44, dock links 52, heart 44 wide — [styles.css](file:///D:/Yondo/apps/web/src/styles.css); this clears WCAG 2.5.8's 24 px floor and is slightly under Google's 48dp suggestion for the 44 px items.

### Inferences

#### P1. Discovery (home, search, chips, filters, cards)
1. Today (code): hero (tag, H1, lead, search box) then an always-open filter panel (11 service chips, free-text City and Language, max price, rating select, applied-filter chips, "Clear all"), then a 12-per-page grid with "Show more", skeletons and empty/error states. URL-synced filters. Cards: photo, verified tag (API `verified:true` only), name+age, rating (only if reviews exist), city, up to 3 service tags, "from X / N min". No home rails, no sort, no time filter.
2. Comparables: Airbnb collapses filters into one sheet with a live result count on the button and shows the heart to guests [K]. TaskRabbit starts from task + location, then compares Taskers by rate, skills, reviews [S TaskRabbit how-it-works]. Baymard: show applied filters, filter by every attribute shown on the card, avoid back-and-forth to a separate filter UI [S Baymard].
3. Must-have: (a) on phones collapse filters into a "Filters (n)" sheet with "Show N results"; (b) a "when" filter (today / tomorrow / weekend / pick time) using the existing `available_from/until`; (c) sort (rating, price, newest); (d) language as multi-select chips (uz/ru/en), city as a list (start with Tashkent), not free text; (e) show languages on the card (language is a filter, Baymard 38% finding); (f) result count; (g) empty state that offers the single most useful relaxation.
4. Nice-to-have: TZ section 6 rails (Available today, Top rated, New) once supply exists; recently viewed; saved search.
5. Excessive/confusing: four stacked hero elements before the first card [I]; rating options "2+" (almost nobody filters by 2 stars) [I]; the Language label is the same string as the UI-language setting, so "Language" is ambiguous; 11 chips including "Custom experience" and "Online call" wrapping across rows [I]; hard-coded placeholders ("Toshkent", "200 000") are not translated.
6. Risks (Uzbekistan): cold start: with identity verification unconfigured in production, the likely first-visit state is "No companions are visible yet ... after the application, content and identity checks" (exposes internal pipeline) [I from docs/web-and-admin.md]. Free-text language: a Russian speaker typing "русский" likely gets zero results [I; test]. One signed-photo request per card = 12+ extra requests per page on weak mobile networks [I]. Filter panel likely pushes the first card below the fold at 360 px [I; measure]. No gender/age on cards is fine for "not dating" positioning.
7. Owner questions (recommended answer in brackets):
   - Q1.1 Is a date/time filter needed on the first screen? [Yes: booking is time-bound and the API already supports it; use Today/Tomorrow/Weekend chips.]
   - Q1.2 Is gender a public filter (TZ section 7 lists it)? [No at launch: it is the strongest dating-app signal and invites discrimination; revisit with safety data (e.g., women customers asking for women companions) as an opt-in filter.]
   - Q1.3 Fixed launch city list instead of free text? [Yes, Tashkent first; add cities as supply appears.]
   - Q1.4 Home rails (Top rated/New/Popular)? [No at launch (thin supply); only "Available today".]
   - Q1.5 Show response time and completed-meetings count on cards? [Yes when data exists; both build trust (TZ section 8 lists completed bookings).]
   - Q1.6 What should a visitor see while there are zero or few companions? [A waitlist/"notify me" capture, not an empty grid.]

#### P2. Profile (companion profile, services, reviews, booking dialog)
1. Today (code): back chip; photo + thumbnails; name, verified tag, `age · city · gender`; rating/count or "No reviews yet"; bio; Languages and Interests tag boxes; services with price per unit; availability hint; sticky bottom bar with Book. Guests go to login and return (`from`); users without the customer role see "Choose the customer role". Dialog = service, datetime-local, duration, free-text place, estimate banner, Send request; then toast and redirect to the bookings list.
2. Comparables: Airbnb listing: review list with ratings, host info, availability calendar, price and cancellation summary before "Reserve", Request-to-Book with a 24 h host window [S Airbnb 88]. TaskRabbit profile: reviews, rate, chat-to-book [S TaskRabbit]. Rover: reviews only from completed bookings, identity verification, block/report on profiles [S Rover]. Preply/Superprof: intro video, trial/first lesson [S weak]. Booksy: service list plus slot picker [K].
3. Must-have: review texts (TZ section 8, and "Discover, Trust, Book" is the product core); visible availability or slot picker instead of blind time entry (today the server rejects with `booking_time_unavailable` / `availability_not_found`); cancellation and response-time summary next to the Book button (once defined); a "public places only" reassurance next to the place field; report/block entry for a fake profile (TZ section 8/24; currently "not available yet").
4. Nice-to-have: intro video (TZ section 8); completed-meetings count; share button producing a Telegram-friendly link preview (needs per-profile OG tags, which a pure SPA cannot serve without prerender/edge injection [I]); similar companions.
5. Excessive/confusing: gender inside the headline line (dating-adjacent); Languages and Interests as two equal boxes (merge into one "About" block); the availability hint pointing to a non-existent time filter; fallback sentences ("No personal details provided") that add noise.
6. Risks: `datetime-local` renders inconsistently across low-end Android WebViews and Telegram's in-app browser [I; test]; the free-text place with a 3-character minimum lets a home address through (hint only); "Estimated price" may differ from the server total and the platform fee is unset, so the payment step can 503 after the customer already committed (trust hit); companion-written bio/interests are not translated (settings note), so a ru customer may see only Uzbek.
7. Owner questions:
   - Q2.1 Show review texts publicly at launch? [Yes, with moderation and first-name only.]
   - Q2.2 Time selection: free time entry or companion-published slots? [Slots: removes rejections; the availability data already exists server-side.]
   - Q2.3 Show gender on the public profile? [Only if the companion opts in; never in the headline.]
   - Q2.4 Allow a pre-booking message to the companion? [No at launch: chat opens with the booking, which limits off-platform leakage; reconsider with data.]
   - Q2.5 Offer a vetted public-venue list per city for the meeting place? [Yes, suggestions plus free text; reduces home-address risk.]
   - Q2.6 Show the cancellation policy and response window in the booking dialog? [Yes, mandatory once the policy exists (owner decision, see Q4).]

#### P3. Login (phone + SMS code + consent)
1. Today (code): phone field prefilled `+998` with example hint, unticked consent checkbox (Terms/Privacy open in new tabs) that must be ticked before the code is requested, "Send code"; step 2: numeric code field (`autocomplete=one-time-code`, autofocus), change number, resend countdown, dev-OTP banner only if the API returns one; a disclaimer line "not a dating or escort service"; link to Settings; returns to the page the user came from.
2. Comparables: login at commitment, not at first access (NN/g; TaskRabbit) [S NN/g]. Android needs WebOTP and a `@domain #code` SMS format for auto-fill [S web.dev]. Telegram Gateway delivers codes at about $0.01 each [S Telegram]. Uber/Airbnb offer phone first plus alternative sign-in options [K].
3. Must-have: WebOTP wiring and matching SMS template; auto-submit when the code length is reached; phone mask with paste cleanup (`dedupePhonePrefix` exists); a fallback channel when SMS does not arrive; errors by code (exists); consent text in the user's language.
4. Nice-to-have: Telegram code delivery as fallback; "remember this device" with a longer session; 18+ confirmation inside the consent line.
5. Excessive/confusing: disclaimer line duplicates the consent box; Settings link above the form (a UZ|RU|EN switch is already in the top bar); the animated `layout` card; "Change number" chip competes with the primary button.
6. Risks: with no SMS provider the production error is `otp_delivery_unavailable` for 100% of new users (launch blocker; docs list "SMS provider" as not completed); Uzbek operator deliverability and SMS cost unknown; tokens in `sessionStorage` mean a closed tab, a new browser, or the Telegram in-app browser vs Chrome can force another SMS login [I; test]; there is no 18+ confirmation at sign-in (age is optional on Account); Terms/Privacy are Uzbek-only for ru users.
7. Owner questions:
   - Q3.1 Add Telegram as a code channel? [Yes as fallback: cheap, high reach (70-76% of Uzbek internet users prefer or use Telegram) [S UzDaily/CA Barometer]; confirm the +998 price in the Gateway dashboard.]
   - Q3.2 Google/Apple sign-in? [No at launch: TZ section 42 says phone+OTP for MVP.]
   - Q3.3 Require an explicit "I am 18 or older"? [Yes: adult-only meetings with strangers; put it into the consent line.]
   - Q3.4 Keep the consent checkbox (versioned record) vs "by continuing you accept"? [Keep the checkbox; it is your evidence.]
   - Q3.5 Longer session on trusted devices (instead of per-tab)? [Yes, 30 days; each SMS costs money and a drop-off.]

#### P4. Favorites
1. Today (code): customer-only list of the same cards as Discovery; empty state "Explore"; non-customer gets a 403 state with "Choose the customer role"; hearts are visible only to signed-in customers (guests never see a heart); unfavoriting reloads the list.
2. Comparables: Airbnb wishlists with a heart visible to guests that prompts login on tap [K]; Wolt/Glovo favourites rail on home [K]; Booksy favourites plus book again [K].
3. Must-have: guest heart that prompts login and then saves; "available today" signal on saved cards; a message if a saved companion became unavailable; one-tap Book from the card.
4. Nice-to-have: notify when a favourite becomes available; notes; share list.
5. Excessive/confusing: a permanent bottom-nav slot for Favorites while supply is small and Notifications has no slot [I].
6. Risks: silent disappearance of a favourite that is no longer public; the 403 role state confuses a plain customer if the role was lost.
7. Owner questions:
   - Q4.1 Are Favorites needed at launch? [Yes, but move to the Profile menu and give the nav slot to Notifications/Inbox.]
   - Q4.2 Can guests heart? [Yes, login prompt on tap.]
   - Q4.3 Notify the customer when a favourite becomes available? [Not at launch.]

#### P5. Bookings (list, cancel, report, block)
1. Today (code): permanent banner "No payment provider is connected yet ..."; list of cards: service + status tag, time range, place, price, "Your role"; buttons: Accept/Decline (companion), Cancel, Details, Report, Block/Unblock, SOS (confirmed/active). Confirm dialogs for accept/decline/cancel/block. One page serves both roles. No grouping, no companion name/photo, limit 50, no polling.
2. Comparables: Airbnb Trips: Upcoming/Past, photo + host + dates + status on each card [K]. TaskRabbit: payment/transaction history and visible fees [S TaskRabbit cancellation]. Booksy: upcoming/past plus rebook [K]. Wolt: active order pinned with live status [S Wolt Drive].
3. Must-have: companion name and photo (needs an API field or join); Upcoming / Past grouping; one status-driven primary action per card (Pay, Open chat, I'm here) instead of six equal buttons; "Book again" on completed (TZ section 35); expiry hint for pending requests (needs the response window); unread/needs-action badge on the tab.
4. Nice-to-have: add to calendar; share booking with a trusted contact (TZ section 17); receipt.
5. Excessive/confusing: Report, Block, Cancel and SOS on every card (move to an overflow "..." and Details); the permanent provider banner leaks internal status (show per-booking state instead); "Your role" row is noise for customer-only users; SOS duplicates the header SOS.
6. Risks: cancel dialog says refunds "are handled separately", so a paying customer learns nothing about money; `reason: ''` is sent, so no reason is captured; a decline looks like "Cancelled"; status changes need a manual refresh (only chat polls); destructive Cancel/Block sit next to Details on a phone (confirm dialogs mitigate).
7. Owner questions:
   - Q5.1 Cancellation rules: free window, fee tiers, who bears a companion-side cancellation, refund timing? [Owner decision, do not invent. Models to choose from: platform-set like TaskRabbit (fee within 24 h, free in first 5 minutes, free on companion no-show) [S] or companion-set like Booksy (deposit/fee % per service) [S]; show the chosen rule before the request is sent.]
   - Q5.2 How long may a companion take to answer before the request expires? [Pick a window (Airbnb uses 24 h [S]); show "answer expected by ..." and auto-notify the customer.]
   - Q5.3 "Book again" on completed bookings? [Yes, prefill service, duration and place.]
   - Q5.4 Move Report/Block/SOS into an overflow menu? [Yes.]
   - Q5.5 Show companion name and photo on every booking? [Yes; requires an API field.]
   - Q5.6 Distinguish "declined by companion" from "cancelled"? [Yes; customers need to know whether to rebook with someone else.]

#### P6. BookingDetail (payment, meeting, chat, review, report, SOS)
1. Today (code): header card; Payment (explanatory note, "Go to payment" when `accepted`, provider link, status line, 503 shown as a banner not "declined"); Meeting ("I'm here" x2 then Start, then Finish); Chat (8 s polling, text only, system messages); Review (1-5 stars + optional comment after `completed`); Safety (Report, SOS). Always renders all five sections.
2. Comparables: Airbnb reservation page: host card, directions unlocked after confirmation, change/cancel with refund breakdown, receipt [K]. Wolt: one status stepper with ETA [S]. Uber: safety toolkit and trip sharing in-ride [S]. TaskRabbit: fees in transaction history [S]. Rover: booking protection if the provider cancels [S].
3. Must-have: one "Next step" card on top driven by status (pending: waiting + deadline; accepted: pay N UZS; confirmed: meeting time + I'm here; completed: rate); hide sections that cannot be used yet; companion identity and profile link; cancel with cost preview; price breakdown (service, fee, total) once the fee policy exists; payment return handling (poll or refetch on focus after the provider); open place in a maps app; add to calendar; share booking with a trusted contact (TZ section 17).
4. Nice-to-have: reminders 24 h / 1 h before (needs an external channel); "running late" quick message; extend duration; chat images (TZ section 15).
5. Excessive/confusing: four inactive cards on a pending booking (Payment "not now", Meeting "not yet", Review "after meeting", empty chat); Safety section duplicates the header SOS; two lines of payment explanation; "Arrived 0 / 2" wording.
6. Risks: "I'm here" has no proof of presence, and there is no no-show path in the UI (TZ section 22), so a companion who does not show leaves only Report/Support and no defined refund; "Finish" waits for the other side with no timeout, which can block completion and the review; 8 s polling is battery/data heavy on weak phones [I]; payment link opens in the same tab and there is no return-URL handling yet [I]; the stable idempotency key per booking may return the same failed attempt on retry [I; test]; no "report a problem" branch after a low star rating; the chat hint tells users not to share phone numbers but Telegram habits make @username exchange likely.
7. Owner questions:
   - Q6.1 Cancel from the detail page with a cost preview? [Yes, once Q5.1 is decided.]
   - Q6.2 Timeouts: how long may an accepted booking stay unpaid; when is a meeting auto-completed if one side does not press Finish; when is a no-show declared? [Owner decision; each needs a number and a refund consequence.]
   - Q6.3 Location-verified check-in? [No at launch: privacy cost, weak GPS indoors; keep tap check-in and add a no-show report.]
   - Q6.4 Chat images at launch? [No: storage adapter is not built and the owner said server/storage come last.]
   - Q6.5 Hide all phone numbers and add number/handle detection later (TZ section 15)? [Yes; keep the hint now.]
   - Q6.6 Add "open in maps" and "add to calendar"? [Yes, cheap and reduces no-shows.]

#### P7. DemoPay (test payment page)
1. Today (code): `/demo-pay/:reference` for the paying customer only: DEMO chip, "Test payment page", banner "not a real payment", amount, status, buttons Confirm (DEMO) / Reject (DEMO) / Back; 404 state when the server has no demo provider.
2. Comparables: a real hosted checkout (Click, Payme) shows merchant, amount, card or wallet entry, SMS confirmation, then returns to the merchant URL [K]. TaskRabbit/Airbnb show payments inside the app [S TaskRabbit Payments tab].
3. Must-have for the demo: unmistakable DEMO labelling (present); a clear return path (present); never reachable in production (server flag, present). For the real flow (a different screen): amount including fees, order summary, time limit, return-URL handling, pending state.
4. Nice-to-have: scenario buttons for QA (timeout, decline) on the demo only.
5. Excessive/confusing: nothing for a test page; the route should disappear when the real provider is enabled. The owner rule that promo videos carry no DEMO label means this page must never be filmed.
6. Risks: low; a tester could still mistake it for payment if the banner were removed; a real provider will add a "pending" state that the current detail page does not poll.
7. Owner questions:
   - Q7.1 Which provider first? [Click first (the backend already models CLICK test mode), Payme second; Paynet leads by revenue per Kun.uz [S], so check merchant onboarding terms for all three.]
   - Q7.2 Keep the DEMO provider on the public demo URL? [Yes, clearly separated from any production domain.]
   - Q7.3 Hold the full amount at acceptance or a deposit? [Owner decision (TaskRabbit/Booksy differ [S]); needs fee and payout policy (TZ sections 26-27).]
   - Q7.4 Which payment methods must the provider page support (Uzcard, Humo, Visa/Mastercard, wallet)? [All local cards plus wallet; decided by the provider contract.]

#### P8. Notifications
1. Today (code): list (50) of kind label + time + "New" tag; "Open booking" button for booking notices (marks read); "Mark all as read"; empty state. Reachable only from the Account menu (badge there). Gift notices appear without a link ("Gift order created (test)").
2. Comparables: ride/delivery apps rely on push and SMS for state changes (Wolt tracking link [S]); Booksy/Airbnb send reminders and status changes outside the app [K]; Airbnb emails the outcome of a request [S Airbnb 88: "updated by email"].
3. Must-have: an out-of-app channel for three events (accepted: pay now; declined/expired; meeting soon); nav badge; whole row tappable; content that says who and when ("X accepted your Coffee on 15 Nov, 18:00").
4. Nice-to-have: opt-in Telegram bot, web push after PWA install; per-type preferences.
5. Excessive/confusing: gift/test notices before any gift flow exists; a separate page plus a separate badge if Bookings can carry the state.
6. Risks: today the accept-to-pay loop depends on the customer opening the app; unpaid accepted bookings expire at start time (slot lost silently); notification kinds omit scheduled reminders (backend: not built); `chat_message` notices say "New message" without sender or booking.
7. Owner questions:
   - Q8.1 Which out-of-app channel for critical events? [Telegram bot (opt-in) first, SMS only for "accepted: pay now" if cost allows; no e-mail per owner decision.]
   - Q8.2 Keep a notification page or fold it into Bookings status? [Keep, give it a nav slot with badge.]
   - Q8.3 Reminder timing before a meeting? [Owner picks; a common pattern is two reminders.]
   - Q8.4 Hide gift/test notice kinds until gifts ship? [Yes.]

#### P9. Account (profile hub, deletion request)
1. Today (code): header (phone, roles, member since); menu (Bookings, Notifications+badge, Favorites, Studio, Help, Settings); personal form (age 18-120, free-text gender, city); "Who I am" role chips (Customer/Companion toggle, at least one); sign out; deletion block (30 days, refused with open bookings, cancellable).
2. Comparables: Airbnb/Uber account hubs: personal info, login and security, payments, notifications, privacy [K]; TaskRabbit Payments tab with transaction history [S]. TZ section 36 lists personal info, verification, bookings, favorites, reviews, payments, safety, settings, support.
3. Must-have: display first name (companions need to know who requests); payment history once a provider exists; notification preferences; clear sign-out; deletion with plain explanation (exists).
4. Nice-to-have: avatar; "my reviews"; sign out other devices; data export.
5. Excessive/confusing: free-text gender for customers; a one-tap role toggle that can turn a customer into a companion (or remove the customer role) without explanation; Studio linked twice; the internal "account status is set by an administrator" note.
6. Risks: free-text gender/age is sensitive data without a stated purpose (Privacy should justify it or you should drop it); removing the customer role blocks booking; deletion is final after the window and refused while bookings are open (message exists); Account is the target of the "Profile" tab, so a long page with a danger zone is the first thing a customer sees.
7. Owner questions:
   - Q9.1 Collect age and gender from customers (TZ section 3 says so)? [Collect an 18+ confirmation only; gender optional via a fixed choice or drop it unless a feature uses it.]
   - Q9.2 Require a display name for customers? [Yes, first name, so a companion knows who is booking.]
   - Q9.3 Role toggle vs a "Become a companion" call to action? [Separate CTA that leads to the application.]
   - Q9.4 Offer data export? [Not at launch.]

#### P10. Help (112, trusted contacts, support requests, FAQ, my reports)
1. Today (code): Emergency card (Call 112 + SOS), "Report a problem" (explains, links to Bookings; profile reports unavailable), then if signed in: My reports, Trusted contacts (add/remove, stored only), beta feedback (invited users); FAQ (9 questions); in-app support form with status and replies; signed-out users get a login prompt.
2. Comparables: Uber Safety Center (trusted contacts, share trip, emergency) [S]; Yango Safety Center (SOS, share route, up to 3 contacts) [S]; Rover 24/7 Trust and Safety with block/report [S]; TaskRabbit/Airbnb help centres with search and contact options [K].
3. Must-have: emergency first (done); safety guide and community guidelines pages (TZ sections 16 and 19, missing); a way to reach support without signing in (OTP failures); stated response time; trusted-contact sharing of booking details (TZ section 17).
4. Nice-to-have: FAQ search; Telegram support link; first-booking safety checklist; Contact Picker on Android [K].
5. Excessive/confusing: FAQ lines that say "not defined yet" (must be replaced before launch); one long page mixing static content and per-user data (split Safety / Contact us); the "Report a problem" card only explains.
6. Risks: unverified 112 claim (Gaps); saved trusted contacts can look like a safety net although nobody is notified (copy says so, keep it visible); in-app-only support is unreachable for users who cannot sign in; no stated hours or response time.
7. Owner questions:
   - Q10.1 Add a Telegram support entry (username or bot) for people who cannot sign in? [Yes: fits the "no e-mail, no phone" rule and Telegram habits.]
   - Q10.2 Publish support hours and a response target? [Yes, but only after staffing is decided; otherwise state hours honestly.]
   - Q10.3 Safety guide and Community Guidelines pages before launch? [Yes (TZ sections 16, 19, 20).]
   - Q10.4 Manual "Share booking" with trusted contacts (an sms:/messenger link, no server SMS)? [Yes, consistent with the honest-SOS rule.]
   - Q10.5 Allow reporting a profile without a booking (fake profile, TZ section 24)? [Yes; needs an API change.]

#### P11. Settings (language, Uzbek alphabets, themes)
1. Today (code): Language (UZ/RU/EN) and Uzbek alphabet (1995 / 2026), Appearance (5 themes), Account (link or login), Privacy and safety (to Help), About (version, Terms, Privacy, draft banner). Works signed out; language and alphabet are saved to the account when signed in; theme is per device.
2. Comparables: consumer apps keep language, notifications, privacy, account; extra theme palettes are rare beyond OS dark mode [K]; Telegram offers language lists inside settings [K].
3. Must-have: language (done); notification preferences when channels exist; account/privacy links; visible sign-out (lives on Account).
4. Nice-to-have: "lite mode" (no blur or animation) auto-enabled on low-end devices or Save-Data; text-size option; follow-system dark mode.
5. Excessive/confusing: three non-brand themes (Gul, Jurnal, Stone) next to the two Yondo themes whose rule is "only ink/paper/carrot"; three preference controls on a first-time screen; the "Draft" banner and version row in About.
6. Risks: "Current alphabet (1995)" / "New alphabet (2026)" is jargon for many users; the default silently flips from 1995 to 2026 on 2027-04-22 for users who never chose, so the UI spelling changes under them [I]; Uzbek Cyrillic (still used by many older readers) is not offered, RU covers only Russian readers [I]; no low-power fallback (Cited Findings).
7. Owner questions:
   - Q11.1 Ship only the two Yondo themes at launch? [Yes: brand consistency, less QA, fewer blur-heavy variants.]
   - Q11.2 Add a lite mode, on by default for low-end devices? [Yes.]
   - Q11.3 Uzbek Cyrillic? [No at launch; the RU locale serves Cyrillic readers. Confirm with a few real Uzbek users.]
   - Q11.4 On 2027-04-22, switch default spelling automatically or ask once? [Ask once with an example word, then respect the choice.]
   - Q11.5 Offer per-channel notification preferences? [Yes after Q8.1.]

#### P12. Terms / Privacy (and the consent gate)
1. Today (code): `/terms` and `/privacy` render owner-written Uzbek Markdown (80 and 116 lines) with a draft banner and version; ru/en users see "available in Uzbek only"; consent is an unticked box at login; a full-page gate asks signed-in users to accept new versions (except on the two pages). Operator "not yet indicated".
2. Comparables: Airbnb/TaskRabbit/Uber split Terms from cancellation, refund, community-standards and safety pages; TaskRabbit publishes a dedicated cancellation article [S]. TZ section 20 lists ten documents.
3. Must-have: operator identity; Cancellation, Refund, No-show and Payment terms; Community Guidelines and Prohibited Services (TZ sections 19-20); a short plain-language summary on top; Russian version.
4. Nice-to-have: "what changed" on a version bump; anchors/table of contents.
5. Excessive/confusing: the draft banner and "operator not indicated" must go before launch; text-only Markdown (no summary) is long on a phone.
6. Risks: a ru customer consents to a document they may not fully read in their language; Terms point to fees/cancellation that are "not defined", so consent is given without the money rules; a version bump gate can block a user mid-payment.
7. Owner questions:
   - Q12.1 Provide Russian Terms and Privacy at launch? [Yes: mixed uz/ru audience; the owner said legal review is not required, but translation is a comprehension issue, not a legal one.]
   - Q12.2 Separate Cancellation/Refund/Community Guidelines pages? [Yes, TZ section 20; fill them only from owner decisions.]
   - Q12.3 Name the operator before launch? [Yes (already on the pre-publication checklist).]
   - Q12.4 Add a 5-line key-points box above Terms? [Yes.]

#### P13. SOS dialog
1. Today (code): header SOS (signed-in), also in Help, on confirmed/active booking cards and Detail. Dialog = confirmation: Call 112 (`tel:`), "Add my location to the message" (browser geolocation on tap, goes only into SMS text), trusted contacts with SMS (prefilled text) and Call links, "Signal to a moderator" for an active meeting (recorded alert, "nobody was notified automatically"), Close. Guests see 112 + location + login hint.
2. Comparables: Uber trusted contacts, share trip, in-app emergency button [S]; Yango Safety Center with SOS, Share Route and up to three contacts, automatic or manual [S]; Rover's 24/7 Trust and Safety team [S]. Those products have server-side reach; Yondo deliberately claims none, which is the right honesty rule.
3. Must-have: 112 first and biggest (done); no false claims (done); booking context in the SMS (place, time, meeting service) so a contact can act; a statement of when a moderator is on duty; works from device capabilities only (done).
4. Nice-to-have: manual "share my booking" before the meeting; messenger share (Telegram/WhatsApp) alongside SMS.
5. Excessive/confusing: five blocks in one scrolling dialog (intro, 112, location, contacts, moderator) is a lot to scan under stress [I]; the moderator section fetches `/bookings` after open, so it appears late.
6. Risks: `sms:` and `tel:` links and geolocation may behave differently in Telegram's in-app browser [I; test]; SMS needs balance on the user's SIM; a "Signal recorded" message can still reassure more than the SLA justifies if nobody is on shift; location can take up to 15 s on weak GPS; users with no trusted contacts see only a link to Help.
7. Owner questions:
   - Q13.1 Who reads moderator SOS signals and when (24/7 or office hours)? [Do not promise more than staffing; if not 24/7, print the hours in the dialog.]
   - Q13.2 Add Telegram/WhatsApp share to SMS? [Yes.]
   - Q13.3 Include meeting place/time/service in the SOS text? [Yes.]
   - Q13.4 Require at least one trusted contact before the first meeting? [Prompt, do not require.]
   - Q13.5 Keep SOS visible in the header when no booking is active? [Yes (owner decision S25), but visually quieter.]

#### P14. ReportDialog (and Block)
1. Today (code): from a booking card or Detail: dialog says who the report is about, category (8, default "Other"), required description (4000), "not emergency help" note; sends only `booking_id`; toast points to Help > My reports (statuses open / in_review). Block is a separate button with a confirm dialog and Unblock; the other side is not notified. No profile-level report, no evidence upload.
2. Comparables: Rover gives everyone block and report [S]; TZ section 23 describes Booking > Issue > Description > Evidence > Submit; Airbnb/Uber after-trip issue reporting [K].
3. Must-have: expected response time; outcome statuses (resolved plus what was done); a combined "Report and block" choice; reach from the chat and from a profile.
4. Nice-to-have: optional screenshot evidence (needs the storage adapter); attach chat context with consent.
5. Excessive/confusing: separate Report, Block, Support and Cancel buttons in several places; report categories overlap with support topics (payment_issue vs Support > Payment).
6. Risks: false or retaliatory reports; no closure state, so users never learn the result; a customer in distress may not find the right tool among Report / SOS / Support.
7. Owner questions:
   - Q14.1 One "Get help with this booking" sheet routing to emergency / report / support? [Yes.]
   - Q14.2 Evidence upload at launch? [No: storage comes last per owner (S26).]
   - Q14.3 What can moderation do and how is the reporter told (suspend, warn, refund)? [Owner decision; today only open / in_review exist.]
   - Q14.4 Does a report auto-block the companion for that customer? [Offer "Report and block" as a checkbox, default on for harassment/unsafe categories.]

#### P15. Layout, top bar, footer
1. Today (code): top bar with logo, desktop nav (Discover, Favorites and Bookings when signed in, Profile or Sign in, Admin), SOS for signed-in users, UZ|RU|EN switch; below 860 px a bottom dock with the same items; footer links Help, Settings, Terms, Privacy; skip link; animated aurora background and page transitions; consent gate around the outlet. Notifications has no nav slot or badge; Help is only in footer and Profile menu.
2. Comparables: bottom tab bars with 4-5 items and badges on the inbox/orders tab (Airbnb, Booksy, Wolt) [K].
3. Must-have: badge on the tab where action is needed (accepted-unpaid, new message); skip link and 44-52 px targets (present); sticky Book CTA (present).
4. Nice-to-have: web app manifest and install prompt (none exists); per-profile link previews for Telegram sharing (needs prerender or edge injection) [I]; "lite mode".
5. Excessive/confusing: aurora + parallax + spotlight + shared-layout pill animations + 9 `backdrop-filter` rules on every page; for a low-end Android this is the most likely cause of jank [I; measure on a real device].
6. Risks: no low-power fallback; with Brand/SOS/language switch/dock the 360 px top bar may be crowded [I; check]; carrot `#E8501A` is 3.36:1 on paper, correctly restricted to graphics by owner rule.
7. Owner questions:
   - Q15.1 Replace the Favorites tab with Notifications/Inbox (with badge)? [Yes.]
   - Q15.2 Keep the animated background on low-end devices? [No: auto lite mode.]
   - Q15.3 Make the site installable (PWA) and Telegram-share friendly? [PWA yes later; link previews yes before marketing starts.]
   - Q15.4 Put Help in the main nav? [No; footer plus Profile menu plus the SOS dialog is enough.]

---

## Q3. What do the cross-page flows look like (first booking, rebooking, failure states)?

### Takeaway
A first-time visitor needs roughly 9 screens and 2 waits before "request sent" and then depends on an unannounced companion decision; rebooking has no shortcut and no remembered preferences; failure states mostly end on a message with no next best action (decline, unavailable payment, no results, expired slot).

### Cited Findings
- Journey order and screens come from the routes in [App.tsx](file:///D:/Yondo/apps/web/src/App.tsx), the login redirect (`state.from`) in [Login.tsx](file:///D:/Yondo/apps/web/src/pages/Login.tsx) and the booking dialog in [Profile.tsx](file:///D:/Yondo/apps/web/src/pages/Profile.tsx).
- Bookings never auto-refresh, notifications are in-app only, unpaid accepted bookings expire at start time (README: "never confirmed and whose start passed show as expired") — [README](file:///D:/Yondo/apps/web/README.md), [docs/frontend-api-integration.md](file:///D:/Yondo/docs/frontend-api-integration.md).
- Error-code copy exists for: `booking_time_unavailable`, `availability_not_found`, `booking_start_in_past`, `booking_blocked`, `booking_expired`, `payment_provider_unavailable`, `payment_configuration_unavailable`, `booking_not_payable`, `meeting_not_ready`, `meeting_check_in_required`, `otp_delivery_unavailable`, `network_error`, `account_deletion_pending` — [en.ts](file:///D:/Yondo/apps/web/src/i18n/en.ts).
- TaskRabbit: after a Tasker cancels the client can rebook with a new Tasker [S](https://support.taskrabbit.com/hc/en-us/articles/360036115891); Rover offers help finding a new sitter after a last-minute cancel [S](https://www.rover.com/safety); Airbnb frees the guest to book elsewhere if the host declines or lets the request lapse [S](https://www.airbnb.com/help/article/3702).

### Inferences
**Flow A: first-time visitor to first booking** (screens in order; friction in brackets)
1. Discovery: hero plus open filter panel [first card below the fold at 360 px, I]. 2. Card. 3. Profile [no reviews text, no availability]. 4. Tap Book: guests go to Login (correct: login at commitment [S NN/g]). 5. Phone + tick consent [Uzbek-only documents for ru users]. 6. SMS code [provider not connected; WebOTP missing]. 7. Back on the profile (returns via `from`). 8. Booking dialog [blind time; estimate only; no policy shown]. 9. Toast, redirect to Bookings (pending). 10. Wait [no external notice; no response deadline]. 11. Companion accepts [customer only learns by opening the app]. 12. Bookings > Details > "Go to payment" [fee/provider may be unavailable]. 13. Provider page, return, status [no polling]. 14. Confirmed; chat; at the place "I'm here"; Start; Finish [no no-show path]. 15. Review [no "report" branch for low stars]. Biggest drop-off candidates [I]: SMS delivery, blind time entry, the unannounced wait, payment availability.
- Recommended order of fixes: (1) availability/slots, (2) notification channel, (3) companion identity + status-driven Next step card, (4) policy text (cancellation, response window, fee) shown before sending, (5) payment return polling.

**Flow B: returning customer rebooking**
- Paths today: Favorites tab or Bookings > open companion is not possible from a booking (no companion link on the booking), so the user must search again or use Favorites. No "Book again" (TZ section 35). The dialog does not remember service, duration or place. A new tab or closed browser may require another SMS login (`sessionStorage`).
- Needed: "Book again" on completed and cancelled cards with prefilled service/duration/place; a link from a booking to the companion profile; "Recently booked" row on Discovery for signed-in customers; longer session.

**Flow C: failure states** (today / comparable behaviour / needed)
- Companion declines: today appears as "Cancelled" plus a `booking_declined` notification; comparables free the guest to book elsewhere [S Airbnb] or rebook with another provider [S TaskRabbit]; needed: distinct "Declined" state, reason if given, one-tap "Find similar companions" with the same time and service.
- Companion never answers: today stays "Awaiting response" until the start time passes, then "Expired" [README]; comparables set a 24 h window [S Airbnb]; needed: owner-set window, countdown shown to both sides, notification on expiry with a rebook CTA.
- Time taken / not available: today server error text (`booking_time_unavailable`) inside the dialog; needed: show nearest free slots instead of an error.
- Payment unavailable (503): today a neutral banner "payment service is not connected yet" (correct not to say "declined"); booking stays accepted and may expire; needed: a production message with an expected time or alternative (e.g., "we will notify you"), and no forward motion that can lose the slot silently.
- Payment fails/abandoned: today status line "Failed" and the same button; idempotency key reuse unverified [I]; needed: clear "try again" state, time left to pay.
- No search results: today "No matching companions found" + "Clear filters"; comparables recommend one primary next action [S Carbon/SAP]; needed: suggest which single filter to relax with a count, plus a "notify me" option while supply is thin.
- SMS code does not arrive: today `otp_delivery_unavailable` or resend after countdown; needed: fallback channel (Telegram [S]) and a support path that works signed-out.
- Offline/weak network: `network_error` copy exists; no offline queue for payment or chat sends [I].
- Companion no-show / meeting not finished: no UI path; Report and Support only; needed: no-show report with defined refund rule (owner) and auto-complete timeout.
- Account deletion pending: booking refused with `account_deletion_pending` and a cancel hint — adequate.

### Gaps
- No measured completion times, drop-off data or analytics exist in the repo; all funnel claims are qualitative.
- Whether new users receive the `customer` role automatically at first sign-in was not confirmed in the backend code (the UI handles a user without it via a "Choose the customer role" link).
- Behaviour on real low-end Android, iOS Safari and Telegram's in-app browser was not tested.

---

## Q4. Which owner decisions block or shape the customer pages, ranked?

### Takeaway
Nine P0 policy decisions gate a public launch; none can be inferred from the code or the comparables, only chosen. Everything else is design work that can proceed in parallel.

### Cited Findings
- The product rules forbid inventing platform fee, delivery fee, cancellation percentage, refund amount or payout rules; unset values must show "Aniqlanmagan"/503 — [CLAUDE.md section 4](file:///D:/Yondo/CLAUDE.md).
- TZ section 21 says cancellation percentages are set after the business model is confirmed; section 26 says the payment provider is selected separately; section 22 lists no-show handling with refund/payout rules — [TZ.md](file:///D:/Yondo/TZ.md).
- The pre-publication checklist and WORKLOG list operator name, support SLA and provider setup as open — [docs/legal/pre-publication-checklist.md](file:///D:/Yondo/docs/legal/pre-publication-checklist.md), [docs/WORKLOG.md](file:///D:/Yondo/docs/WORKLOG.md).

### Inferences
**P0 (blocks a public launch; each appears on several pages)**
1. Cancellation, refund and no-show policy (free window, fees, companion-side cancellation, refund timing). Pages: Profile, Bookings, BookingDetail, FAQ, Terms.
2. Platform fee and total-price display (service price + fee = total). Pages: Profile dialog, BookingDetail, DemoPay/real checkout.
3. First payment provider and flow (Click/Payme/Paynet; full amount vs deposit; holding until completion per TZ section 27). Pages: BookingDetail, DemoPay.
4. Companion response window and the unpaid-hold window (how long a pending request may wait; how long an accepted booking may stay unpaid). Pages: Bookings, BookingDetail, Notifications.
5. OTP delivery channel(s) and provider (SMS, Telegram fallback). Page: Login.
6. Support hours/response target and SOS moderator staffing, plus verifying the emergency number. Pages: Help, SOS.
7. Operator identity and the missing policy documents (cancellation, refund, community guidelines). Pages: Terms/Privacy, Help.
8. 18+ confirmation at sign-in. Pages: Login, Account.
9. Russian versions of Terms/Privacy. Pages: Terms/Privacy, Login.

**P1 (shapes conversion and trust)**: availability/slot model and time filter; companion identity on bookings; out-of-app notifications; public review texts; gender display/filter; fixed city list; ship only Yondo themes plus lite mode; Notifications nav slot; "Book again".

**P2 (later)**: venue suggestions, chat images/evidence upload, PWA/Telegram Mini App, data export, location-verified check-in, home rails.

### Gaps
- No decision list exists yet for the companion-facing screens; this audit covers customer pages only.
- Priorities are my judgement from the evidence above, not a ranked backlog from the owner.
