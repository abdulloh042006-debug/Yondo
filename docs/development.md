# Backend development

This repository uses a monorepo layout. The API is the only implemented application;
`apps/mobile`, `apps/admin`, `packages`, and `infra` are reserved workspace areas.

## Requirements

- Python 3.12+
- Docker with Compose

## Setup

From the repository root, start the local dependencies and create the API environment:

```bash
docker compose up -d postgres redis minio
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
cd apps/api
cp ../../.env.example .env  # Windows PowerShell: Copy-Item ..\..\.env.example .env
python -m pip install -e '.[dev]'
```

Then, from `apps/api`:

```bash
alembic upgrade head
uvicorn yondo_api.main:app --reload
```

The API documentation is available at `http://localhost:8000/docs` outside production.
Liveness is `GET /health`; dependency readiness is `GET /api/v1/health/ready`.

## Quality checks

Run from `apps/api` after installing development dependencies:

```bash
pytest
ruff check .
python -m pip wheel --no-deps --wheel-dir dist .
```

Ruff formatting is configured in `apps/api/pyproject.toml`; format an edited file with
`ruff format path/to/file.py`. CI does not enforce whole-tree formatting because existing API
files are not uniformly formatted.

Configuration comes from `YONDO_`-prefixed environment variables. Do not commit `.env` or
real secrets. The example credentials are for local development only. Remove `apps/api/.env`
when you no longer need the local configuration.
