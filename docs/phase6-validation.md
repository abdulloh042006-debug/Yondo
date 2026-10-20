# Phase 6 final freeze hardening - 2026-10-01

Post-audit hardening covers three additional photo edge cases without changing
Phase 6 product scope: malformed PNG checksum errors now return structured 422,
request cancellation after storage persistence runs shielded cleanup, and ambiguous
DB commit acknowledgement is reconciled from a fresh session before any object
deletion so durable metadata is not left pointing at a deleted object.

Validation on the final sources: targeted audit regressions PASS, full SQLite suite
PASS with the expected PostgreSQL-only skips, Ruff PASS, isolated sdist/wheel build
PASS, and git diff --check PASS. Native PostgreSQL 17 completed all 147 tests with
zero skips after Alembic upgrade/check reported no model drift. The three new photo
regressions also passed directly against PostgreSQL. Docker was run with a temporary
2 GB WSL cap for this validation and the developer's prior 3 GB cap was restored
afterward.

# Phase 6 audit remediation - 2026-10-01

**Status: PASS for the scoped H1-H4 development-baseline remediation.**
Baseline: `c78108e2e0f005d51648faa579fec99b8b9e5166`.
Target branch: `abdulloh042006-debug-development-infrastructure`.
Checkout: `D:\Yondo-Phase6-validation` on `DESKTOP-3BE6EEH`.
Phase 7 was not started. Product/UX documents and Phase 5 source remain unchanged.
This is not a declaration of production readiness.

## Audit findings and completed fixes

Finding IDs below refer to Claude's read-only audit of `c78108e`. The earlier
uncommitted remediation used different IDs and did not cover all Claude findings.
Its scoped changes were inspected and retained, then H3 and the timezone half
of H4 were completed here.

- **H1:** application and aggregate content revisions bind decisions to what an
  admin reviewed. Required typed `expected_revision` is checked under the owner
  lock. Profile/service/photo edits and resubmissions invalidate old decisions.
  A single authorized content-review snapshot includes profile/services/photos.
- **H2:** Pillow validation/decode/EXIF/orientation/conversion/JPEG work runs in
  AnyIO worker threads with a dedicated two-worker limiter per application process.
  Existing MIME, byte, pixel and animation restrictions remain enforced.
- **H3:** the existing per-profile photo cap counts retained tombstones as well
  as live photos, under the owner lock and before processing/uploading bytes.
  Repeated upload/delete cycles and concurrent uploads cannot reset or exceed
  this quota. Deletion hides photos but does not restore capacity until a future
  approved retention/GC process reclaims retained objects and metadata. No
  destructive retention policy or arbitrary new business limit was introduced.
- **H4:** unrepresentable UTC normalization and invalid IANA zone keys, including
  filesystem directory errors for America/Etc, return structured 422 responses.
- Existing upload compensation improvements were preserved: upload exceptions
  and DB-save failures attempt cleanup; failed cleanup logs the private object
  key while preserving the original structured response.
- Migration `20261001_0004` backfills non-null revision counters to 1. Decision
  clients must fetch and submit the reviewed revision; omission returns 422 and
  stale revisions return 409.

## Checks executed on the final runtime/test sources

Windows Python 3.13.15; native PostgreSQL 17.11 in the new disposable container
`yondo-phase6-final-pg-20261001`, localhost port 55438, DB `yondo_phase6_final`.
No existing application DB was used. Pytest cache was disabled.

| Check | Result |
| --- | --- |
| Full SQLite suite | 138 passed, 6 native-only skips |
| Full native PostgreSQL suite | 144 passed, zero skips |
| Ruff `check --no-cache .` | PASS |
| PostgreSQL upgrade head / Alembic check | PASS; no model drift |
| Populated PostgreSQL 0004 -> 0003 -> head | PASS; application, profile and availability data preserved; revisions backfilled to 1 |
| PostgreSQL downgrade to Phase 5 (0002) / upgrade / check | PASS; existing users retained; GiST exclusion and btree_gist verified |
| Fresh SQLite upgrade/check and 0004/0003 plus 0002/head round trips | PASS; no model drift |
| `python -m build` | PASS; isolated sdist and wheel build |
| Build content | PASS; runtime sources match wheel; new migration and regression tests match sdist |
| `git diff --check` | PASS |

Regression coverage includes stale application/content decisions after edits and
resubmission, every service mutation, profile/photo/caption/order changes, required
revisions, real EXIF/GPS stripping and orientation, animated-image rejection,
ambiguous upload failure, real DB constraint rollback, cleanup success/failure,
UTC overflow boundaries, timezone directory failures, event-loop responsiveness,
native review/edit races, bounded image-worker concurrency, retained-photo quota,
owner isolation and concurrent uploads against that quota.

One existing Starlette/httpx deprecation warning remains. Initial lint line length
was corrected. A no-isolation build lacked setuptools; the standard isolated build
installed its declared backend dependency and completed successfully.

## Files changed

- `apps/api/migrations/versions/20261001_0004_review_revisions.py`
- `apps/api/src/yondo_api/companions/{admin,models,photos,router,schemas,service}.py`
- `apps/api/src/yondo_api/main.py`
- `apps/api/tests/companions/{conftest,test_audit_regressions,test_constraints,test_lifecycle,test_photos}.py`
- `docs/companion-system.md`
- `docs/phase6-validation.md`

Only these 15 files belong in the remediation commit. Transfer archives, patches,
local validation scripts/logs, environments, DB files and build output are excluded.

## Remaining issues and next step

H1-H4 are addressed for this scoped baseline. Other audit observations are not
claimed resolved: exclusive read locks, set-wise identity eligibility for future
Discovery, admin queue/revocation operations, production pricing configuration,
availability bounds and activation/edit policy need their respective follow-ups.
Low-priority findings, including cancellation-related orphan risk, remain recorded
in the source audit and were not silently treated as completed.

Concrete storage and identity adapters plus business configuration are still
needed before production. Retention/GC remains undecided; retained photos consume
quota until reclamation. Storage/DB compensation is not an atomic transaction:
failed cleanup and cancellation can require orphan reconciliation. No general
request-rate limiter was added; image execution itself is bounded.

The repository CI workflow runs on main pushes or pull requests, not direct pushes
to this development branch; absence of a new workflow run is not a CI pass.
Recommended next roadmap phase is Phase 7 Discovery only after separate approval
and resolution of its identity/visibility design prerequisites. It was not started.

---

The following is the historical foundation validation report; its no-push statements
and test totals describe the earlier Phase 6 implementation, not this remediation.

# Phase 6 validation report

**Status: PASS for the requested Phase 6 backend foundation.** Native PostgreSQL
validation completed on 2026-09-30. Nothing has been pushed; Phase 7 was not started.
Production storage and identity integration remain separate deployment work.

Baseline: `40e3e1502347dbf066712ba0e69a2531cfb9be3d` on
`abdulloh042006-debug-development-infrastructure`, containing Phase 5.
Local branch: `codex/phase6-companion-system`.
Authorized Windows validation checkout: `D:\Yondo-Phase6-validation`, branch
`phase6-validation`. The existing `D:\Yondo` checkout was not modified.

## Checks executed

| Check | Result |
| --- | --- |
| Original Phase 5/foundation suite | 21 passed, preserved |
| Full suite on Windows Python 3.13 | 111 passed, zero skipped, 68.29 seconds |
| Phase 6 coverage against native PostgreSQL | 90 passed, including both formerly skipped cases |
| Native PostgreSQL version | 17.11, official `postgres:17-alpine` container |
| PostgreSQL `alembic upgrade head` / `alembic check` | PASS; no model drift |
| PostgreSQL downgrade to 0002, upgrade to head, check | PASS |
| Direct GiST overlapping insert rejection | PASS |
| Concurrent overlapping inserts | PASS: one commit, one conflict, one persisted row |
| SQLite regression run | 109 passed, two PostgreSQL-only skips |
| SQLite Alembic upgrade/check | PASS |
| Ruff `check --no-cache .` | PASS |
| `python -m build` | PASS: sdist and wheel |
| `git diff --check`, including added files | PASS |

The companion fixtures use native PostgreSQL through `YONDO_TEST_DATABASE_URL`.
The unchanged Phase 5/foundation tests retain their existing database fixtures.
The disposable database was `yondo_phase6_test`, exposed only on localhost port
55436 in container `yondo-phase6-validation-pg-20260930`. It did not use an existing
development or production database. The test container was stopped after validation.

Evidence is retained in `D:\Yondo-Phase6-validation\validation.log`; the runner is
`validate.local.ps1` in that checkout. The runner exited 0 and printed
`PHASE6_VALIDATION_ALL_CHECKS_PASSED`. Build artifacts are in `apps/api/dist`.

Earlier PGlite rollback failures and the root-only cloud runtime prevented native
validation. Those environment blockers are now resolved by the Windows/Docker run;
no application workaround or permission-check bypass was introduced. Docker was
launched with its missing ProgramData environment restored for that process only.

One preexisting dependency warning remains: Starlette's TestClient warns about
its httpx integration. It does not fail tests. Phase 5 authentication code,
its migrations and tests, `TZ.md`, `ROADMAP.md`, and UX/UI documentation are unchanged.

## Coverage

Application ownership, duplicates, edit/submit/reject/resubmit/withdraw transitions;
profile creation/replacement, mass-assignment rejection and validation; role/account
and admin authorization; independent identity/content/application activation gates;
provider failure and dynamic identity/account/role revocation; invalid transitions;
service CRUD, precision and price/currency/duration hooks; availability CRUD, all
interval overlap shapes, adjacency, UTC and DST offsets; image validation/limits,
EXIF removal, metadata, ordering, captions, ownership and soft deletion; storage
failures; database foreign keys, state/price/interval checks and uniqueness.

Native-only tests passed and assert direct GiST constraint enforcement and
simultaneous conflicting availability inserts. They opt in through
`YONDO_TEST_DATABASE_URL` and intentionally clear the supplied test database.

## Decisions and unresolved choices

See `companion-system.md` for architecture, every endpoint, migration design,
state transitions and configuration defaults. Identity and storage are injected
through interfaces; a missing identity source prevents activation and a missing
storage adapter returns 503. No new ID/selfie workflow was introduced.

Currencies, free-service eligibility and price/duration limits remain configurable.
Completeness/taxonomy/retention rules remain product decisions rather than invented
requirements. Deleted photos remain private tombstones pending retention/GC policy.
Upload compensation cannot guarantee atomicity across the DB and object storage.
Production deployment still needs concrete storage and identity read adapters.

## Exact next recommended step

Review the validated Phase 6 diff in `D:\Yondo-Phase6-validation` before integrating
it into the development branch. No push or integration into `D:\Yondo` was performed.
Phase 7 Discovery is next in ROADMAP, but requires a separate authorized task.
The identity and storage adapters remain necessary before production activation.

## Files changed

- `.env.example`
- `apps/api/MANIFEST.in`
- `apps/api/README.md`
- `apps/api/migrations/versions/20260930_0003_companion_system.py`
- `apps/api/pyproject.toml`
- `apps/api/src/yondo_api/api/errors.py`
- `apps/api/src/yondo_api/companions/__init__.py`
- `apps/api/src/yondo_api/companions/admin.py`
- `apps/api/src/yondo_api/companions/dependencies.py`
- `apps/api/src/yondo_api/companions/integrations.py`
- `apps/api/src/yondo_api/companions/models.py`
- `apps/api/src/yondo_api/companions/photos.py`
- `apps/api/src/yondo_api/companions/resources.py`
- `apps/api/src/yondo_api/companions/router.py`
- `apps/api/src/yondo_api/companions/schemas.py`
- `apps/api/src/yondo_api/companions/service.py`
- `apps/api/src/yondo_api/config.py`
- `apps/api/src/yondo_api/main.py`
- `apps/api/src/yondo_api/models/__init__.py`
- `apps/api/tests/companions/__init__.py`
- `apps/api/tests/companions/conftest.py`
- `apps/api/tests/companions/test_constraints.py`
- `apps/api/tests/companions/test_lifecycle.py`
- `apps/api/tests/companions/test_photos.py`
- `apps/api/tests/companions/test_resources.py`
- `docs/companion-system.md`
- `docs/phase6-validation.md`
