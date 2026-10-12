# YONDO — Safety incident operations (internal backend)

Scope: make reports and recorded SOS alerts visible to authorized administrators for manual review. This is a development foundation, **not** emergency dispatch, incident resolution, or a production-grade safety center.

## API
- `GET /api/v1/admin/safety/summary`: unacknowledged SOS and open report counts.
- `GET /api/v1/admin/safety/reports`: paginated, private reports with optional open/in_review filter.
- `GET /api/v1/admin/safety/alerts`: paginated SOS records, optionally only unacknowledged.
- `POST /api/v1/admin/safety/reports/{id}/acknowledge`: marks a report `in_review`, writes a permanent admin acknowledgement note.
- `POST /api/v1/admin/safety/alerts/{id}/acknowledge`: records a manual SOS acknowledgement.
- Unauthorized user access fails with 403. Repeated acknowledgement returns the first immutable record; unique DB constraints prevent duplicates.
- The SOS list always explicitly reports `emergency_service_contacted=false`. **No emergency service or trusted contact is notified.**

## Still blocked
- No live on-call staffing, incident SLA, responder paging, legal/privacy approvals, formal report resolution, suspension/dispute adjudication, or support dashboards.
- No customer-facing assertion that a safety alert has been acted on in real time.
- Do not enable a closed beta with real safety-critical reliance until human and technical escalation operations are approved.
- The booking cancellation safeguard only flags money for manual refund reconciliation; it is not an automatic refund and does not define refund eligibility.
