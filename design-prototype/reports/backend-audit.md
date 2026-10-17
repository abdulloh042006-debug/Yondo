# Backend / delivery audit (engineering-handoff pass)
Labels: **PASS** verified · **FAIL** verified failure · **BLOCKED** could not verify · **NOT IMPLEMENTED** does not exist · **OUT OF SCOPE** excluded by phase/roadmap or by an explicit instruction.
Environment: Linux sandbox, Python 3.12, PostgreSQL 16 (installed locally for this audit), headless Chromium. Branch `design/prototype`, base `origin/codex/notification-integration`. No backend source file was modified.

## Historical reports vs reality
| Claim in the handoff | Status |
|---|---|
| `D:\Yondo`, `D:\Yondo-Phase6-validation\*.xml/log` (109 passed + 2 skipped) | **BLOCKED**: Windows paths/reports are not available in this environment; they were neither read nor trusted. |
| “Phase 6 = companion system only” | Repository is far past Phase 6 (14 migrations incl. bookings, payments, chat, safety, gifts, notifications). Verified below against the current code, not the old numbers. |
| Native PostgreSQL validation “unresolved” | **PASS** now (below). |

## Database (native PostgreSQL 16, clean DB)
| Check | Result |
|---|---|
| `alembic upgrade head` from empty DB | **PASS**: 14 migrations, exit 0 |
| `alembic check` (model/migration drift) | **PASS**: “No new upgrade operations detected” |
| `alembic downgrade base` → `upgrade head` → `check` | **PASS**: 14 down, 14 up, no drift; single head `20261013_0014` |
| Existing backend suite, PostgreSQL | **PASS**: 200 passed, 0 skipped, exit 0 |
| Existing backend suite, SQLite | **PASS**: 192 passed, 8 skipped (PostgreSQL-only), exit 0 |
| PG-only concurrency tests (`-k postgres`) | **PASS** on native PG: 4 passed (exclusion constraint on direct inserts, concurrent availability inserts cannot overlap, two buyers/last stock, repeated checkout creates one order). **Skipped on SQLite** (4 skipped), so SQLite is not a substitute. |
| New decision/contract tests against the real backend | **PASS**: 50 passed on SQLite and 50 on PostgreSQL 16 (`tests/backend`) |

## Static / contract / security
| Check | Result |
|---|---|
| `ruff check` | **PASS** (“All checks passed”) |
| `ruff format --check` | **FAIL (pre-existing, not enforced by CI)**: 50 files would be reformatted. Left untouched to avoid an unrelated mass diff. |
| OpenAPI generated vs checked-in (`export_openapi.py --check`) | **PASS** |
| Operations without a security scheme | 13 of 125, all intentional: OTP request/verify/refresh, public discovery (3), public gift products (2), health (2), payment webhook, CLICK test prepare/complete. |
| Admin operations secured | **PASS**: 27/27 declare a security scheme (role enforcement itself is covered by the backend's own tests; not re-derived here). |
| Public responses expose phone/secrets | **PASS**: none (only the token response on auth). |
| Secrets in tracked files at HEAD | **PASS**: no token/key patterns, no `.env`/key/db/log files tracked. `.env.example` holds local-dev placeholders only. |
| Webhook replay protection | **PASS (by code + existing tests)**: events are de-duplicated through `PaymentEventReceipt(provider_event_id)`. Signature verification is delegated to the payment provider adapter; **no real provider exists (NOT IMPLEMENTED)**, so signature validation against a live provider is **BLOCKED**. |
| CLICK test endpoints | Gated by `click_test_enabled`, forbidden outside `development`/`test` by a settings validator; signature compared with `hmac.compare_digest`. |
| Reporter identity | **PASS (real test)**: derived from the token; client-supplied `reporter_id` is rejected 422. |
| Report/block target | **PASS (real tests)**: profile id ⇒ 404; self ⇒ 422; unauthenticated ⇒ 401; counterparty enforced with `booking_id`. |
| Companion user id visible to customers | **PASS (real test)**: not exposed; consequence: no documented profile→user mapping (see `docs/03`). Incidental user-id exposure in `ChatMessageResponse.sender_id`, `ReviewRead.reviewee_id` noted. |

## Scope items from the handoff
| Item | Status |
|---|---|
| Companion system (applications, profile, services, availability, activation gates) | **PASS** by existing backend suite (PG 200/200) + real `tests/backend` checks of availability/price validation. Not re-audited line by line. |
| Identity verification provider | **NOT IMPLEMENTED** (protocol/status only); activation stays gated. |
| Payment provider, live charges/refunds/payouts | **NOT IMPLEMENTED / OUT OF SCOPE**: unconfigured provider returns 503; no real money was moved or attempted; no fee/cancellation/refund rules invented. |
| Combined booking+gift checkout, delivery pricing, courier | **NOT IMPLEMENTED**: checkout always 503; delivery fee setting does not exist. |
| Gift orders | Offline CLICK-simulated test orders only (`real_money_moved=false`); fulfilment is manual/operator. Not operational delivery. |
| SOS | Records an alert for manual review; `emergency_service_contacted=false`; UI says so. Not an emergency service. |
| Notifications | In-app inbox only. FCM/SMS/email/scheduled reminders **NOT IMPLEMENTED**. |
| Vendor panel / admin UI / mobile client | **NOT IMPLEMENTED in the repo** (`apps/mobile`, `apps/admin` are README stubs). The design prototype is a mock-backed prototype, not a client. |
| Real-device and screen-reader testing | **BLOCKED** (no devices/AT available). |
| CI result for the pushed branch | **BLOCKED**: unauthenticated GitHub API is rate-limited and the sandbox cannot read the workflow page. |
| Push to GitHub | **BLOCKED**: no approved authentication mechanism in this environment (a token pasted in chat earlier is treated as compromised and was not reused). |

## Findings
1. Backend already implements the availability-containment decision; no change required.
2. `ruff format` drift in 50 files (CI does not enforce format).
3. No CORS configuration in the backend (matters for any browser client on another origin).
4. Large amounts: JSON numbers above 2^53−1 are not exact in JavaScript; backend stores 64-bit values.
5. Profile→user id mapping missing (blocks customer-side report/block of companions).
6. No staging environment/test accounts documented (`docs/04-staging-readiness.md`).

## Readiness
Internal testing of the backend with the DEMO/mocked prototype: **ready**. Closed beta: **not ready** (needs SMS provider, payment provider + approved fee/cancellation policy, identity provider, real client, staging, device/AT testing, owner decisions above). Production: **not ready**.
