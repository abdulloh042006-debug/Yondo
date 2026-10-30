# Yondo web app: page-by-page UX audit of the COMPANION (hamroh) side and the ADMIN console, with owner questions

Scope: `D:\Yondo\apps\web` (read in full for Studio, Bookings, BookingDetail, Notifications, Account/Layout routing and every `src/admin/*` page), plus `docs/companion-system.md`, `docs/web-and-admin.md`, `docs/mvp-safety-ops.md`, `TZ.md` (§4, 14, 21-27, 37-40, 45-47), `docs/WORKLOG.md` (S28-S31). Date of review: 2026-10-28. No code was changed.
Conventions: "Today" = what the code does (repo path as source). "Comparables" = external products (URL as source). "Rec" = my recommended answer to an owner question; recommendations are proposals, never existing rules. Anything that is a business rule (fee, cancellation %, refund, payout, response deadlines, price limits) is listed as an OWNER DECISION and no value is invented.
Source-quality legend used in Gaps: P = primary page fetched and read; S = search-result summary only (page itself not read or blocked); 3rd = third-party/secondary.

---

## 0. Role architecture: should customer / companion / admin have separate full-featured screens or modes?

### Takeaway
Keep ONE account, ONE codebase and ONE sign-in, but give the companion a distinct "Hamroh mode" (own home + own bottom navigation, switchable like Airbnb's "Switch to hosting"), keep admin as its separate desktop-first shell (already so), and do NOT build separate native apps before the beta. Today the companion has no home of their own: the Studio is a hidden profile-builder reachable only from Account, and bookings are one mixed list.

### Cited Findings
- Today: the mobile dock/top bar is the same for everyone: Discover, Favorites, Bookings, Profile (+ Admin for admins); there is no Studio/Hamroh entry in it. Studio is linked only from Account (menu link + button) once the "companion" role chip is on; `/studio` requires role `companion`, `/admin/*` requires role `admin` and both are lazy chunks — `apps/web/src/ui/Layout.tsx`, `src/pages/Account.tsx`, `src/App.tsx`.
- Today: becoming a companion = toggling a role chip (`PUT /auth/roles`, server replaces the whole non-admin role set; `admin` cannot be self-assigned) — `src/pages/Account.tsx`, `docs/web-and-admin.md`.
- Today: the companion's bookings are in the same `/bookings` list as their own customer bookings, distinguished only by a "Your role" row; accept/decline buttons appear only when `isCompanion && !mine && pending` — `src/pages/Bookings.tsx`.
- Today: TZ §37 specifies a companion dashboard (Today, Booking Requests, Upcoming, Calendar, Earnings, Reviews, Services, Availability, Profile, Safety); only Services/Availability/Profile exist (inside Studio) — `TZ.md` §37 vs `src/pages/Studio.tsx`.
- Comparable: Airbnb keeps guest and host in one app and one account with an explicit switch ("Switch to hosting"; back via "Traveling") — [Airbnb Help 3546](https://www.airbnb.com/help/article/3546) (S). Hosting-mode tab names reported by third parties: Listings, Calendar, Reservations, Messages, Earnings; no official list found — [Smartorder guide](https://www.smartorder.ai/resources/blog/airbnb-host-login-guide/) (3rd).
- Comparable: TaskRabbit uses a SEPARATE Tasker app from the client app, and registration is in-app only — [TaskRabbit: How do I become a Tasker](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P).
- Comparable: NN/g says wizards suit novice/infrequent processes and a faster alternative should exist for repeat use — [NN/g Wizards](https://www.nngroup.com/articles/wizards/) (P). Maps to: guided wizard for first-time onboarding, tabbed Studio for later edits.

### Inferences
- Must: (1) explicit "Become a hamroh" CTA (Profile page + public landing page) instead of a role chip; (2) a Hamroh mode switch (top bar or Profile) that swaps the dock to: Bugun (Today) / So'rovlar (Requests) / Kalendar / Profil (Studio) / Yordam; remembers last mode; (3) shared across modes: notifications, chat, SOS (always one tap), Help, Settings.
- Nice: Earnings tab shown read-only once payout rules exist; "view my public profile as customers see it".
- Probably excessive for launch: separate native/Flutter companion app; separate subdomain per role; more than three modes; per-role themes.
- Risks: a person holding both roles can confuse which role an action is in (keep a visible mode badge); companion safety needs SOS reachable in every mode; low-end phones: keep admin and studio as lazy chunks (already).
- Owner questions (closed; Rec):
  1. Can one account be both customer and hamroh? Rec: yes, with a visible mode switch (Airbnb pattern).
  2. Separate native companion app before the beta? Rec: no; mobile web/PWA mode first, decide after beta feedback.
  3. Is "Become a hamroh" a public landing page (uz+ru) before sign-up? Rec: yes — it is also the place to state what Yondo is NOT (not dating/escort).
  4. Is admin allowed on mobile? Rec: desktop-first, mobile read-only for SOS only.

### Gaps
- Official Airbnb hosting-mode tab list not found; Fiverr's "switch to selling" could not be verified (only one unreliable site returned) so Fiverr is not used as evidence. Uber/Yandex "separate driver app" not verified in this session.

---

## 1. Companion: entry point and Studio shell (`/studio`, 6 tabs)

### Takeaway
The Studio is a flat set of six equal tabs (Holat, Ariza, Profil, Xizmatlar, Rasmlar, Bo'sh vaqt) with no step order, no progress indicator and no "what next"; a first-timer must infer the order and that Application and Profile are two separate submissions.

### Cited Findings
- Today: tabs = status, application, profile, services, photos, availability, opened on "status"; each tab loads and saves independently; no autosave (explicit Save); no preview of the public card; no completeness meter — `src/pages/Studio.tsx`.
- Today: tablist buttons have `role="tab"`/`aria-selected` and `onClick` only (no arrow-key handler, no `aria-controls`), so keyboard/screen-reader behaviour of the tab pattern likely needs testing — `src/pages/Studio.tsx` L37-51.
- Today: Application and Profile each have their own submit button, both labelled with the same i18n key `studio.app.submit` — `src/pages/Studio.tsx` L173-175 and L267-269.
- Comparable: TaskRabbit's flow is a linear checklist: skills, location, verify info, at least one time slot, work-area map; then identity verification email within up to 2 working days — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P).
- Comparable: NN/g wizard rules: show a list of steps with the current one highlighted, mark completed steps, sequential order, descriptive button labels (not "Next"), allow exit/save/resume — [NN/g](https://www.nngroup.com/articles/wizards/) (P).
- Comparable: Stripe Connect onboarding supports "Save for later", re-entry links, and collecting only the currently-due information first (incremental) — [Stripe Connect onboarding](https://docs.stripe.com/connect/connect-onboarding) (P).

### Inferences
- Must: a "Setup" checklist at the top of Studio (Profile, Services, Photos, Availability, Identity, Safety orientation, Submit) with state per item (to do / done / in review / needs changes) and one primary "Continue" button; one combined "Send for review" action (UI merge; the backend can keep both states); a "How customers see you" preview; keyboard-correct tabs.
- Nice: per-field autosave drafts (low-end phones lose connectivity), profile-strength hints (no ranking promises).
- Probably excessive: gamified levels/badges, AI bio writer, video intro (TZ says photo/video; MVP = photos).
- Risks: abandonment from unclear next step; two "Submit" buttons produce a half-submitted profile (application approved, content never sent); accessibility (tab pattern); low-end phones (each tab is a separate fetch).
- Owner questions:
  1. First-time flow as a guided wizard, later edits in tabs? Rec: yes.
  2. One "Send for review" button for everything? Rec: yes.
  3. Is a "profile preview" mandatory before submit? Rec: yes, cheap and reduces rejections.

### Gaps
- No real-device keyboard/screen-reader test of the Studio tabs was run here (code reading only).

---

## 2. Companion: Application tab and identity verification

### Takeaway
Today "becoming a companion" is one free-text statement plus up to four separate gates (application approval, content approval, admin activating the account, identity verification), and the identity gate cannot be cleared in production wiring — so no companion can go public until an identity path exists.

### Cited Findings
- Today: statement textarea; Save / Submit / Withdraw (confirm dialog); statuses draft, submitted, approved, rejected, withdrawn; rejected shows the admin's `review_note`; submitted is read-only; no age/city/consent/conduct-rules step — `src/pages/Studio.tsx` (ApplicationForm).
- Today: activation requires approved application + approved content + active account + companion role + identity "verified"; default identity adapter returns `unknown`; production uses `UnconfiguredIdentityEligibility`; nothing moves a user from `verification_pending` to `active` except an admin in Users — `docs/companion-system.md`, `docs/web-and-admin.md`.
- Today: the companions backend module contains no notification calls, and the notification kinds are only booking/payment/chat/review/gift — so an applicant is NOT told when an admin approves or rejects (verified by grep in `apps/api/src/yondo_api/companions` and `src/i18n/en.ts` `notif.kind.*`).
- Comparable: TaskRabbit identity step = photo of ID + selfie on a partner site, "up to 2 working days" — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P). Eligibility there also includes 18+ and a one-time non-refundable registration fee — [TaskRabbit requirements](https://support.taskrabbit.com/hc/en-us/articles/204411070-what-s-required-to-become-a-tasker) (S); a fee for companions is NOT proposed here (owner decision).
- Comparable: Uber document review "may take up to 48 hours" in the US page and "up to 2 hours" on the Australian page; upload tips: full document visible, one file at a time — [Uber docs (AU)](https://www.uber.com/au/en/drive/sydney/get-started/uberx-docs), [Uber docs (US)](https://www.uber.com/ie/en/drive/requirements/documents/?city=akron) (S). Background check 3-10 business days is a third-party estimate — [Gridwise](https://gridwise.io/blog/uber-background-check) (3rd).
- Comparable: Yandex Taxi driver identity uses selfie + short voice recording, ">90% accuracy" (company claim) — [Yandex blog](https://www.yandex.com/company/blog/new-ai-driver-identification-system-for-yandex-taxi) (S).
- Comparable: Thumbtack uses Checkr background checks and a badge; sources disagree whether it is mandatory for all pros; no published list of disqualifying offences; pros have a dispute path — [Thumbtack safety](https://www.thumbtack.com/safetyguidelines/), [Lemberg Law](https://lemberglaw.com/thumbtack-background-check-error-dispute/) (S/3rd).
- Comparable (Uzbekistan): MyID (UZINFOCOM) = remote biometric identification with liveness, backed by State Personalization Center data, iBeta ISO 30107-3 test cited, products: mobile SDK, Web SDK, server SDK, Cloud; docs at docs.myid.uz; pricing not published; partnership application via the site — [MyID](https://myid.uz/en/) (P). OneID appears as the "Unified Identification System" — [dgov.uz](https://dgov.uz/en/identification/) (S, not read).
- Legal (Uzbekistan): a March 2026 amendment narrowed data localization but reportedly keeps biometric data tied to servers inside Uzbekistan — [Kun.uz](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems) (3rd news; effective date and text not verified).

### Inferences
- Must: structured application (age 18+ confirmation, city, languages, services wanted, short "why", conduct-rules acceptance incl. "not dating/escort"); ONE identity step before first public listing; "needs changes" state separate from "rejected"; rejection with category + which section to fix + appeal route; a notification on every decision (in-app + an off-app channel); store only the verification RESULT and provider reference, not ID images (privacy-by-minimum; also avoids biometric-localization issues).
- Nice: MyID Web/mobile SDK once a partnership exists; reference/vouch from an existing companion.
- Probably excessive at beta: mandatory criminal-record checks, video interview for everyone, application fee.
- Risks: companion safety/fraud: fake profiles with stolen photos, minors, coerced or third-party-controlled accounts (the category is adjacent to escort, so expect hostile actors — payout-to-third-party and many accounts per device are signals); privacy: ID/biometric data retention; fairness: unexplained rejections; moderator workload: every re-submission re-opens review.
- Owner questions:
  1. Identity before first public listing, mandatory? Rec: yes (server already enforces).
  2. For the beta, manual identity check by an admin (video call or in-person, passport seen, nothing copied, only a "verified" flag + audit note) until MyID is contracted? Rec: yes — needs a small admin write path (today the adapter is read-only).
  3. Minimum age 18, stated on landing and in the form? Rec: yes.
  4. Do you commit to a review time to show applicants? Rec: only a number you can staff (e.g., "usually within N working days"); otherwise show "submitted on <date>" only.
  5. Background checks at beta? Rec: no; decide after beta.
  6. After a rejection can the applicant resubmit unlimited times? Rec: yes, but after 3 rejections require a support conversation.

### Gaps
- MyID integration cost, contract steps and API details not public (docs.myid.uz not read); OneID details not read. Whether a "criminal record certificate" can be obtained digitally in Uzbekistan was not researched. Biometric-localization rule is from news, not the statute.

---

## 3. Companion: Profile tab (name, bio, languages, interests)

### Takeaway
The form is simple, but languages and interests are comma-separated free text (while customers filter by language), and every edit to an approved profile silently de-lists the companion until an admin re-approves — the single biggest operational and UX cost for a small beta.

### Cited Findings
- Today: fields display_name (128), bio (8000), languages and interests as comma-split text; Save and Submit are separate; editable when draft/rejected/approved, locked while pending; text warning "any edit cancels approval" but no confirmation before saving — `src/pages/Studio.tsx` ProfileForm, `src/i18n/en.ts` `studio.profile.editWarning`.
- Today: any profile, service, photo, caption or order mutation sets content to draft and inactive; availability edits do not; languages/interests stored as bounded JSON arrays, case-insensitively unique, "no new taxonomy is invented" — `docs/companion-system.md`.
- Comparable: Fiverr asks for profile photo, accurate professional background, skills; moderation looks at profile accuracy; denied gigs are fixed and resubmitted — [Fiverr Gigs best practices](https://help.fiverr.com/hc/en-us/articles/360010452317-Gigs-best-practices), [Creating a Gig](https://help.fiverr.com/hc/en-us/articles/360010451397-Creating-a-Gig) (S; the help page returned HTTP 403 when fetched).
- Comparable: TaskRabbit chooses skills from categories, not free text (S) — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P for the "set your skills" step).

### Inferences
- Must: language and interest pick-lists (chips, with "other"); bio min length + prompts + counter; confirm dialog before saving edits to an approved profile; ideally keep the approved version live while the edited version is reviewed (needs backend; otherwise a companion who fixes a typo vanishes from search); contact-details detector (phone, @handle, links) with a clear message — off-platform leakage and safety.
- Nice: bio prompts in uz/ru; "translate hint"; show previous rejection note next to the field.
- Probably excessive: rich text, social links, video bio.
- Risks: sexualised or contact-sharing wording conflicts with the brand rule; moderators need written guidelines in uz and ru; inconsistent spellings break language filters; low-end phones: long textareas OK.
- Owner questions:
  1. Should an edit to an approved profile keep the old version live until the new one is approved? Rec: yes (needs backend work); minimum for beta: confirm dialog + exempt trivial fields.
  2. Are phone numbers/Telegram handles/links forbidden in bio? Rec: yes, auto-detect.
  3. Fixed list of languages/interests? Rec: yes, owner supplies the lists (uz, ru, en, tg, kk, ko, tr ... + other).

### Gaps
- Which fields count as "material" for re-review is an owner decision, not found in repo.

---

## 4. Companion: Services and prices tab

### Takeaway
Service setup is clean (catalog code + price per unit + 30/60/90/120 min + description), but it lacks the rules that make a booking safe and unambiguous: who pays venue costs, minimum notice, buffer between meetings.

### Cited Findings
- Today: catalog of 10 codes (coffee, walking, cinema, shopping, event, city_friend, conversation, study, online_call, custom_experience), one row per code; price typed in UZS and stored as integer tiyin (x100); unit 30/60/90/120; description up to 2000; delete with confirm; any change returns the profile to draft — `src/pages/Studio.tsx` ServicesTab/ServiceForm, `src/lib/labels.ts`.
- Today: platform fee, delivery fee, cancellation %, refund and payout are undecided; UI must show "Aniqlanmagan" — `CLAUDE.md` §4; `TZ.md` §21, §26.
- Comparable: TaskRabbit Taskers "set your own rates" and pick service categories — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P for categories; "own rates" from S [Gerald guide](https://joingerald.com/learn/work--income/taskers-guide), 3rd).
- Comparable: Airbnb service listings offer hour-based advance notice and preparation time from 15 minutes to 6 hours — [Airbnb Help 3949](https://www.airbnb.co.in/help/article/3949) (S); Airbnb stays: advance notice (same-day cutoff or 1-7 days), prep time before/after, availability window 3-24 months — [Airbnb Help 1353](https://www.airbnb.com/help/article/1353), [Airbnb resource 322](https://www.airbnb.com/resources/hosting-homes/a/navigating-every-step-of-the-booking-process-322) (S).

### Inferences
- Must: live formatted price echo ("50 000 so'm") to prevent a 100x typo; "what is included / who pays tickets, coffee, transport" line shown on the service card; minimum notice and buffer settings per companion; examples next to description; clear unit meaning (price per unit of N minutes).
- Nice: price band hints only after real booking data exists (do not invent numbers); duplicate a service.
- Probably excessive: packages, discounts, tips, dynamic pricing, multi-currency.
- Risks: `custom_experience` is open-ended and a moderation/safety hole; price used as a proxy for sexualised services; wrong unit assumptions → customer disputes; accessibility: ensure numeric input has visible currency.
- Owner questions:
  1. Who pays venue costs (cafe bill, tickets) — each pays own, or customer covers? Rec: state explicitly per service, paid directly between them, not through the platform at beta.
  2. Hide `custom_experience` (and `online_call` unless call policy exists) at beta? Rec: hide custom_experience.
  3. Minimum notice default and booking length minimum? Rec: companion-settable with owner defaults (e.g., 60 min, a few hours' notice) — numbers are yours to set.
  4. Any price floor/ceiling? Rec: none at beta, only a soft warning.

### Gaps
- How the server computes the booking price from unit/duration not re-verified here.

---

## 5. Companion: Photos tab

### Takeaway
Upload/delete works but gives no guidance, no ordering, no per-photo status, and on the free demo hosting the storage adapter is missing so uploads are unavailable; photos are the highest-risk content for both trust and moderator workload.

### Cited Findings
- Today: upload JPEG/PNG/WebP, delete with confirm, "№ n" label; reorder and caption endpoints exist but are NOT IMPLEMENTED in the UI; note "photos are reviewed by an administrator; any change returns the profile to draft"; no min/max count, size limit, upload progress, or photo rules shown — `src/pages/Studio.tsx` PhotosTab, `docs/web-and-admin.md`.
- Today: server strips EXIF/location, re-encodes JPEG, rejects animation; first ordered photo is primary — `docs/companion-system.md`.
- Today: only the `ObjectStorage` protocol exists; with no adapter photo upload returns 503 ("unavailable") — `docs/WORKLOG.md` S29 "Not done: S3/MinIO adapter".
- Comparable: Uber document capture guidance (full document visible, one file at a time, not photocopies) — [Uber docs](https://www.uber.com/au/en/drive/sydney/get-started/uberx-docs) (S).
- Comparable: WCAG 2.2 Dragging Movements (2.5.7, AA) requires a non-drag alternative for drag-reorder; Target Size Minimum (2.5.8, AA) 24x24 CSS px — [W3C What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) (P).
- Comparable (moderator exposure): practitioner sources stress moderator wellbeing for harmful content and rotation — [TSPA events](https://www.tspa.org/explore/events/past-events/) (3rd), [moderation playbook](https://playbooks.com/skills/gtmagents/gtm-agents/moderation-safety-playbook) (3rd).

### Inferences
- Must: photo-rules panel with good/bad examples (face clear, only you, no minors, no watermarks/contacts, no explicit content); min and max count; client-side downscale/compress before upload (cheap Android cameras produce multi-MB files); progress + retry; reorder via up/down buttons (not drag only); per-photo review status and reason (today all-or-nothing); the storage adapter before any beta.
- Nice: crop to the 3:4 card; duplicate/stolen-image check link for admins; optional captions.
- Probably excessive: video, filters, AI enhancement, face-blur tooling.
- Risks: stolen/stock photos, third parties or minors in photos, explicit uploads (quarantine and hash-block), photo retention after deletion vs account-deletion policy, moderator exposure, cultural sensitivity about publishing a face (trust vs personal safety).
- Owner questions:
  1. Minimum photos to apply (Rec: 3) and maximum (Rec: 6)?
  2. Must the main photo show the face clearly? Rec: yes for verified listings — but decide whether a "blurred until booking confirmed" option is allowed for safety/cultural reasons.
  3. Is the ID selfie (liveness) separate from gallery photos? Rec: yes, never published.
  4. Which storage provider and where hosted (in-country)? Rec: decide with the server stage; required before beta.

### Gaps
- Face-detection/duplicate-photo tooling costs not researched.

---

## 6. Companion: Availability tab

### Takeaway
Availability is one-off date-time windows entered one by one with a fixed UTC+5 offset; there is no weekly pattern, calendar view, edit, or view of existing bookings, which will make a companion's weekly upkeep slow and error-prone.

### Cited Findings
- Today: two `datetime-local` fields, converted with a hard-coded `+05:00` and sent as `Asia/Tashkent`; list with delete only (no edit); no recurring rule; no display of bookings on the calendar; availability changes do not trigger re-review — `src/pages/Studio.tsx` AvailabilityTab, `docs/companion-system.md`.
- Today: discovery's availability filter = full containment; booking conflicts stay in force — `CLAUDE.md` §4.
- Comparable: Fresha repeating shifts (every 1-4 weeks) with clients able to book only inside shifts, blocked time for exceptions — [Fresha help](https://www.fresha.com/help-center/knowledge-base/calendar/252-schedule-and-update-team-shifts) (S).
- Comparable: Airbnb advance notice, preparation time and a 3-24 month availability window — [Airbnb Help 1353](https://www.airbnb.com/help/article/1353), [resource 322](https://www.airbnb.com/resources/hosting-homes/a/navigating-every-step-of-the-booking-process-322) (S). TaskRabbit requires at least one slot at onboarding — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P).
- Booksy: no official source found (see Gaps).

### Inferences
- Must: weekly template ("Mon-Fri 18:00-22:00") that generates windows for the next N weeks; month/week calendar showing windows + pending/confirmed bookings; edit and "block this day"; visible timezone label; 15/30-minute step time selectors for phones; a conflict warning when deleting a window with a confirmed booking.
- Nice: ICS export; "pause bookings" (the existing Unlist toggle can be labelled this way); reminders to refresh availability.
- Probably excessive: two-way Google/Apple calendar sync, multi-timezone, team calendars.
- Risks: companion safety — night-time or isolated slots chosen without guidance (platform policy needed); stale availability → declines/expiry hurt customers; hard-coded offset is correct today (Uzbekistan has one zone) but breaks if the product expands; accessibility of datetime-local on low-end Android browsers.
- Owner questions:
  1. Weekly template at beta? Rec: yes.
  2. How far ahead can customers book? Rec: owner picks (e.g., 2-4 weeks) and shows it.
  3. Latest allowed start time for meetings (e.g., no starts after a set hour)? Rec: yes, a safety default you set; companion can only be stricter.
  4. Must the meeting place be a public venue (stated in booking flow)? Rec: yes, policy text plus customer-side rule.

### Gaps
- Booksy calendar/request behaviour not verified; Fresha manual-approval behaviour not found.

---

## 7. Companion: Status tab (review status, blockers, activate/unlist)

### Takeaway
The status tab shows four raw statuses and a blockers list, which is honest but gives no timeline, no owner of the next step, no time expectation, and a permanent dead end ("identity verification is not connected yet").

### Cited Findings
- Today: tag "Visible/Hidden" + application, content, account, identity statuses; blockers mapped from server codes (application_not_approved, content_not_approved, account_not_active, companion_role_required, identity_not_verified); Activate disabled unless content approved; Unlist toggles intent; static note "content approval is not identity verification" — `src/pages/Studio.tsx` StatusTab, `src/lib/labels.ts`, `src/i18n/en.ts` `studio.status.*`, `blocker.*`.
- Today: `publicly_active` is computed server-side from all gates each time; activation_requested is only intent — `docs/companion-system.md`.
- Comparable: Stripe exposes requirement lists (currently_due / eventually_due), lets users "Save for later", and says to send users back into the flow when new requirements appear; "update my verification information" entry point — [Stripe Connect onboarding](https://docs.stripe.com/connect/connect-onboarding) (P).
- Comparable: TaskRabbit emails each verification step; Uber shows document review time (hours to 48h) — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P), [Uber](https://www.uber.com/au/en/drive/sydney/get-started/uberx-docs) (S).

### Inferences
- Must: a timeline (Submitted, Under review, Identity, Approved, Live) with dates; each blocker has a plain-language action and a "waiting for you / waiting for Yondo" label; no internal notes shown; neutral wording for suspended/banned plus appeal route; notification at every change; collapse "account active" into the same review outcome from the user's viewpoint.
- Nice: "profile strength" and photo tips (no ranking promises until ranking is designed).
- Probably excessive: public ranking explanations, tiers/badges.
- Risks: opaque waiting → support tickets (support is in-app only → admin workload); anxiety/harassment of reviewers; showing admin notes can leak moderator identity or internal reasoning.
- Owner questions:
  1. Auto-go-live once all gates pass, or keep an explicit "Go live" button? Rec: explicit button as the last checklist step (companion controls timing).
  2. Do you publish a review-time promise? Rec: only if staffed (see §2 Q4).
  3. Appeal route for rejection/suspension = in-app support form with application reference? Rec: yes.

### Gaps
- No evidence on how long real manual reviews will take (no data yet).

---

## 8. Companion: Bookings list (requests, accept/decline)

### Takeaway
The booking list is functional but blind and flat: no customer information to decide on, no deadline, no decline reason, no separation of "needs your answer" from history.

### Cited Findings
- Today: one list (limit 50, no tabs/filters/paging); card = service, status, time range, place, price, "Your role"; companion buttons Accept / Decline only when `pending`; Decline posts `{reason: ''}`; Cancel on pending/accepted/confirmed; Report and Block (via booking id) on every card; SOS on confirmed/active — `src/pages/Bookings.tsx`.
- Today: pending/accepted bookings whose start has passed become `expired` via the periodic job (slot released, cannot be accepted/paid); no countdown is shown in the UI — `apps/api/src/yondo_api/bookings/expiry.py`, `CLAUDE.md` §7 (S25).
- Today: no customer name, rating or trust data is shown to the companion (privacy by design); realtime chat is not wired; notifications are in-app only — `src/pages/BookingDetail.tsx`, `src/pages/Notifications.tsx`.
- Comparable: Airbnb expects hosts to accept or decline within 24 hours; a decline counts as a response, silence is a "late response"; response rate/time can affect search placement — [Airbnb Help 2414](https://www.airbnb.com/help/article/2414) (P).
- Comparable: request-to-book tools put pending requests in an "Unconfirmed" tab with reject-with-reason, and some auto-decline after 24 hours — [Cal.com](https://cal.com/docs/how-to-guides/how-to-set-up-requires-confirmation), [Cowlendar](https://help.cowlendar.com/how-to-calendar/confirm-or-decline-new-bookings-manually) (S).

### Inferences
- Must: "Needs your answer" block on top with a reply-by time; Requests / Upcoming / Past tabs; preset decline reasons (optional); a minimal customer card before accepting (first name or alias, phone-verified, number of completed bookings, companion-given ratings) — each field subject to owner privacy decision; request details incl. place and a short safety reminder; penalise silence, never declines (Airbnb logic).
- Nice: suggest-another-time; quick replies; calendar overlay.
- Probably excessive at beta: auto-accept (Instant Book) rules; analytics; bulk actions.
- Risks: companion safety — meeting an unknown person at a customer-chosen place; response-rate pressure pushing companions to accept unsafe requests; missed requests (no off-app alert) = lost bookings; privacy leakage in notification previews; harassment through repeated requests (block exists via booking).
- Owner questions:
  1. Response window for a request (yours to set) and what happens on silence (auto-expire)? Rec: set a window and show the deadline; expire without penalty at beta.
  2. What customer info does the companion see before accepting? Rec: alias/first name + verified phone + completed count + reviews; no phone number.
  3. Instant booking without acceptance? Rec: no at beta.
  4. Are decline reasons required? Rec: optional presets.
  5. Companion cancel of a confirmed booking: consequences? OWNER DECISION (cancellation/refund % undecided); Rec: show a neutral warning, no numbers.

### Gaps
- Whether the server enforces any response deadline is not documented.

---

## 9. Companion: Booking detail (payment view, check-in/start/finish, chat, review, safety)

### Takeaway
One long page with six stacked sections works as a record but not as a "what do I do now" screen; the companion needs a single next action, a pre-meeting safety brief, and clarity on money (which is undecided).

### Cited Findings
- Today: sections = summary, Payment (customer-only pay; companion sees a note), Meeting (check-in, start only when both arrived, end), Chat (polls every 8 s while visible; "You/Them" labels; read-only after completion), Review (1-5 stars + comment after completed), Safety (Report, SOS) — `src/pages/BookingDetail.tsx`.
- Today: SOS = a recorded alert for manual review; never claims emergency services or tracking — `CLAUDE.md` §4; `docs/mvp-safety-ops.md`.
- Today: no earnings/payout line, no map link for the meeting place, no end-meeting confirmation, no no-show action; payment provider not connected (DEMO provider only) — `src/pages/BookingDetail.tsx`, `docs/WORKLOG.md` S29.
- Comparable: WCAG 2.2 consistent help location (3.2.6, A) and 24x24 px targets (2.5.8, AA) — directly relevant to keeping SOS/Report in one predictable place — [W3C WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) (P).
- Comparable: in Uzbekistan Telegram is the preferred messenger (70% in a December 2023 survey; WhatsApp 18%) — [CABAROMETER](https://ca-barometer.org/en/publications/which-messaging-apps-are-popular-in-uzbekistan-kyrgyzstan-and-kazakhstan) (S) — relevant to why in-app polling chat alone will be missed.

### Inferences
- Must: top "Next step" card driven by status (Pay pending / Check in / Start / End); safety brief shown before check-in (public place, tell a trusted contact, what SOS does and does not do); end-meeting confirmation; map link to the place; for companion: "Amount for this booking" with "payout: rules to be announced" (no invented timing); no-show report action (TZ §22) routed to admin; SOS always visible.
- Nice: post-meeting "Are you OK?" one-tap prompt; quick-reply templates; masked call.
- Probably excessive: live location tracking (contradicts the no-tracking SOS promise), voice messages, translation.
- Risks: highest-severity area for companion safety; chat harassment/contact exchange; stale 8-second polling; check-in without proof; disputes with no decided refund/payout rules.
- Owner questions:
  1. Check-in allowed from how many minutes before start? OWNER DECISION; Rec: a short window you set.
  2. No-show process (who decides, effect on money)? OWNER DECISION (TZ §22 defers rules).
  3. Mandatory safety brief acknowledgement on the companion's first booking? Rec: yes.
  4. Post-meeting safety check prompt? Rec: yes, optional one tap.

### Gaps
- Server rules for check-in timing not examined in detail.

---

## 10. Companion: home/dashboard, notifications and earnings (partly missing)

### Takeaway
Notifications are an in-app list with no unread badge, no off-app channel and no kinds for application/identity/support/safety events; there is no companion "Today" home and no earnings view. Both belong in the beta minimum, with earnings kept read-only.

### Cited Findings
- Today: list of 50, kind label + time + "new" tag + link to booking, "read all"; no preferences; kinds: booking_requested/accepted/declined/cancelled, payment_confirmed, chat_message, review_reminder, gift_*; no application/content/identity/account/support/safety kinds — `src/pages/Notifications.tsx`, `src/i18n/en.ts` L800-812.
- Today: no unread count in the nav items — `src/ui/Layout.tsx`.
- Today: TZ requires Today, Earnings, Reviews, Calendar for companions and "Customer -> Platform -> completed -> payout; dispute pauses payout"; percentages only after the business model is approved — `TZ.md` §21, §27, §37.
- Comparable: TaskRabbit sends an email at each verification step — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P). Telegram is the dominant messenger in Uzbekistan (70% preference, Dec 2023 survey) — [CABAROMETER](https://ca-barometer.org/en/publications/which-messaging-apps-are-popular-in-uzbekistan-kyrgyzstan-and-kazakhstan) (S).
- Comparable: Stripe Connect collects payout/bank details incrementally, only when needed, and exposes enabled/restricted state — [Stripe](https://docs.stripe.com/connect/connect-onboarding) (P).
- Legal context (not advice): self-employed registration in Uzbekistan is described as free via the Soliq app/tax office; a 1% turnover tax for sole proprietors/self-employed up to 1 bn UZS from 1 Jan 2026 is reported; figures are from non-official pages — [Solarstaff](https://help.solarstaff.com/en/articles/9250017-freelance-and-taxes-uzbekistan) (3rd), [Fergana](https://en.fergana.agency/news/139408/) (3rd news).

### Inferences
- Must: companion lifecycle notifications (submitted, needs changes, approved, rejected with reason, identity result, account active/suspended, support reply, new booking request with reply-by time); an off-app channel for new booking requests; unread badge on the dock; a Today home (next booking, requests waiting, setup status); Earnings = read-only list of completed bookings and amounts with "payout rules will be announced" until the owner decides.
- Nice: quiet hours; Telegram bot with opt-in deep link; weekly digest.
- Probably excessive: e-mail channel (support is in-app by design), balance charts, tax reports, web-push on iOS.
- Risks: missed requests; notification text on lock screens revealing meeting details (keep generic); SMS cost; Telegram requires linking phone to chat id (privacy); payout/tax obligations of companions (legal status) unresolved.
- Owner questions:
  1. Beta off-app channel: Telegram bot (opt-in) or SMS? Rec: Telegram opt-in for requests; SMS only for OTP/critical.
  2. Lock-screen text generic ("You have a new request")? Rec: yes.
  3. Payout method and schedule? OWNER DECISION (not decided); Rec: if the beta uses real money, run manual payouts with a ledger and say so honestly.
  4. Must companions be registered as self-employed (or other status) before payouts? OWNER/LEGAL DECISION; Rec: get a lawyer/accountant answer before the first payout.
  5. Do companions rate customers (TZ §4)? Rec: yes, private to staff at beta.

### Gaps
- Payment provider (CLICK/Payme) payout capabilities not researched; official Soliq pages not read; no Uzbek-specific marketplace payout precedent verified.

---

## 11. Shared pages: Settings, Terms/Privacy, Help (as used by companions)

### Takeaway
Shared pages are solid for a first launch, but nothing in them is companion-specific (no companion rules, no companion terms, no companion FAQ beyond "How do I become a companion?"), and there are more visual/text variants than a small team can QA.

### Cited Findings
- Today: Settings = language uz/ru/en, two Uzbek alphabets (1995 default until 2027-04-22, then 2026), 5 themes, account groups; Terms/Privacy are separate versioned pages with consent recorded at login; Help = 112, reports, trusted contacts, FAQ, in-app support request, beta feedback — `CLAUDE.md` §7, `docs/web-and-admin.md`, `src/pages/Help.tsx`.
- Today: operator name, backup retention and job scheduling are still owner/ops items; `privacy.md` §10 "Shriftlar" bullet is untrue after fonts became self-hosted; native-speaker review of uz/ru/en is pending — `docs/WORKLOG.md` S28 and Next steps.
- Comparable: WCAG 2.2 Consistent Help (3.2.6) and Redundant Entry (3.3.7) — [W3C WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) (P).

### Inferences
- Must: a one-page "Companion rules" (uz+ru) acknowledged at application: no dating/escort, no contact exchange, public places, conduct, consequences; a short companion addendum to Terms (independent status, cancellations, payouts "as announced"); companion Help section (safety tips, what SOS does, review process, payouts "to be announced"); support categories for companion/payment/safety; Help always in the same place.
- Nice: simple glossary of statuses.
- Probably excessive for launch: all 5 themes and both alphabets as first-class QA targets — keep the two Yondo themes visible and move the rest to an "Extra" group; alphabet choice stays because of the 2027 transition.
- Risks: legal text not final (operator name); machine-quality translation errors in rules text; heavy glass/blur/aurora effects on low-end phones (not measured here — flagged as a test item).
- Owner questions:
  1. Separate companion rules + addendum before beta? Rec: yes.
  2. Hide the three non-Yondo themes at launch? Rec: yes (owner rule says Yondo themes only; others add QA).
  3. Is a published support response time acceptable? Rec: only if staffed.

### Gaps
- No performance measurement on low-end Android was done.

---

## 12. Admin: shell, authentication and navigation

### Takeaway
The console is server-authorized and carefully scoped, but it has a single undifferentiated admin role, SMS-OTP-only sign-in, and no logging of data viewing — acceptable for 2-3 trusted admins only if hardened before real users arrive.

### Cited Findings
- Today: `/admin/*` guarded by role `admin` (client) AND by server authorization on every endpoint; nav has 8 items (Overview, Applications, Safety, Users, Support, Deletions, Bookings, Audit); no role differentiation inside admin — `src/admin/routes.tsx`, `src/admin/shared.tsx`, `docs/web-and-admin.md`.
- Today: first admin is created by a direct DB insert; `PUT /auth/roles` refuses `admin`; admins and self cannot be status-changed from Users — `docs/web-and-admin.md`.
- Today: audit rows are written for decisions/acknowledgements/status changes/replies/erasure; viewing photos, reports or SOS is not listed as an audited action — `docs/web-and-admin.md`.
- Comparable: WCAG 2.2 Accessible Authentication (3.3.8): code transcription is a cognitive function test unless paste/autofill or another method is allowed — [W3C WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) (P).
- Comparable: triage practice = severity/reversibility first, then volume/SLA, with predefined escalation points — [startup.jobs T&S](https://startup.jobs/interview-questions/trust-safety-specialist), [moderation playbook](https://playbooks.com/skills/gtmagents/gtm-agents/moderation-safety-playbook) (3rd).

### Inferences
- Must: named personal admin accounts only; a second factor or step-up for admin sign-in (SIM-swap risk on SMS OTP); idle session timeout; log VIEW of ID/photos/reports/SOS (not only decisions); allow OTP paste/autofill.
- Nice: two permission levels (moderation vs support) when team exceeds ~3; IP allow-list.
- Probably excessive: granular RBAC, SSO, custom dashboards for 2-3 admins.
- Risks: account takeover exposes private photos, SOS and the ability to ban users; insider misuse; a single admin on leave leaves SOS unwatched.
- Owner questions:
  1. Who are the admins at beta (names, count, backups)? Rec: 2-3 named + 1 on-call rota.
  2. Require a second factor for admins before any real user? Rec: yes.
  3. Log every view of sensitive data? Rec: yes.

### Gaps
- Stripe/Shopify admin role-model documentation not fetched; comparison is by general practice.

---

## 13. Admin: Dashboard (`/admin`)

### Takeaway
Seven real counters with links, but no ages/SLAs, no auto-refresh and no alert channel — an unacknowledged SOS only exists if an admin happens to open the page.

### Cited Findings
- Today: tiles = submitted applications, pending content (both capped at "100+"), open reports, unacknowledged SOS, users, bookings, payments; banner that numbers are real; a card listing unconnected features; flag showing emergency dispatch is not configured — `src/admin/Dashboard.tsx`.
- Today: no responder paging, no on-call, no incident SLA; "do not enable a closed beta with real safety-critical reliance until human and technical escalation operations are approved" — `docs/mvp-safety-ops.md`.
- Comparable: practitioner T&S guidance — severity first, central incident log, predefined escalation points — [startup.jobs](https://startup.jobs/interview-questions/trust-safety-specialist), [playbook](https://playbooks.com/skills/gtmagents/gtm-agents/moderation-safety-playbook) (3rd).
- Success metrics defined by TZ §47: signup conversion, verified users, companion supply, search to profile and profile to booking conversion, completion, cancellation, no-show, repeat, rating, report rate — `TZ.md` §47.

### Inferences
- Must: SOS tile first and visually dominant with "oldest waiting: N min"; "oldest waiting" on every queue; polling refresh for SOS; an alert to the on-call admin (Telegram/SMS) when an SOS is created; "meetings active now" count.
- Nice: 6-8 beta metrics from TZ §47 with CSV export.
- Probably excessive: charts, BI, risk scores, live maps.
- Risks: unattended SOS (liability and real harm); "payments" count mistaken for revenue; cap hides true queue size.
- Owner questions:
  1. Who watches SOS during meeting hours, and what is the target acknowledgement time? OWNER DECISION; Rec: named on-call with a phone alert during evening/weekend hours.
  2. Does the SOS dialog text stay "recorded for manual review"? Rec: yes, never promise help.
  3. Which five metrics on the dashboard? Rec: requests, acceptance rate, completion, cancellations/no-shows, reports.

### Gaps
- No evidence on real SOS volume (none yet).

---

## 14. Admin: Companion applications and content review

### Takeaway
The review screen shows the right material (statement, profile, services, photos, history) with revision-safe decisions and mandatory notes, but it forces two separate decisions, offers no rubric or reason templates, no "needs changes", no queue ordering/claiming, and no applicant context.

### Cited Findings
- Today: list filters (submitted, content pending, approved, rejected, all), 25 per page; rows show display name, date, short user id, two status tags; detail shows application block, profile block (name, languages, interests, activation requested, bio, services with prices, photo gallery via signed URLs) and an audit history for the user; decisions through a dialog with a mandatory note (approve >= 3, reject >= 8 characters) and stale-revision refusal — `src/admin/Applications.tsx`.
- Today: no applicant age/city/phone-masked/account status on the detail; no identity panel; no canned reasons; no assign/claim; decisions for application and content are separate; account activation is a third action on the Users page — `src/admin/Applications.tsx`, `src/admin/Users.tsx`.
- Comparable: Fiverr — automatic review then fix-and-resubmit, identity (KYC) required to publish — [Fiverr](https://help.fiverr.com/hc/en-us/articles/360010451397-Creating-a-Gig) (S, page 403).
- Comparable: TaskRabbit up to 2 working days; Uber hours to 48h — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P), [Uber](https://www.uber.com/au/en/drive/sydney/get-started/uberx-docs) (S).
- Comparable: Thumbtack lets pros dispute background-check results — [Lemberg Law](https://lemberglaw.com/thumbtack-background-check-error-dispute/) (3rd); principle reused: give reasons and a route to challenge.
- Comparable: Cal.com lets the provider reject with a reason that is sent to the requester — [Cal.com](https://cal.com/docs/how-to-guides/how-to-set-up-requires-confirmation) (S).

### Inferences
- Must: one review page per applicant with a checklist rubric (photos real and clear, no minors/others, no contact info, bio not sexualised, services valid, prices sane, identity verified) and canned rejection reasons (+ free text, uz/ru); "needs changes" (specific items) distinct from reject; oldest-first sort with age badge; claim/lock to avoid two admins reviewing; applicant context (age, city, masked phone, account age, prior rejections); the account-active and identity actions on the same screen (or linked); notification to the applicant.
- Nice: diff versus the last approved version; second-opinion flag; internal notes; link for reverse image search.
- Probably excessive: ML scoring, auto-approval, full case management for 20 companions.
- Risks: moderator workload (edit-triggered re-review multiplies cases), inconsistent decisions without a rubric, explicit-image exposure (rotate, blur-by-default), wrongful rejection without appeal, privacy of rejected applicants' photos (retention).
- Owner questions:
  1. Written moderation guidelines (uz+ru) before the first review? Rec: yes, owner drafts one page.
  2. Add "needs changes"? Rec: yes.
  3. Order of checks: identity first, then content? Rec: yes (cheaper to reject early).
  4. Second reviewer for the first N approvals? Rec: single reviewer + spot-check of the first 20.
  5. Retention for rejected applicants' photos? OWNER/LEGAL DECISION.

### Gaps
- Fiverr/Upwork moderation internals are not public; Upwork was not researched.

---

## 15. Admin: Users

### Takeaway
A safe, deliberate status-change tool (reason + typed id + protected admins), but with no user detail page it cannot answer "what is the history of this person?".

### Cited Findings
- Today: filters = account status and phone search; table = short id (click to expand), masked phone, roles, status, city, registered, action; status dialog: new status (active, verification_pending, restricted, suspended, banned; not deleted), reason >= 8 chars, typed 8-char id, red banner for non-active; admin and self rows protected; deleted rows without action — `src/admin/Users.tsx`.
- Today: TZ §39-40 list approve/reject/warn/restrict/suspend/ban and statuses active, verification pending, restricted, suspended, banned; no "warn" and no definition of what restricted vs suspended means for bookings in flight — `TZ.md` §39-40.
- Comparable: Stripe-style and marketplace admin consoles centre on an object detail page with a timeline and related objects (general practice; no single source fetched).

### Inferences
- Must: user detail (roles, status history from audit, application/profile link, bookings, reports filed/against, support tickets, deletion request); defined consequences per status; a "warn" action; reasons visible to the user in neutral form; appeal route.
- Nice: strike counter, duplicate-phone/device flag, CSV export.
- Probably excessive: bulk status changes, automated risk score.
- Risks: wrongful bans, missing appeal, accidental self-lockout of ops, PII exposure (masked phone is good).
- Owner questions:
  1. Definitions and consequences of restricted / suspended / banned (what happens to existing bookings)? OWNER DECISION.
  2. Strike ladder (warn, restrict, suspend, ban) written on one page? Rec: yes.
  3. Appeal reviewed by a different admin? Rec: yes.

### Gaps
- No single primary source for Stripe/Shopify admin patterns was fetched.

---

## 16. Admin: Bookings (read-only)

### Takeaway
The list shows only id, status and created time, so it cannot support a report, dispute or support case; it needs a read-only detail view and filters, but no refund/payout buttons until rules exist.

### Cited Findings
- Today: table with id, status, created; 25 per page; rows not clickable; no search/filter; banner explains read-only — `src/admin/Lists.tsx`.
- Today: reports and SOS reference `booking_id`; admin management of bookings/payments/refunds is OUT OF SCOPE by design (no refund logic) — `docs/web-and-admin.md`.
- Today: cancellation safeguard only flags money for manual refund reconciliation — `docs/mvp-safety-ops.md`.

### Inferences
- Must: booking detail (parties as user links, service, time, place, price, status timeline, payment state, linked reports/SOS); filter by status/date; search by id.
- Nice: manual note on a booking; CSV for accounting.
- Probably excessive: refund/cancel/complete overrides, payout screens before rules are decided.
- Risks: reading private chat needs a legal basis and disclosure in Privacy; disputes without rules produce ad hoc decisions.
- Owner questions:
  1. May admins read booking chat? Rec: only when a report or SOS exists, with a logged reason, disclosed in the Privacy policy.
  2. Any manual override of booking state at beta? Rec: no, except via support with a note.
  3. Dispute Center (TZ §23) at beta? Rec: no; use Safety + Support + manual hold.

### Gaps
- Money rules (refund, payout, dispute) are undecided; nothing to design against.

---

## 17. Admin: Safety queue (reports and SOS)

### Takeaway
Reports and SOS are visible with immutable acknowledgement notes, but "acknowledged" is the only outcome: no priority, no context, no resolution, no alert, no runbook — the least ready part for a real beta.

### Cited Findings
- Today: tabs Reports/SOS, "only open" toggle, refresh; report card = category, status, description, time, reporter short id, reported short id, booking id, "mark reviewed" with note >= 8; SOS card = time, sender, booking, "emergency service contacted: No", "mark reviewed" with note; first acknowledgement is immutable — `src/admin/Safety.tsx`, `docs/mvp-safety-ops.md`.
- Today: not built: live on-call staffing, incident SLA, responder paging, formal report resolution, suspension/dispute adjudication — `docs/mvp-safety-ops.md`.
- Today: report categories = harassment, inappropriate request, fake profile, fraud, unsafe behavior, no-show, payment issue, other — `TZ.md` §24, `src/lib/labels.ts`.
- Comparable: triage by severity and reversibility, then volume/SLA, fast escalation path, central incident log with severity and predefined escalation points, rotating moderators — [startup.jobs](https://startup.jobs/interview-questions/trust-safety-specialist), [playbook](https://playbooks.com/skills/gtmagents/gtm-agents/moderation-safety-playbook), [TSPA](https://www.tspa.org/explore/events/past-events/) (3rd).

### Inferences
- Must: SOS card with booking context (time, place, meeting state, check-ins, both parties linked, other recent alerts); sort SOS first then oldest first; outcome field (no action, warning, restricted, suspended, banned, referred) with a link to the Users action; "other reports about this user" panel; age timer; alert to on-call; a written runbook (who calls whom, what authority, what is logged).
- Nice: contact templates; neutral "we reviewed your report" message to the reporter.
- Probably excessive: automatic classification/risk scoring, full Dispute Center UI.
- Risks: a recorded SOS nobody sees; malicious or brigading reports against companions; limited reporter anonymity (booking-based reports reveal the counterpart); moderator wellbeing; sensitive-data retention; the product never claims emergency services were notified, so the human runbook is the real safety net.
- Owner questions:
  1. Who staffs the queue during meeting hours and what is the SOS acknowledgement target? OWNER DECISION; Rec: do not open the beta before this is answered (the repo itself says so).
  2. Outcome taxonomy (six outcomes above)? Rec: yes.
  3. Notify the reporter that the report was reviewed (no details)? Rec: yes.
  4. Policy for contacting police or law enforcement and who decides? OWNER/LEGAL DECISION.

### Gaps
- Airbnb/Uber primary trust-and-safety design posts not found in this session; only practitioner secondary sources.

---

## 18. Admin: Support requests

### Takeaway
A working single-reply inbox for the only support channel, missing the context and efficiency tools (user/booking context, canned replies, internal notes, ordering) that determine response time.

### Cited Findings
- Today: status filter (open default), cards with category, status, user id, time, message, previous reply; textarea reply (>= 2 chars) with "Send" or "Send and close"; each reply audited server-side; one message + one reply per ticket in the model — `src/admin/Support.tsx`.
- Today: support = in-app request form only (no e-mail; phone only if a real line exists; hours and response time undefined) — `CLAUDE.md` §7 (S24).
- Today: no notification kind for a support reply, so the user must open Help to see it — `src/i18n/en.ts` `notif.kind.*`.

### Inferences
- Must: user context beside the ticket (roles, status, recent bookings, open reports); canned replies per category in uz+ru; internal notes; oldest-first with age; notification when answered; a way for suspended users to appeal.
- Nice: reopen on user follow-up, satisfaction thumbs, routing by category.
- Probably excessive: live chat, chatbots, SLA automation, ticket merge.
- Risks: users paste passport/card numbers in free text; no e-mail fallback for users who cannot log in; admin workload.
- Owner questions:
  1. Published response time? Rec: only a number you can staff.
  2. Support languages (uz+ru)? Rec: yes.
  3. Can banned/suspended users still file an appeal? Rec: yes (verify the app allows it).
  4. Add a "do not send ID numbers or card data" warning on the form? Rec: yes.

### Gaps
- Not verified whether suspended users can still reach the support form.

---

## 19. Admin: Account-deletion requests

### Takeaway
Adequate for a beta (list + guarded "process due" run), but it must not let a reported user escape review by deleting the account.

### Cited Findings
- Today: table of requests (user, status pending/cancelled/completed, requested, due/completed); danger button "process due deletions" with confirm; toast shows erased and skipped-open-bookings counts — `src/admin/Support.tsx` (Deletions).
- Today: personal data erased or de-identified within 30 days, legally needed records kept de-identified; hourly job `python -m yondo_api.jobs` exists but is not scheduled yet (server stage later) — `CLAUDE.md` §7 (S24, S26), `docs/legal/pre-publication-checklist.md`.

### Inferences
- Must: legal-hold rule (open report/SOS/dispute blocks erasure); show why a request was skipped; schedule the job at the server stage.
- Nice: requester sees the planned erasure date; dry-run counts.
- Probably excessive: admin immediate delete, bulk actions.
- Risks: irreversible action by one click; conflict with investigations; backups retention not defined.
- Owner questions:
  1. Block erasure while a report/dispute is open? Rec: yes.
  2. Which records are "legally needed" and for how long? OWNER/LEGAL DECISION.
  3. Keep the manual button once the hourly job runs? Rec: yes, as fallback.

### Gaps
- Uzbek legal retention periods and erasure rights were not researched.

---

## 20. Admin: Audit log

### Takeaway
A useful, transactionally written log, too thin to investigate with: no filters by person or date, no export, only decision events.

### Cited Findings
- Today: filter by action prefix (account_status, companion_application, companion_content, safety_report, safety_sos, support_reply, account_erased); table time/action/admin id/target id/reason; 25 per page — `src/admin/Lists.tsx`.
- Today: events written in the same transaction as the decision; no row on failed (stale) decisions — `docs/web-and-admin.md`.

### Inferences
- Must: filter by admin and target, date range, CSV export, show admin display name, log views of sensitive data.
- Nice: weekly anomaly review (many bans by one admin).
- Probably excessive: SIEM integration, tamper-evident ledger.
- Risks: PII typed into reasons; retention vs deletion conflict.
- Owner questions:
  1. Who reviews the audit log and how often? Rec: owner weekly.
  2. Retention period? OWNER/LEGAL DECISION.

### Gaps
- Whether the audit table is append-only at database level was not verified.

---

## 21. Ideal companion onboarding journey: "I want to become a companion" to first paid booking

### Takeaway
Roughly 15-25 minutes of active work over 1-2 sessions, one combined review submission, one identity step, an honest status timeline, and money expectations stated as "rules will be announced" until the owner decides; the waiting time (review + first request) dominates, not form time.

### Cited Findings
- Reference patterns: linear checklist then identity (ID photo + selfie) up to 2 working days — [TaskRabbit](https://support.taskrabbit.com/hc/en-us/articles/360031918292-How-Do-I-Become-a-Tasker) (P); incremental collection, Save for later, re-entry — [Stripe](https://docs.stripe.com/connect/connect-onboarding) (P); wizard rules — [NN/g](https://www.nngroup.com/articles/wizards/) (P); response expectation 24h with decline counting as a response — [Airbnb](https://www.airbnb.com/help/article/2414) (P).
- Repo constraints: application, content, account activation and identity are separate gates; payment provider not connected; platform fee/cancellation/refund/payout undecided — `docs/companion-system.md`, `CLAUDE.md` §4.

### Inferences
- Proposed journey (step, active time, what it does):
  1. Public "Become a hamroh" page, uz+ru (1-2 min read): what Yondo is and is not, requirements (18+, ID, 3+ photos), what happens next. Review time and payout wording only as the owner decides.
  2. Sign in with phone OTP + accept Terms/Privacy (exists) + companion rules (new) (1-2 min).
  3. Eligibility: age confirmation, city, languages (picked from lists) (1 min).
  4. Profile: name, short bio with prompts, interests (3 min).
  5. Services & prices: 1-3 services, price per unit, venue-cost line, notice/buffer (3 min).
  6. Photos: 3+ with rules, auto-crop, upload progress (3-5 min).
  7. Weekly availability template (2 min).
  8. Identity check via MyID (or beta manual check) (3-5 min active; wait as agreed): ID + liveness; store result only.
  9. Safety orientation: public places, trusted contacts, SOS = recorded alert for manual review (not emergency services), block/report (2 min); acknowledge.
  10. Preview, then "Send for review" (one action). Save-and-resume at every step.
  11. Status timeline: Submitted (date) -> Under review -> Decision. Show who is waiting; notify via in-app + off-app channel. Outcomes: Approved / Needs changes (list + fix links) / Rejected (reason + appeal).
  12. "Go live" (explicit) after approval; choose notification channel.
  13. First request arrives: alert with reply-by time; accept or decline (preset reasons); chat; customer pays only after acceptance (existing rule).
  14. Meeting: safety brief, check-in, start, end; mutual review.
  15. After completion: show the booking amount and "payout: per rules to be announced" (no invented timing/percentages); collect payout details only when payout rules exist (incremental, Stripe pattern).
- Review-status display principles: always show date submitted, current step, what is needed from the companion vs from Yondo; never show internal notes; one clear next action; never promise a time that is not staffed.
- Risks across the journey: drop-off at identity and photos; slow manual review; first-booking dependency on customer demand (a supply-only beta stalls: seed demand from the 20-50 customers); payment not live means "first paid booking" cannot truly be paid — real provider vs clearly-labelled test mode is an owner decision.
- Owner questions:
  1. Is the beta's first "paid" booking real money (CLICK/Payme keys needed) or labelled test payments? OWNER DECISION; Rec: say which, honestly, to testers.
  2. Single sitting vs resumable? Rec: resumable.
  3. Is a short phone/video call with each beta companion part of onboarding? Rec: yes for 10-20 companions (builds trust, doubles as manual identity check if chosen).

### Gaps
- Real conversion/time data for Uzbekistan marketplaces not available; step durations are estimates.

---

## 22. Minimum admin tooling for a closed beta (10-20 companions, 20-50 customers)

### Takeaway
The existing console covers queues and audit; it is missing the five things that decide whether a beta is safe and operable: an SOS alert + runbook, an identity path, context pages (booking, user), applicant notifications, and hardened admin login.

### Cited Findings
- Exists: dashboard counters, applications queue/detail with decisions and notes, users list/status change, safety queue with acknowledgement notes, support queue with replies, deletions, audit log — `src/admin/*`.
- Exists in backend but not in UI: beta enrollment and beta feedback tables (enrollment admin NOT IMPLEMENTED in UI) — `apps/api/src/yondo_api/beta/models.py`, `docs/web-and-admin.md`.
- Constraint: "Do not enable a closed beta with real safety-critical reliance until human and technical escalation operations are approved" — `docs/mvp-safety-ops.md`.

### Inferences
- MUST before the beta: (1) SOS alert to on-call (Telegram/SMS) + one-page runbook + named rota; (2) identity path (manual verified-flag with audit, or MyID); (3) booking detail and user detail pages (read-only); (4) notifications to applicants (decision) and users (support reply); (5) admin second factor/step-up and view-logging; (6) rejection reasons + "needs changes"; (7) storage adapter for photos; (8) beta cohort control (invite list/allow-list using the existing beta tables); (9) written moderation guidelines.
- SHOULD: oldest-first queues with age badges; claim/lock; canned support replies; CSV export of audit and 5-8 beta metrics; companion Today/requests view.
- LATER: manual payout ledger (only after payout rules), dispute workflow, warn/strike automation, RBAC.
- Staffing sizing (inference): 20 companions means a handful of applications and re-reviews per week, small support volume, rare but critical SOS; evenings/weekends are when meetings happen, so on-call hours should match meeting hours; 2-3 admins plus one weekly audit review is proportionate.
- Owner questions:
  1. Open the beta only after SOS on-call + runbook exist? Rec: yes.
  2. Invite-only beta using the existing beta tables? Rec: yes.
  3. Manual identity verification for the first 20 companions? Rec: yes, then MyID.
  4. Who is the single accountable person for safety escalations? Rec: name one owner.

### Gaps
- No evidence on actual staffing or volume; sizing is an inference.

---

## 23. Consolidated OWNER DECISION register (business/legal rules; no values were invented)

### Takeaway
These are the items the code and docs leave open; the UI shows "Aniqlanmagan" or hides the feature until they are answered.

### Cited Findings
- Undecided per repo: platform fee, delivery fee, cancellation percentages, refund amounts, payout rules, dispute handling, price limits — `CLAUDE.md` §4, `TZ.md` §21-23, §26-27, `docs/mvp-safety-ops.md`.

### Inferences
- Money: fee model; who pays venue costs; payout method, schedule and holds; cancellation and refund percentages; no-show handling; companion tax/self-employed status (legal advice needed; the cited tax details are from non-official pages).
- Safety: SOS staffing, acknowledgement target, runbook, police-contact policy; late-evening start limit; public-venue rule; safety-brief acknowledgement.
- Trust: identity method and timing (manual vs MyID), age rule, photo rules (face visible?), background checks (Rec: no at beta), customer info visible to companions.
- Moderation: guidelines, outcome taxonomy, strike ladder, definitions of restricted/suspended/banned, appeals, retention of rejected applicants' data, legal hold on deletion.
- Product: role-mode model, edit-without-delisting policy, response window for requests, booking horizon, minimum notice, hidden services at beta (custom_experience, online_call), off-app notification channel.
- Platform/legal: operator name, storage hosting in-country (biometric data), admin second factor, chat-reading policy.

### Gaps
- Legal items (data localization details, tax status, retention periods) need a local lawyer; sources here are news/secondary.
