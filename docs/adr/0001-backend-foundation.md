# ADR 0001: Backend foundation

- Status: Accepted
- Date: 2026-09-28

## Context

Yondo needs a production-oriented MVP foundation while Phase 5 authentication and later
marketplace domains are not yet in scope.

## Decision

- Use a FastAPI modular monolith under `apps/api`. Domain modules can be separated later
  without paying distributed-system costs during the MVP.
- Use async SQLAlchemy with PostgreSQL and Alembic migrations. Redis is an infrastructure
  dependency for short-lived state and later background/realtime coordination.
- Give users UUID identifiers and store roles in a join table. A user may therefore be both a
  customer and companion without duplicate accounts.
- Keep the phone number private in the user persistence model. No public user response schema
  is introduced in Phase 4.
- Represent roles and account statuses with application enums plus database check constraints.
- Expose an unversioned liveness endpoint and a versioned dependency-aware readiness endpoint.
- Put object storage and push notifications behind provider protocols. Concrete S3 and FCM
  adapters will be added when their consuming feature and credentials are introduced.
- Define role-permission mappings now, but defer identity/session enforcement to Phase 5.

## Consequences

The backend can start and its dependencies can be observed without implementing product flows.
Authentication, booking, payment, chat, gift, and rating behavior remain intentionally absent.

