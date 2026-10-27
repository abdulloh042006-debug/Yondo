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
# server.py (the e2e demo harness) imports httpx and uses the aiosqlite driver; both are dev-only extras of apps/api.
RUN pip install --no-cache-dir /app/api 'httpx>=0.28,<1' 'aiosqlite>=0.20,<1'
COPY apps/web/e2e/server.py apps/web/e2e/demo_payment.py /app/
COPY --from=web /web/dist /app/dist

ENV YONDO_DEMO_HOST=0.0.0.0 \
    YONDO_WEB_DIST=/app/dist \
    PORT=8000
# The seed expects an empty database, so every start begins with a new file (data is not kept).
CMD ["sh", "-c", "rm -f /tmp/demo.db && exec python /app/server.py \"${PORT}\" /tmp/demo.db"]
