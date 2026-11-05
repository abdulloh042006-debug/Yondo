# Yondo API

FastAPI backend for Yondo. Python 3.12 or later is required.

The repository's `docs/development.md` covers local setup. Phase 6 companion API,
activation gates, integration contracts, and validation notes are documented in
`docs/companion-system.md` at the repository root.

From this directory (PowerShell or a POSIX shell):

```text
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m pytest
python -m ruff check --no-cache .
python -m pip wheel --no-deps --wheel-dir dist .
```

Set `YONDO_DATABASE_URL` for your PostgreSQL database. Migration 0003 needs the
`btree_gist` extension; a DBA may provision it before running migrations.
The source distribution includes Alembic configuration, migrations, and tests.
The wheel contains the runtime application; deploy migrations from the source
checkout or source distribution alongside it.
