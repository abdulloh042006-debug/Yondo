# Public DEMO image: the real Yondo API + the built web app in ONE process on ONE port.
# Build from the repository root:  docker build -f infra/deploy/Dockerfile -t yondo-demo .
# Read infra/deploy/README.md first: this image uses the e2e test doubles (dev OTP shown on screen,
# in-memory photo storage, identity always "verified") and a throw-away SQLite file. It is NOT production.

FROM node:22-slim AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY apps/api/ /app/api/
# demo_app.py uses the aiosqlite driver, a dev-only extra of apps/api (httpx is a main dependency since the TezCheck adapter).
RUN pip install --no-cache-dir /app/api 'aiosqlite>=0.20,<1'
COPY infra/deploy/demo/demo_app.py infra/deploy/demo/demo_payment.py infra/deploy/demo/demo_persist.py /app/
COPY --from=web /web/dist /app/dist

ENV YONDO_DEMO_HOST=0.0.0.0 \
    YONDO_WEB_DIST=/app/dist \
    PORT=8000
# Default mode: a throw-away SQLite file, new at every start (the seed expects an empty database).
# With YONDO_DEMO_DATABASE_URL set the same image keeps its data in that PostgreSQL (see README).
CMD ["sh", "-c", "rm -f /tmp/demo.db && exec python /app/demo_app.py \"${PORT}\" /tmp/demo.db"]
