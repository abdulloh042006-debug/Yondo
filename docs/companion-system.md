# Phase 6 — Companion backend foundation

## Scope and baseline

Implemented on top of `40e3e1502347dbf066712ba0e69a2531cfb9be3d` from
`abdulloh042006-debug-development-infrastructure`. The remote `main` branch
still contains Phase 4; it is not the baseline for this patch.

No Discovery, Booking, Payment, Chat, Calls, Gifts, Meeting, Reviews, SOS,
intro video, or ID/selfie workflow has been added. `TZ.md`, `ROADMAP.md`,
UX/UI documents, and Phase 5 authentication code are unchanged.

## Architecture

`yondo_api.companions` owns its SQLAlchemy models, strict Pydantic schemas,
owner/admin authorization, service helpers, identity read adapter, routes,
photo processing, and state transitions. It reuses Phase 5 bearer sessions,
users, roles, account statuses, DB sessions, version prefix, and structured errors.

Five tables:

- `companion_applications`: one application per user, statement, state and latest decision metadata.
- `companion_profiles`: one profile per application, display name, bio, languages,
  interests, content approval and activation intent. Age/city/gender stay on User.
- `companion_services`: catalog code, description, exact BIGINT minor-unit amount,
  three-letter uppercase currency code, and explicit pricing duration in minutes.
- `companion_photos`: server-generated object key, actual MIME/size/dimensions,
  caption, unique order per profile, private deletion tombstone.
- `companion_availability`: finite timezone-aware start/end instants and an IANA
  display timezone. Database values are UTC instants; intervals are half-open.

Foreign keys, unique constraints, enum-state checks, positive interval/duration
checks, nonnegative price checks and indexes enforce structural integrity.
Languages/interests use bounded JSON arrays, with trimmed, case-insensitively
unique entries. No new taxonomy is invented.

## Ownership and status gates

A user selects the existing companion role before applying. A customer-only
account cannot access or change companion resources. The owner comes from the
bearer session, never from the request body. Child IDs are also scoped to that
owner's profile. Other owners receive 404. Restricted/suspended/banned accounts
cannot modify companion resources. Admin decisions require an active admin;
self-approval is prohibited. The admin endpoints are domain approval operations,
not a Phase 14 admin panel.

Application transitions:

- Create -> draft.
- Draft -> submitted.
- Submitted -> approved or rejected, by admin only.
- Draft/rejected/withdrawn -> draft through edit; reuse the existing application.
- Any non-withdrawn application -> withdrawn by owner; activation is cleared.

Content transitions:

- Create -> draft.
- Draft/rejected -> pending through submit.
- Pending -> approved or rejected, by admin only.
- Any profile, service, photo, caption or order mutation -> draft and inactive.
- Availability updates do not change content approval.

Activation is a separate owner action. It requires all of:

1. Approved application.
2. Approved content.
3. Active account.
4. Current companion role.
5. Identity adapter reports verified.

`activation_requested` is **intent**, not a public visibility flag. The canonical
`companion_status()` computes `publicly_active` from all current gates each time.
Future Discovery must use that gate, never filter only on activation intent.
Account/identity/role revocation therefore makes a profile ineligible without
requiring a second, potentially stale verification record. Identity adapter
failure returns 503; unknown/pending/rejected prevents activation. Approval alone
never activates a profile.

The default identity adapter returns unknown. Phone OTP and account active are
not identity proof. Inject a read-only `IdentityEligibility` adapter into
`create_application` when Trust & Safety provides an authoritative identity source.
Phase 6 does not persist ID/selfie information or expose identity writes.

## Endpoints

All paths below use the existing configurable `/api/v1` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| POST, GET, PUT | `/companions/me/application` | Create/read/edit owned application |
| POST | `/companions/me/application/submit` | Submit draft |
| POST | `/companions/me/application/withdraw` | Withdraw and deactivate |
| POST, GET, PUT | `/companions/me/profile` | Create/read/replace profile content |
| POST | `/companions/me/profile/submit` | Submit content for approval |
| GET | `/companions/me/status` | Current separate gates, blockers and effective activity |
| POST | `/companions/me/activate` | Activate only after all gates pass |
| POST | `/companions/me/deactivate` | Clear activation intent |
| GET, POST | `/companions/me/services` | List/create services and prices |
| PUT, DELETE | `/companions/me/services/{service_id}` | Replace/delete owned service |
| GET, POST | `/companions/me/availability` | List/create windows |
| PUT, DELETE | `/companions/me/availability/{availability_id}` | Replace/delete owned window |
| GET, POST | `/companions/me/photos` | List metadata/upload still image |
| PUT | `/companions/me/photos/order` | Set complete ordered list of current photo IDs |
| PATCH, DELETE | `/companions/me/photos/{photo_id}` | Caption or soft delete |
| GET | `/companions/me/photos/{photo_id}/download` | Authorized temporary download URL |
| GET | `/companions/admin/applications/{application_id}` | Inspect application |
| POST | `/companions/admin/applications/{application_id}/decision` | Approve/reject submitted application |
| GET | `/companions/admin/users/{user_id}/profile` | Inspect profile for approval |
| GET | `/companions/admin/users/{user_id}/services` | Inspect offered services/prices |
| GET | `/companions/admin/users/{user_id}/photos` | Inspect current photo metadata |
| GET | `/companions/admin/users/{user_id}/photos/{photo_id}/download` | Inspect photo content |
| POST | `/companions/admin/profiles/{profile_id}/decision` | Approve/reject pending content |

PUT replaces the editable representation; clients send all desired fields.
Unknown/privileged fields are rejected. Decisions require `decision` (`approve`
or `reject`) and a nonempty `note`. API validation returns the existing error
shape with request ID. The shared error handler now omits input/exception objects
from validation details so custom validators remain JSON-safe and private.

## Photos and storage

POST photos accepts raw `image/jpeg`, `image/png`, or `image/webp` bytes.
The server validates the decoded image and configured resource limits, rejects
animation, respects EXIF orientation, and re-encodes a clean JPEG without EXIF or
embedded location data. Metadata is derived from the stored image. Upload callers
cannot supply arbitrary keys, URLs, dimensions, MIME claims, owner IDs or statuses.
The first ordered photo is the primary photo; deleted entries are not returned.
Reordering requires the entire live set and runs transactionally with a temporary
nonconflicting position range.

The existing `ObjectStorage` protocol is injected with
`create_application(settings, object_storage=adapter)`. Deployment adapters should
use the existing `Settings.storage_*` configuration. No provider is hard-coded.
The preexisting repository had only the protocol, not a concrete adapter; missing
storage returns a structured 503. Tests inject an in-memory implementation.

Deletion immediately hides metadata and denies new download URLs, while retaining
a private tombstone/object until retention policy is decided. Previously issued
signed URLs expire per the adapter (protocol default: 300 seconds). Upload/DB
failure attempts object cleanup; failed compensation is logged and needs eventual
orphan reconciliation. There is no distributed DB/object-store transaction.

## Money and configuration

Prices are integer minor units, never floating point. JSON float/bool/string
amounts and BIGINT overflow are rejected. `unit_minutes` explicitly describes the
pricing unit; no hourly default, minimum booking duration, fee, rounding,
conversion, payment or cancellation policy is introduced. Clients must preserve
64-bit integer precision, including when parsing JSON.

Configuration uses the existing `YONDO_` environment prefix:

| Setting suffix | Default | Meaning |
| --- | --- | --- |
| `COMPANION_SERVICE_CODES` | Eight TZ MVP codes | Configurable catalog; excludes V2/custom/call offerings |
| `COMPANION_ALLOWED_CURRENCIES` | `[]` | No business allowlist yet; syntax only |
| `COMPANION_PRICE_MIN_MINOR` | `0` | Technical nonnegative lower bound; configurable business minimum |
| `COMPANION_PRICE_MAX_MINOR` | unset | Optional business upper bound |
| `COMPANION_ALLOWED_UNIT_MINUTES` | `[]` | Positive integer durations until policy is configured |
| `COMPANION_MAX_PHOTOS` | `20` | Configurable technical resource cap |
| `COMPANION_PHOTO_MAX_BYTES` | `10485760` | Upload and processed-image byte cap |
| `COMPANION_PHOTO_MAX_PIXELS` | `25000000` | Decoded pixel cap |

Tuple settings use JSON arrays in environment variables. Zero price is representable
at the foundation layer; this is not a decision to launch free services. No currency
is silently selected, and currency code syntax alone does not establish support.
No automated minimum-photo/bio/language/service count is invented for approval.
An authorized reviewer decides approval until a completeness policy is specified.

## Availability and future booking

Owner mutations serialize on the user row, with a profile lock for child changes.
Overlap checks use `existing.start < new.end AND existing.end > new.start`.
PostgreSQL additionally enforces nonoverlap with a GiST exclusion constraint on
`profile_id` and `tstzrange(starts_at, ends_at, '[)')`, backed by `btree_gist`.
Adjacent windows and identical windows for different companions are valid.
Offsets make DST instants unambiguous; the IANA zone is retained for presentation.
No recurring schedule, lead time, availability horizon or booking is inferred.

Phase 8 must lock the same owner/profile aggregate before testing availability and
reserving time, and enforce its own reservation exclusion/uniqueness constraints.
An availability row is **not a reservation** and does not itself prevent double
booking. Future availability edits/deletes must check live reservations inside
that transaction. SQLite tests cover API logic, not PostgreSQL concurrency.

## Migration

`20260930_0003_companion_system` follows `20260929_0002` and creates only the five
companion tables and constraints. It does not rewrite Phase 5 tables. PostgreSQL
requires permission to create `btree_gist`, or the extension preinstalled by a DBA.
Downgrade drops Phase 6 tables and deliberately retains the shared extension.
Migrations and tests are included in the source distribution.

## Validation and remaining work

See `docs/phase6-validation.md` for executed checks and their exact limitations.

Outstanding product/deployment choices, isolated behind configuration/integration:

- Allowed currencies, free-service eligibility, min/max price and pricing durations.
- Exact content-completeness criteria, language/interest taxonomy and retention period.
- Concrete storage adapter using existing settings; later tombstone/orphan cleanup.
- Authoritative Trust & Safety identity source and read-adapter implementation.

None of these is silently represented as a finalized business policy. Default
identity remains unknown and production activation remains fail-closed.
