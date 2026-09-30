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
