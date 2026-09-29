# Backend development

## Requirements

- Python 3.12+
- Docker with Compose

## Setup

From the repository root:

```bash
cp .env.example .env
docker compose up -d postgres redis minio
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e 'apps/api[dev]'
cd apps/api
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
```

Configuration comes from `YONDO_`-prefixed environment variables. Do not commit `.env` or
real secrets. The example credentials are for local development only.

