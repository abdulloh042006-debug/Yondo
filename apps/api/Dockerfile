# Yondo API image: API server, background worker and migrations share one image.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml MANIFEST.in README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN pip install .

RUN useradd --system --uid 10001 yondo
USER yondo

EXPOSE 8000

# --no-access-log: application middleware logs requests without query strings,
# so WebSocket/query credentials never reach the logs.
CMD ["uvicorn", "yondo_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers"]
