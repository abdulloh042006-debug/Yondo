# Legal documents and account deletion: before publication

Status at 2026-10-23 (S24). Labels: DONE / OPEN (owner) / OPEN (ops). The Terms of use and Privacy policy
are published in the app as drafts (`/terms`, `/privacy`, version `2026-10-23-draft`); the text lives in
`apps/web/src/legal/{terms,privacy}.md`, the version in `apps/web/src/legal/versions.ts` **and**
`apps/api/src/yondo_api/account/legal.py` (a unit test keeps them equal).

| # | Item (owner checklist) | Status | Notes |
|---|---|---|---|
| 1 | Operator's official name and contact | **OPEN (owner)** | Both documents say "hali ko‘rsatilmagan". Owner decision: no e-mail for now; contact = in-app support form. Put the legal entity / owner name in both files. |
| 2 | Check the data actually collected and the providers | DONE (from code) | Privacy §2 and §10 list what the code stores today. Fonts are self-hosted since S28 (no request to Google): the "Shriftlar" bullet in `privacy.md` §10 is now outdated — **OPEN (owner)**: remove it when the next document version is published. SMS, payment, identity, object storage, push and hosting are **not connected** — update §10 when any is. |
| 3 | Confirm the 30-day deletion and backup periods | Partly DONE / **OPEN (ops)** | In-app request → profile hidden → erased/de-identified by the daily job (due after 29 days). **Ops must schedule** `python -m yondo_api.jobs` hourly — ready-made systemd timer / cron in `infra/jobs/`. Backup retention is not defined (no backup infrastructure yet): the policy says so. Photo objects are deleted only when an object-storage adapter is configured. |
| 4 | Publish terms and privacy on separate pages | DONE | `/terms`, `/privacy`; linked from the footer, Settings → About, login consent box. Draft banner shown. |
| 5 | Consent and document-version recording | DONE | Unticked consent box on login; `user_consents` (user, document, version, time); gate asks again when a version changes; server refuses non-current versions. |
| 6 | Final review against Uzbek law | Optional (owner said not required) | Recommended before leaving draft status. |

When publishing: fill item 1, set a real effective date, change the version (e.g. `2026-11-01`) in both
places, remove the draft banner text if desired. Every user is then asked to accept the new version.

## SOS wording (privacy)
SOS location is read in the browser only after the user taps "add location" and is put into the SMS the user
sends from their own phone; it is not sent to the Yondo server. Privacy §2 ("geolocation not used") stays true.

## What the erasure keeps (proposed retention, confirm with the operator)
Kept, linked to a de-identified account: bookings, payments and payouts, reviews, booking chat messages,
safety reports/SOS alerts and acknowledgements, consent records, admin audit events, beta feedback.
Deleted/cleared: phone number, age, gender, city, language, roles, sessions, OTP challenge, profile texts,
photos, availability, service descriptions, favorites, trusted contacts, own blocks, gift cart,
notifications, chat read state, support requests, beta enrollment.
