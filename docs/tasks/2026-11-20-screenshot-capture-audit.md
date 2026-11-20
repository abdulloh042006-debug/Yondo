# YONDO UI screenshot audit and capture checklist

**Created:** 2026-11-20  
**Status:** CHECKLIST PREPARED; fresh capture is BLOCKED by unavailable workstation/browser environment.  
**Scope:** screenshots of the existing, running product only. This is not authorization to start the queued UI redesign or change app behavior.

## Goal

Create a truthful, repeatable visual baseline for every currently reachable YONDO screen, in both owner-approved themes:

- **Day:** `yondo`
- **Night:** `yondo-tun`

Capture the actual web and mobile applications, plus the web admin console. Do not substitute the HTML design prototype for screenshots of the running application.

## Rules for valid evidence

- Every screen/state is complete only when a real browser/device screenshot exists in **both** themes.
- Use deterministic seeded/test accounts and DEMO records. Never use real identity documents, phone numbers, private user data, live payment details, API keys, or production secrets.
- Set the theme explicitly for each capture. Do not use `system`, `gul`, `rausch/Jurnal`, or `stone` for this task.
- Keep viewport and device scale recorded in the filename or capture manifest. Required baseline: mobile viewport **360 × 800**; web desktop **1440 × 900**. Also capture the web app at 360 × 800 to check responsive layout.
- Capture the page after it has settled. Include important open sheets/dialogs, filters, selected tabs, empty states and validation states where they are actually implemented.
- A route that does not exist, cannot be reached, or has no implementation must be marked **NOT IMPLEMENTED / BLOCKED**, not represented by a fabricated mock.
- Do not include screenshots containing real personal information. Blur/redact any accidental sensitive values before committing.
- Keep the older baseline and prototype captures as historical evidence. Do not overwrite them.

## Existing screenshot evidence found in the repository

The current repository already contains a **partial historical baseline** in `docs/design/redesign-2026-11/before/`:

- 12 web day captures: login/password setup, discovery/list/filter/card states, favorites empty, bookings, booking details, account/profile, settings, help and companion profile.
- 3 web night captures: discovery, booking details and account/profile.
- 11 mobile day captures: anonymous/discovery, code/password setup, favorites, bookings, profile, settings (including scroll positions) and help (including scroll positions).
- No mobile night captures were present in that folder.

The redesign prototype and its frames are separate evidence:
- `design-prototype/redesign/index.html`
- `docs/design/redesign-2026-11/prototype/`

Those prototype frames are **not** current-app screenshots. Reuse them only as design references, never as proof that the production UI currently looks or behaves that way.

## A. Web application — public/customer/companion

For each item, capture `yondo` and `yondo-tun` at desktop 1440 × 900 and responsive 360 × 800 where applicable.

- [ ] `/` Discovery / Kashf — default list, search results, no-results state, loading/error state if reproducible.
- [ ] Discovery filter sheet — open, selected filters, clear/apply states.
- [ ] `/?view=cards` — card-deck view, next/save interaction state.
- [ ] `/c/:id` — public companion profile with DEMO/test record; capture top and scrolled content.
- [ ] `/login` — sign-in form, OTP/code step, password creation, password sign-in/reset and validation states that exist in the current build.
- [ ] `/auth/callback/telegram` — capture only a deterministic test callback result; do not use a real login token.
- [ ] `/favorites` — empty and populated states.
- [ ] `/bookings` — empty and populated list; capture the available status filters/tabs if present.
- [ ] `/bookings/:id` — each reproducible booking state supported by the UI (for example pending, accepted, active, completed or cancelled); capture available dialogs/actions separately.
- [ ] `/demo-pay/:reference` and `/pay/:reference` — only if the test environment can reach the current implemented page safely; use simulator/test references only. Mark unavailable states rather than implying that real payment processing is live.
- [ ] `/notifications` — page, unread/read states and empty state if implemented.
- [ ] `/account` — profile/account hub, role display and available actions.
- [ ] `/settings` — language, Uzbek alphabet, theme selector, notification/sound preferences, account/roles, privacy/safety and about/legal sections. Capture selectors/sheets open as separate states.
- [ ] `/help` — safety information, FAQ, support form and confirmation/error states that are implemented; capture scrolled sections.
- [ ] `/terms` and `/privacy` — each legal page at top and scrolled content.
- [ ] `/studio` — capture each existing tab separately: Status, Application, Profile, Services, Photos, Availability. Include empty, draft/pending/rejected/approved or blocker states only when reproducible using test records.
- [ ] Unknown route — 404/not-found screen.

## B. Web admin console

Capture only with a dedicated test admin account and seeded records. Verify that no sensitive production data appears.

- [ ] `/admin` — dashboard.
- [ ] `/admin/applications` — applications queue, filters and empty state.
- [ ] `/admin/applications/:id` — application detail and available review/confirmation states.
- [ ] `/admin/safety` — safety queue, empty state and acknowledgement dialog if seeded.
- [ ] `/admin/users` — user list, filters and status-change confirmation if seeded.
- [ ] `/admin/support` — support queue and request detail/reply state if seeded.
- [ ] `/admin/deletions` — deletion queue and available states if seeded.
- [ ] `/admin/bookings` — admin booking list and empty state.
- [ ] `/admin/payments` — admin payments view and empty state; record the actual read/action capabilities shown.
- [ ] `/admin/audit` — audit log and empty/populated state.
- [ ] Verify customer/companion accounts cannot open admin routes; record the access-denied/redirect behavior without exposing private data.

## C. Mobile application

Capture at **360 × 800** in both explicit themes. Use the current mobile app, not a web-page screenshot resized to look like a phone.

- [ ] Discover / Kashf — list, search/filter state and card deck.
- [ ] Companion public profile.
- [ ] Login — anonymous entry, code/OTP step, password setup/sign-in and validation states that exist.
- [ ] Favorites — empty and populated.
- [ ] Bookings — empty and populated.
- [ ] Booking details — each reproducible UI status/action state.
- [ ] Account/Profile — top and scrolled content.
- [ ] Settings — all available sections and theme/language selectors.
- [ ] Notifications — available page states.
- [ ] Help — top, scrolled content, support and SOS confirmation states where implemented.
- [ ] Password/age-restriction/legal-consent gates — capture the actual states accessible in test accounts.
- [ ] My Photos — capture only if reachable in the current navigation; include empty/populated/reorder/delete-confirm states that exist.

**Mobile scope note:** the inspected mobile `App.tsx` does not expose the same standalone `/studio` and `/admin` route tree as web. Do not invent mobile Studio/Admin pages; record them as web-only unless a real mobile route is added later.

## D. Screenshot naming and folder structure

Save the new evidence under:

```text
docs/screenshots/2026-11-20/
  web/
    desktop/yondo/
    desktop/yondo-tun/
    mobile/yondo/
    mobile/yondo-tun/
  mobile-app/
    yondo/
    yondo-tun/
  manifest.md
```

Suggested filenames use stable route/state names, for example:

- `discovery-default-1440x900.png`
- `discovery-filters-open-360x800.png`
- `booking-detail-accepted-yondo-tun-360x800.png`
- `admin-applications-populated-yondo-1440x900.png`

The manifest must record: screen/route, theme, viewport, test account role (not its credentials), test data seed, screenshot filename, capture date, and result (`PASS`, `BLOCKED`, `NOT IMPLEMENTED`). Link each pair of day/night captures.

## E. Validation before marking a screen complete

- [ ] Confirm the target route is served by the current app build.
- [ ] Confirm the requested theme is visibly active and persisted only for the test context.
- [ ] Confirm the screenshot is legible, complete, not clipped and has no horizontal overflow at the target width.
- [ ] Confirm no real personal/sensitive data or secrets appear.
- [ ] Compare day/night pairs for missing text, contrast, overflow and layout regressions.
- [ ] Run the relevant web checks from `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`; run `npm run e2e` when the real test API is available.
- [ ] Run the mobile typecheck/smoke checks available in `apps/mobile`.
- [ ] Review the final folder and manifest; only then mark a screen pair complete.
- [ ] Commit the screenshots and manifest to this task branch and link the commit in the tracking issue.

## F. Dependencies / current blocker

- [ ] Bring the authorized Desktop Commander workstation online (or provide an available runner with the repository checkout and browser dependencies).
- [ ] Restore/open the YONDO checkout and confirm the active commit/branch before starting the app.
- [ ] Start the test API/database and web/mobile apps using the repository's documented setup.
- [ ] Run deterministic Playwright/device capture for the matrix above.
- [ ] Review every screenshot, write the manifest, then commit and push the binary images.

**Current environment check (2026-11-20):** both linked Desktop Commander devices reported **Offline**. The available container has Chromium/Node but cannot resolve GitHub or install/restore the project dependencies. Therefore no new live-app screenshots have been captured in this session. No placeholder or prototype image is being passed off as a live-app capture.

## G. Scope guard

The separate `docs/tasks/2026-11-18-ui-redesign-brief.md` is marked QUEUED and explicitly says to start the redesign only after its prerequisite tasks and on the owner's instruction. This screenshot audit does not start that redesign, change app code, or claim any unimplemented booking/payment/chat/vendor features are complete.
