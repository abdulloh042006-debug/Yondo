# One app with role modes vs two apps for a two-sided marketplace (Yondo)

Research status note: the research session hit a usage limit before the last three planned lookups finished (Chrome Trusted Web Activity docs, WCAG/EAA legal status, Apple HIG dark-mode page fetch failed because the page is JS-rendered). Those items are listed under Gaps. Every claim below is either cited, or placed under "Inferences" as my judgment. "Search-result snippet" means the search tool summarised the page but I did not open the page itself; treat those as medium confidence.

Date context: today is 2026-10-28. Repo facts below come from my own read of D:\Yondo (file paths given), not from the web.

---

## 1. How do comparable products do it (case studies: one app vs two, switcher design, stated reason)?

### Takeaway
The evidence splits cleanly: ride-hailing and delivery products (Yandex, Uber, Bolt, Wolt, Glovo) ship a separate supply-side app, and so do the professional-services marketplaces TaskRabbit and Thumbtack and Uzbekistan's Uzum (sellers). Peer-style marketplaces (Airbnb, Fiverr, Upwork, Rover, and apparently inDrive) keep both roles in one account/app with a mode switch. No company I found states its reason in its own words; reasons are my inference. Upwork is a notable data point: it merged its separate client and freelancer apps into one.

### Cited Findings

Separate supply-side app (two apps):
- Yandex Pro is a distinct App Store app for taxi drivers and couriers (car, motorcycle, bicycle, on foot); it carries taxi orders, Yandex Eda courier features, car-rental fleet search, a map of higher-paying zones, and runs in 300+ cities; the developer's other listed apps include Yandex Go (the passenger/food super-app). The listing does not say outright that passengers use a different app. — [Yandex Pro App Store (RU)](https://apps.apple.com/ru/app/%D1%8F%D0%BD%D0%B4%D0%B5%D0%BA%D1%81-%D0%BF%D1%80%D0%BE-%D0%B2%D0%BE%D0%B4%D0%B8%D1%82%D0%B5%D0%BB%D0%B8-%D0%B8-%D0%BA%D1%83%D1%80%D1%8C%D0%B5%D1%80%D1%8B/id1496904594)
- Yandex Pro was created on the base of Yandex.Taximeter (older reporting, search-result snippet; page not opened) — [iXBT](https://www.ixbt.com/live/comments/1093870)
- In 2020 Yandex.Taxi became Yandex Go; Drive/Eda/Lavka continued both inside Go and as standalone apps (search-result snippet) — [NEWSru.co.il](https://newsru.co.il/auto/20aug2020/yandex_go.html)
- Yandex's ride-hailing share in Uzbekistan is listed at 86.3% (2023) (search-result snippet) — [Wikipedia: Yandex Taxi](https://en.wikipedia.org/wiki/Yandex_Taxi)
- Uber presents a Rider app and a Driver app as distinct products on its own explainer page — [Uber: how it works](https://www.uber.com/about/how-does-uber-work/). Uber's engineering post on the driver app ("Carbon") does not explain why it is separate; it says all Uber apps follow an internal template (shared networking, storage, ReactiveX, analytics, crash reporting and the RIBs architecture framework) — [Uber Engineering: driver app RIBs](https://www.uber.com/en-ES/blog/driver-app-ribs-architecture). So: separate apps, shared engineering foundation, no stated product rationale.
- Bolt publishes a separate driver app and rider app (secondary sources; no company statement on why) — [Bolt Driver listing](https://taxify-driver.fileplanet.com/apk), [Bolt safety features on driver app](https://www.connectingafrica.com/emerging-technology/bolt-introduces-additional-safety-features-on-driver-s-app)
- Wolt couriers use a dedicated "Wolt Courier Partner" app; couriers log in by phone + SMS code, get offers that disappear if not accepted within 60 seconds, and Wolt recommends location access "Always" — [Wolt Partner App](https://explore.wolt.com/en/est/couriers/learning-center/partner-app), [App Store listing](https://apps.apple.com/us/app/-/id1477299281)
- Glovo runs a separate "Glovo for Couriers" app (earnings breakdown, schedule, zone insights, one-tap order acceptance; apply at couriers.glovoapp.com) — [AppFollow listing](https://apps.appfollow.io/ios/glovo-couriers/1451416371?country=us)
- TaskRabbit's Tasker app "is different from the Taskrabbit app that Clients use to book tasks"; it is on the App Store and Google Play (iOS 15+/Android 6+) — [TaskRabbit support](https://support.taskrabbit.com/hc/en-gb/articles/115005258786-Downloading-the-Tasker-App)
- Thumbtack has two App Store listings: "Thumbtack: Home Service Pros" (customers) and "Thumbtack for Professionals" (budget controls for lead prices, integrations with Housecall Pro/GoSite/ServiceTitan/Google Calendar). Thumbtack's developer reply to a pro-side complaint on the consumer app told the user to post on the pro app — [Pro app](https://apps.apple.com/app/id908795016), [Consumer app](https://apps.apple.com/us/app/852703300)
- Uzum Market (Uzbekistan) launched a separate "Uzum Sellers" app in October 2023 for merchants: balance, sales and stock in real time, withdrawal requests, replies to reviews, later promotion campaigns; Uzbek and Russian; 6,000+ entrepreneurs at launch (search-result snippet) — [Spot.uz](https://www.spot.uz/ru/2023/10/10/uzum-sellers/), [App Store](https://apps.apple.com/app/id6450532985)

One app / one account with a mode switch:
- Airbnb: in the app "hold Profile and then tap Hosting"; to go back "hold Menu and then tap Traveling"; on the web a "Switch to hosting" link sits beside the avatar — [Airbnb Help 3546](https://www.airbnb.com/help/article/3546). Community threads report the host toggle sometimes missing and being found only on desktop or by using the profile that created the listing — [Airbnb Community](https://community.withairbnb.com/t5/Hosting/Airbnb-App/m-p/799489)
- Fiverr: one account for buying and selling (Community Standards: only one account; a second one risks permanent suspension, except Team seats). A client account becomes a freelancer account via the profile menu ("Become a Seller") after completing a freelancer profile; "switching to a freelancer profile does not affect your client account." Gigs can only be created/edited on desktop — [Fiverr: freelancer profile](https://help.fiverr.com/hc/en-us/articles/360010558598-Creating-editing-your-freelancer-profile), [Fiverr Community Standards](https://help.fiverr.com/hc/en-us/articles/32242973123985-Our-Community-Standards) (the "desktop only" and "one account" points are from search-result summaries of these help pages)
- Upwork: the mobile app supports both roles under one login; once both profiles exist you "tap to switch"; roles are added in Settings and switched from the account menu under the profile picture; notifications are configured separately per role; "some features may only be available on a desktop or mobile browser." Upwork merged its separate "Upwork for Clients" and freelancer apps into one combined app (old client app unsupported after an October 7 cut-off; announcement text says everything is "in one place" for hiring, freelancing or both) — [Upwork help: freelancers app](https://support.upwork.com/hc/en-us/articles/360015504093-Upwork-for-Freelancers-App), [Upwork help: be a client and a freelancer](https://support.upwork.com/hc/en-us/articles/17980481990291--Be-a-client-and-a-freelancer), [Upwork community announcement](https://community.upwork.com/t5/Announcements/Update-on-Upwork-s-New-Mobile-Apps-for-Clients-and-Freelancers/m-p/644816) (announcement URL redirected when I tried to open it; the merger detail is from a search snippet)
- Rover: owners and sitters manage bookings from a single account; an owner becomes a sitter by completing a sitter profile that goes to a review team (Canadian support page, search-result summary). A student design critique of the iOS app says the inbox splits "pending/upcoming" between client and sitter roles with near-identical views, "which leads to many mode errors," and that many users are both clients and sitters — [Rover support](https://support-ca.rover.com/hc/en-ca/articles/360037441871), [Pratt IxD critique](https://ixd.prattsi.org/2022/09/design-critique-rover-ios-app/)
- inDrive: the App Store listing for the main app says "Sign up as a driver or courier and earn on your own terms" and "You can sign up as a driver or courier and use the app as a source of income," with no separate driver app named. I could not confirm an in-app "mode switch" — [inDrive App Store](https://apps.apple.com/cy/app/id780125801)

Uzbekistan-specific:
- Express24: Yandex Uzbekistan agreed in October 2024 to buy part of Express24's assets, planning a single technology platform for food delivery; courier recruiting questions were routed to a Telegram bot in 2022 — [Economist.kg](https://economist.kg/biznes/2024/10/25/yandex-uzbekistan-poghloshchaiet-chast-aktivov-siervisa-dostavki-express24/), [Kun.uz (Cyrillic)](https://kun.uz/kr/news/2022/10/09/express24-da-piyoda-va-velosipeddagi-kurerlar-qancha-pul-topadilar)
- MyTaxi (Uzbekistan): passenger app confirmed (cashless via Uzcard/Humo); I did not find a separate "MyTaxi Driver" listing — [Similarweb](https://www.similarweb.com/app/apple/865012817)

### Inferences
- Pattern in the cases: the supply side gets its own app when its work is "on shift" and operational: dispatch with a timer (Wolt's 60 s offers), always-on location, earnings/zone maps, fleet/inventory/lead-pricing tools (Yandex Pro, Wolt, Glovo, Thumbtack Pro, Uzum Sellers). Peer-style marketplaces where the same person flips between roles (Airbnb, Fiverr, Upwork, Rover) use one app plus a switch. TaskRabbit is the exception (async tasks yet two apps), so the pattern is a tendency, not a rule.
- Stated reasons are absent in all sources found; "tailored tooling per role" is my explanation (one search tool summary flagged the same for Bolt).
- Yondo's companion workflow (receive booking request, accept/decline, manage profile/services/availability, see status/blockers) is asynchronous request/accept, closer to Airbnb/Upwork/Fiverr than to Wolt/Yandex Pro dispatch. That is a judgment based on `docs/web-and-admin.md` (Studio: application, profile, services, photos, availability, status & blockers) and the booking flow in CLAUDE.md; an owner answer about live location or shift behaviour could change it.
- Upwork's consolidation suggests that maintaining two apps for two roles became a cost even for a large company (the reason was not verified).

### Gaps
- Official statements of "why" for Yandex, Uber, Bolt, Wolt, Glovo, TaskRabbit, Thumbtack: none found.
- Bolt, Glovo, Thumbtack evidence is from aggregator/store listings; no Bolt company page opened.
- OLX.uz, Care.com, MyTaxi driver side, inDrive in-app mode-switch mechanics: no usable source found.
- Airbnb engineering/design blog on host/guest mode: not found (only help centre).
- Fiverr and Rover help pages returned only search summaries or 403 on direct fetch.

---

## 2. Pros and cons of (a) one app + role switcher, (b) two entry points from one codebase, (c) fully separate products

### Takeaway
Store-policy and engineering facts favour starting with one codebase and one login; packaging for a second entry point (separate PWA identity under /studio) is cheap and reversible, while fully separate products multiply store review, accounts, push configuration and QA. Most of the trade-off analysis below is judgment; the facts that constrain it are cited.

### Cited Findings
- Apple App Review Guidelines 4.3(a): "Don't create multiple Bundle IDs of the same app" (spam rule); 4.2: apps must "elevate it beyond a repackaged website"; 5.1.1(v): apps that support account creation "must also offer account deletion within the app"; 3.1.3(e): goods/services consumed outside the app can be paid with non-IAP methods such as Apple Pay or card entry; 1.1.4 lists "hookup" apps and apps that "may be used to facilitate prostitution" as prohibited; 4.3(b) restricts dating apps that do not offer a meaningfully different experience — [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Google Play requires an in-app path to delete accounts (a web link resource is also required); retained data for security, fraud or regulation must be disclosed; non-mobile apps (web) still need a discoverable web link — [Google Play account deletion policy](https://support.google.com/googleplay/android-developer/answer/13327111)
- Google Play Sexual Content policy prohibits "apps that promote sex-related entertainment, escort services," services "that may be interpreted as providing or soliciting sexual acts in exchange for compensation," and "compensated dating," naming "sugar dating" — [Google Play policy](https://support.google.com/googleplay/android-developer/answer/9878810) (summary of a truncated page)
- Several PWAs can share one origin if each has a distinct manifest `id` and `start_url`; `id` is the app identity; different `id` = a distinct installable app, same `id` = update of the installed app. Non-overlapping `scope` is recommended (MDN's scope detail is general guidance, not on that page) — [MDN: manifest id](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/id)
- Upwork keeps notification settings separate per role in the single app and sends some tasks to the browser — [Upwork help](https://support.upwork.com/hc/en-us/articles/360015504093-Upwork-for-Freelancers-App)
- Supply-side identity abuse is real in ride-hailing: Bolt and Uber drivers have rented out profiles; Uber says it has a zero-tolerance policy for account sharing, requires periodic real-time selfie ID checks against the profile photo, and background checks; Bolt says profile renting is fraud and drivers caught are banned — [BizNews](https://www.biznews.com/news/bolt-uber-renting-out-profiles). Fiverr limits each person to one account — [Fiverr Community Standards](https://help.fiverr.com/hc/en-us/articles/32242973123985-Our-Community-Standards)
- Yondo today (my read of the repo): one login and one React app; `apps/web/src/App.tsx` lazy-loads `Studio` and the admin console as separate chunks "ordinary visitors never download"; `/studio` is guarded by `RequireAuth role="companion"` and `/admin/*` by role admin; Studio is reached from the Account page menu (`pages/Account.tsx` lines ~117 and ~146), not the top nav; the top nav in `ui/Layout.tsx` has Discover, Favorites, Bookings, Profile, and Admin only for admins; users pick customer/companion in Account; admin cannot be self-assigned (`docs/web-and-admin.md`). Bookings.tsx already branches on `isCompanion`.

### Inferences
Option (a): one app, role switcher
- Pros: one install/link (fits Telegram link-sharing habits); one login and one OTP flow; a companion who also books needs no second account (Rover/Upwork/Fiverr pattern); one codebase, one CI, one analytics funnel (customer to companion conversion is measurable); one store listing/review cycle if native later; Studio already code-split so customers do not pay for it.
- Cons: higher risk of mode errors (Rover critique); every release touches both roles; navigation can bloat; a customer-facing store listing must also describe the companion side; supply-side features that need background/always-on behaviour are awkward in a web app.
Option (b): two entry points from one codebase (e.g. `/studio` as its own installable PWA with its own manifest `id`, `start_url`, `scope`, name/icon; or `studio.` subdomain)
- Pros: companions get a home-screen icon and a focused start screen; no second backend; reversible; keeps cross-role identity; cheap to try before any store work.
- Cons: two manifests/service-worker scopes to manage; a subdomain splits cookies/storage and complicates sessions unless auth is designed for it; deep links and push permission are per origin/scope; users can still land on the wrong entry point. A path-scoped install on one origin avoids the subdomain cost.
Option (c): fully separate products
- Pros: clean mental model; independent release cadence; role-specific permissions at install time (e.g. location "Always"); per-role store presence and ratings; can ship supply tooling that would clutter the customer app.
- Cons: two listings to review and keep compliant (Apple 4.3(a) wants meaningfully different apps, 5.1.1(v) and Play deletion apply to each); two push setups and crash dashboards; split ratings; onboarding friction for cross-role users; roughly double QA; for a small team, this is the highest fixed cost.
Cross-cutting criteria
- Onboarding friction: (a) lowest; (c) highest for a companion who is first a customer (install second app, log in again).
- Verification and safety: independent of packaging. Server-side role checks, admin approval, and identity verification gating do the work; Yondo already enforces role server-side and treats `companion` as approved-by-admin. Separate apps do not prevent a bad actor from installing both.
- Fraud ("companion pretending to be a customer", or profile renting): packaging does not solve it; evidence from ride-hailing shows identity re-verification and one-account rules are the effective controls.
- Push notifications: one subscription per origin/scope; per-role notification preferences are possible (Upwork precedent).
- Analytics: (a) simplest; (b)/(c) need cross-app identity stitching.
- Store review: the Apple/Google rules above apply per listing; a "companion" marketplace must keep positioning and copy clearly away from escort/sugar-dating wording (see policy citations) in every listing; two listings double that exposure.
- Discoverability and trust: one brand "Yondo" with a visible mode is easier to explain; a separate "Studio" listing helps companion recruiting but splits reviews.
- Maintenance cost: (a) < (b) < (c).

### Gaps
- Apple/Google rules specifically requiring an app that serves two roles to explain both roles in the listing/review notes: not found. Only the 4.3(a), 4.2, 5.1.1(v) and Play deletion rules were verified.
- Real fraud data for "supply user pretending to be customer": not found.
- Cost figures for maintaining two apps: not found; the ranking is my estimate.
- Chrome Trusted Web Activity (publishing a PWA to Google Play) docs: fetch failed due to the usage limit; not verified here.

---

## 3. How is mode switching implemented, what UX works, and what should each mode's home contain?

### Takeaway
Leading products put the switch in the profile/account area (Airbnb, Upwork, Fiverr), name the destination mode in the label, and change the whole home/tab bar; the general UX guidance is to always show the current context, make switching quick and unmistakable, and keep it separate from account settings. Bad mode design shows up as "mode errors" when two roles' screens look alike.

### Cited Findings
- Airbnb: Profile tab (app) or avatar link (web) with wording "Switch to hosting" and "Switch to traveling" — [Airbnb Help 3546](https://www.airbnb.com/help/article/3546)
- Upwork: roles added in Settings, switched from the account menu under the profile picture; separate notification settings per role — [Upwork help](https://support.upwork.com/hc/en-us/articles/17980481990291--Be-a-client-and-a-freelancer)
- Fiverr: profile dropdown "Become a Seller"/switch; creating gigs only on desktop — [Fiverr help](https://help.fiverr.com/hc/en-us/articles/360010558598-Creating-editing-your-freelancer-profile)
- Properly (property-services app): the mode switch lives in Settings and the label names the target mode (for example "Switch to 'Receive Jobs'") — [Properly help](https://help.getproperly.com/switch-roles-from-service-provider-to-property-manager)
- Workspace-switcher UX guidance: always show which context you are in; make switching fast and unmistakable; keep the switch distinct from account management — [SaaS UI: workspace switcher patterns](https://www.saasui.design/blog/saas-workspace-organization-switcher-ux-patterns)
- Rover critique: near-identical client/sitter inbox views cause "mode errors" — [Pratt IxD](https://ixd.prattsi.org/2022/09/design-critique-rover-ios-app/)
- Wolt partner app home is built around offers, pickup and drop-off tasks, and earnings; Glovo's around earnings, schedule, zone insights, one-tap acceptance; Thumbtack Pro's around lead pricing and integrations; Uzum Sellers' around balance, sales, stock, reviews, promotions, withdrawals (see section 1 sources).
- Airbnb users report the toggle disappearing in some cases (community reports) — [Airbnb Community](https://community.withairbnb.com/t5/Hosting/Airbnb-App/m-p/799489)

### Inferences
- A good Yondo switcher (judgment): a single, labelled control in the account menu and top bar for users who hold the companion role ("Mijoz rejimi / Hamroh rejimi" style; wording is the owner's), visible mode label in the header, different accent/header treatment per mode inside the allowed palette (ink/paper/carrot; do not add hues), persisted last-used mode, deep links that open the right mode (a booking-request notification opens Studio mode).
- Customer home (existing): Discovery (search/filters), Favorites, Bookings (my requests with status and pay when `accepted`), Notifications, Help/SOS where applicable, Account.
- Companion home (proposed from existing Studio features): pending booking requests (accept/decline), upcoming meetings, availability toggle/calendar, profile & service status with server `blockers`, content-approval state, earnings or payout only when the owner defines them (no invented payout rules), notifications, safety/Help. Customers must never see companion user ids (CLAUDE.md rule), which a mode switch must not weaken.
- Bookings should show two clearly separated lists in companion mode ("I booked" vs "requests to me") to avoid the Rover mode-error pattern; the file `apps/web/src/pages/Bookings.tsx` already branches on `isCompanion`.
- Do not hide the switch behind a settings page only (Properly's placement is hard to discover).

### Gaps
- Material Design and Apple HIG guidance on account/role switching: not retrieved (HIG page is JS-rendered; no fetch result).
- No quantitative usability data (error rates, discoverability) on mode switchers; only a student critique and general guidance.

---

## 4. Which "modes" do users expect in 2026, and what is necessary at launch vs excessive?

### Takeaway
Follow the system light/dark setting by default and offer an in-app override; support multiple languages and Uzbek script variants; meet WCAG 2.2 AA basics; respect reduced motion. A data-saver mode has no reliable web standard yet. Five themes and a text-size control are beyond launch needs; keep the two "Yondo" day/night themes and treat the others as optional.

### Cited Findings
- NN/g (literature review): for people with normal vision, light mode generally performs better, especially at smaller font sizes; dark mode may help some low-vision users (for example cataracts). Recommendations: do not make dark mode the default for a general audience; offer it as an option; use the OS dark-mode API so the app follows the system setting; keep it consistent across screens; do not rely on users finding the toggle — [NN/g: dark mode](https://www.nngroup.com/articles/dark-mode/)
- Android guidance: offer Light, Dark, and "System default (the recommended default option)"; dark theme "reduces power usage" (depending on screen technology), "improves visibility for users with low vision and those who are sensitive to bright light," and helps in low light — [Android Developers: dark theme](https://developer.android.com/develop/ui/views/theming/darktheme)
- WCAG 2.2 became a W3C Recommendation on 5 October 2023. New AA criteria: 2.4.11 Focus Not Obscured (Minimum), 2.5.7 Dragging Movements, 2.5.8 Target Size (Minimum) of 24x24 CSS px, 3.3.8 Accessible Authentication (Minimum); new A criteria: 3.2.6 Consistent Help, 3.3.7 Redundant Entry — [W3C: What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- `prefers-reduced-data` is experimental and, per MDN, not supported by any user agent; `Save-Data` is only listed as a related HTTP header (support not verified) — [MDN: prefers-reduced-data](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-data)
- Uzbek alphabet: the lower house passed a bill revising the alphabet on 7 July 2026; the Senate approved it on 10 September 2026. Letters Oʻ, Gʻ, Sh, Ch become Ö, Ğ, Ş, Ç (28 letters plus an apostrophe; "ng" no longer a separate letter). Documents issued under the old alphabet stay valid; textbooks to be fully converted by 2031. Cyrillic is still widely visible, and the government intends to end parallel use of the two scripts in official communication — [Times of Central Asia](https://timesca.com/uzbekistan-latin-alphabet-changes-senate/), [Kun.uz](https://kun.uz/en/news/2026/07/07/parliaments-lower-house-passes-bill-to-revise-uzbek-alphabet-848eb2). A Dunyo IA report says the president signed it on 21 October with entry into force on 22 April 2027 (search-result snippet; I did not open it) — [Dunyo](https://dunyo.info/en/news/v-uzbekskom-alfavite-poyavyatsya-bukvy-i). This matches the date already used in D:\Yondo\CLAUDE.md (2027-04-22).
- Telegram Mini Apps adapt to the user's Telegram theme in real time (`themeParams`, `colorScheme`, `themeChanged` event), authenticate via server-verified `initData`, offer a settings button, closing confirmation, native popups, `requestContact`, and can be launched from a bot menu button — [Telegram Mini Apps docs](https://core.telegram.org/bots/webapps)
- Market context: Uzbekistan had 33.1 million internet users (89.0% penetration) in October 2025, 33.9 million cellular connections, 14.1 million social-media identities, and a median mobile download speed of 55.51 Mbps (Ookla, end of 2025) — [DataReportal Digital 2026: Uzbekistan](https://datareportal.com/reports/digital-2026-uzbekistan). Android held about 82.3% of the mobile OS market in September 2026 — [Statcounter](https://gs.statcounter.com/os-market-share/mobile/uzbekistan)
- Telegram is the dominant messenger: a 2023 CA-Barometer survey found 70% of Uzbeks prefer Telegram — [CA-Barometer](https://ca-barometer.org/en/publications/which-messaging-apps-are-popular-in-uzbekistan-kyrgyzstan-and-kazakhstan); a December 2025 launch report mentions more than 27 million Telegram users and over 88% of internet-active people (search-result snippet) — [Daryo](https://daryo.uz/en/2025/12/09/wallet-in-telegram-launches-in-uzbekistan-offers-crypto-access-to-27mn-users/)
- Yondo today (my read): `apps/web/src/styles.css` defines `[data-theme='gul']`, `'rausch'`, `'stone'`, `'yondo'`, `'yondo-tun'`; it has `prefers-reduced-motion` rules at several places; root `font-size: 16px` with `-webkit-text-size-adjust: 100%`. My grep output was truncated at 40 hits, so I did not verify whether a `prefers-color-scheme` auto mode exists or whether an in-app text-size setting exists.

### Inferences
Necessary at launch (judgment):
1. Auto/system light-dark default with a manual override in Settings (NN/g and Android both point to "follow system" as the default). Map auto to `yondo` (day) and `yondo-tun` (night). Keep the theme switcher in Settings only, as the owner decided.
2. Language (uz/ru/en) and Uzbek script variants (1995 and 2026 Latin). Since the new alphabet law was reported to take effect 22 April 2027 and Cyrillic is still widely used, the owner should decide whether Uzbek Cyrillic is in scope; it is not in the current build.
3. WCAG 2.2 AA basics: contrast, 24x24 CSS px targets, visible focus not hidden by sticky bars (Yondo has a glass top bar and nav, so focus-obscured checks matter), no dragging-only actions, OTP login that allows paste/autofill (3.3.8), consistent help link placement (3.2.6, Help page exists). Carrot `#E8501A` on paper is 3.36:1 per CLAUDE.md, so it should stay graphic-only for small text (already a project rule).
4. Reduced motion respected (already present); given the owner's wish for strong motion, ensure no essential info depends on animation.
5. Graceful offline/slow-network states: a clear error and retry rather than a full offline mode.
Optional or excessive for launch (judgment):
- Five themes: each theme is an extra contrast and visual QA surface; keeping Gul/Rausch/Stone is optional extra work. If kept, they should not be allowed to fail AA.
- In-app text-size slider: rely on OS/browser font scaling and test at 200% zoom first.
- A custom "data saver" toggle: no reliable standard (`prefers-reduced-data` unsupported); a pragmatic substitute is a small default payload, lazy-loaded Studio/admin chunks (already done), responsive image sizes, and not shipping Google Fonts on slow links. A manual lite mode can wait until metrics show need.
- Full offline mode: a PWA app shell and cached last screen is enough; offline booking is out of scope and unsafe for a time-slot product.
- Per-role themes: the same theme for both modes is simpler; use a mode label and header accent instead.
- Telegram Mini App: worth considering as an additional entry point given Telegram dominance, since Mini Apps inherit Telegram's theme and give server-verifiable login; but it is an owner/roadmap choice, not a launch necessity.

### Gaps
- WCAG legal/regulatory applicability in Uzbekistan: not researched; no Uzbek accessibility regulation found.
- Apple HIG dark-mode and Material 3 theming guidance: not retrieved.
- Real device mix (RAM, Android Go share) for Uzbekistan: not found; only OS share. "Low-end Android" is from the task brief, not verified.
- Share of Uzbek users reading Cyrillic vs Latin UI: no usage data found.
- Data-saver prevalence among Uzbek users: not found.
- European Accessibility Act or other legal drivers for AA: search was cut off by the usage limit.

---

## 5. Recommendation for Yondo (criteria, staged plan, owner questions, summary)

### Takeaway
Ship one product with one login and explicit role modes (option a), add a cheap installable "Studio" entry point on the same codebase only if companions need it (option b), and postpone separate products (option c) until concrete triggers appear. This is a judgment from sections 1-4; the facts behind it are cited there.

### Cited Findings
(Recommendation relies on the cited findings in sections 1-4; no new facts are added here.)
- Peer-style marketplaces use one app and a switch (Airbnb, Fiverr, Upwork, Rover); dispatch/shift/operations-heavy supply uses a separate app (Yandex Pro, Wolt, Glovo, Uber, Bolt, Thumbtack Pro, Uzum Sellers) — section 1 sources.
- Upwork consolidated two apps into one — section 1 sources.
- Apple 4.3(a), 4.2, 5.1.1(v); Google Play deletion and sexual-content rules apply per listing — section 2 sources.
- Per-origin multi-PWA identity via manifest `id`/`start_url`/`scope` — [MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/id).

### Inferences
Decision criteria and how Yondo scores (judgment; items marked "owner?" depend on answers below):
| Criterion | Points to one app | Points to separate app |
| --- | --- | --- |
| Companion work style | async request/accept (current design) | live dispatch, offer timers, always-on location (not in current scope; owner?) |
| Cross-role users | companions also book (owner?) | strictly separate populations |
| Team size / stage | pre-launch, small team: one codebase | dedicated mobile team per app |
| Store exposure | one listing to defend on policy wording | two listings |
| Distribution | link/PWA/Telegram sharing | native-only distribution |
| Supply-side tooling | profile, services, availability, status (light) | inventory, lead pricing, integrations, payouts (heavy) |
| Verification & safety | server-side roles + admin approval (in place) | extra controls unrelated to packaging |

Ranked recommendation:
1. One app, one login, explicit role modes. Add a visible mode label and switcher for companion-role users, a distinct companion home (requests, meetings, availability, status/blockers), role-aware Bookings and notifications. Keep Studio and Admin as lazy chunks (already so).
2. Same codebase, second installable entry point (path-scoped PWA, e.g. `/studio` with its own manifest `id`, `start_url`, `scope`, name and icon) only after companions ask for a home-screen app. Avoid a subdomain unless session handling is designed for it.
3. Fully separate "Yondo Studio" product (own store listing) only if triggers appear: real-time dispatch or location features, supply-side tooling that clutters the customer app, a native team, or a large companion base with different release cadence.
Consider also (not ranked): a Telegram bot/Mini App as a notification and entry channel, given Telegram's share; owner and roadmap decision.

Staged plan (judgment):
- Now (pre-launch): finalise mode UX in the existing web app; make the system theme default map to `yondo`/`yondo-tun`; run the WCAG 2.2 AA checks listed above; keep language/alphabet switchers; decide cross-role rules (self-booking block, one account per person) with server enforcement; prepare store-safe positioning copy for any future listing.
- Launch: PWA install (manifest, icons, service worker shell); per-role notification preferences; measure how many users hold both roles and how often they switch.
- Later (traction): evaluate a path-scoped Studio PWA; evaluate a Google Play wrapper (Trusted Web Activity - not verified in this session) and Apple's 4.2 "repackaged website" risk; decide on native only if triggers in (3) appear.
- Postpone: custom data-saver mode, text-size slider, extra themes beyond the Yondo pair, Uzbek Cyrillic UI (unless owner confirms audience need).

Owner questions (decisions I cannot make for Yondo):
1. Will companions often also book other companions (cross-role use), or is the supply side a small curated group separate from customers?
2. Does the companion side need live behaviour (location sharing during a meeting, short-timer offers, shift/online status) or only asynchronous request/accept?
3. Which channels at launch: web/PWA only, Telegram bot or Mini App, native Android (and iOS)? What budget and time for store reviews?
4. Account rules: can one person have both roles on one account; may a companion book as a customer; is a one-account-per-person rule needed and how is it enforced (identity verification provider still unconfigured per `docs/web-and-admin.md`)?
5. Branding: one "Yondo" brand with a Studio mode, or a separate named product for companions?
6. Which themes and scripts must ship at launch: keep all five themes or only Yondo day/night plus auto; is Uzbek Cyrillic needed; Russian/English parity?
7. How should store listings describe the service so it clears Apple/Google rules on escort, hookup and compensated-dating content (policy wording and legal review are owner decisions)?
8. What do companions need on the home screen first (requests, calendar, earnings), noting that payout rules are not defined and must not be invented?

Plain 10-line summary:
1. Big ride/delivery platforms (Yandex, Uber, Bolt, Wolt, Glovo) split the supply side into a separate app; no company states why, but their work is shift-based and dispatch-driven.
2. Peer marketplaces (Airbnb, Fiverr, Upwork, Rover) keep both roles in one app with a profile-menu switch; Upwork even merged two apps into one.
3. TaskRabbit, Thumbtack and Uzbekistan's Uzum split because supply needs business tools; Yondo's companion tools are lighter (profile, services, availability, requests).
4. Store rules apply per listing: Apple bans multiple bundle IDs of the same app, requires account deletion; Google bans escort and compensated-dating promotion, so two listings double policy exposure.
5. Role security, verification and fraud control live on the server, not in the app packaging; ride-hailing relies on ID re-checks and one-account rules.
6. Good mode switchers show the current mode, name the target mode, and live in the account/profile menu; similar-looking screens cause mode errors (Rover).
7. Follow the system light/dark setting by default (NN/g, Android), keep the Yondo day/night pair; five themes and a text-size slider are optional.
8. Need at launch: uz/ru/en, both Uzbek Latin variants (new alphabet law reported effective 22 April 2027), WCAG 2.2 AA basics, reduced motion; data-saver mode has no stable web standard.
9. Telegram dominates Uzbekistan messaging and Android is about 82% of mobiles, so a link-shareable PWA is a better fit than two native apps now.
10. Start with one app and explicit modes; add a path-scoped Studio PWA only on demand; go fully separate only when real-time or tooling triggers appear.

### Gaps
- No Yondo business data (cross-role share, companion count, devices, budget); recommendation is conditional on owner answers.
- Trusted Web Activity / Play Store wrapper feasibility and Apple's treatment of PWA wrappers (4.2) beyond the one-line guideline: not verified.
- No evidence found on how Apple/Google reviewers treat a "companion booking" category specifically; only the policy wording above.
