# Production API image (NOT the demo harness). Build context: apps/api.
#   docker build -t yondo-api apps/api
# Applies the Alembic migrations, then serves the real API. All settings come from YONDO_* environment
# variables (see infra/deploy/digitalocean/.env.example); nothing secret is baked into the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY . /app
RUN pip install /app \
    && useradd --system --uid 10001 --no-create-home yondo \
    && chown -R yondo /app
USER yondo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Only the reverse proxy (Caddy, same Docker network) can reach this port, so trusting its forwarded headers is safe.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn yondo_api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
