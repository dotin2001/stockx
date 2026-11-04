## 1. Production Configuration and Health

- [x] 1.1 Add an explicit application-environment profile and production validators for signing-secret strength, secure refresh-cookie policy, safe normalized CORS origins, and database settings; verify focused settings tests accept local defaults and reject each unsafe production case without exposing values
- [x] 1.2 Consolidate Stripe cross-field validation across checkout mode, key environment, webhook secret, frontend origin, livemode expectation, and fake-provider use; verify the configuration matrix tests cover disabled, test, live, and mixed invalid combinations
- [x] 1.3 Separate process liveness from a bounded PostgreSQL readiness probe and document the endpoints; verify API tests show liveness remains successful while readiness returns a sanitized non-success response when the database is unavailable

## 2. Session and Account Persistence

- [x] 2.1 Add an Alembic migration and SQLAlchemy models for refresh-token family identity, user verification state, single-use verification/reset challenges, and required indexes/constraints; verify PostgreSQL upgrade, model assertions, and downgrade complete successfully
- [x] 2.2 Backfill existing refresh-token chains into deterministic families before enforcing non-null constraints; verify migration tests cover independent tokens, linked chains, and malformed legacy relationships safely
- [x] 2.3 Add the append-only administrative audit model and migration with actor/action/target/request/timestamp fields and bounded JSON facts; verify database tests cover constraints, indexes, relationships, and migration rollback

## 3. Refresh Rotation and Revocation

- [x] 3.1 Refactor refresh issuance and rotation to create families, lock the presented token row, and atomically issue at most one replacement; verify unit and PostgreSQL concurrency tests prove two simultaneous refreshes cannot both succeed
- [x] 3.2 Detect reuse only for replaced tokens, revoke every active token in that family, clear the cookie, and return `invalid_refresh_token`; verify replay tests cover descendants, ordinary logout, expiration, and unrelated families
- [x] 3.3 Add authenticated logout-all behavior that revokes every active refresh token for the current user; verify route/service tests show other users remain unaffected and all of the caller's prior refresh cookies fail

## 4. Authentication Abuse Controls and Account Lifecycle

- [x] 4.1 Replace ad hoc email checks with standards-aware validation while retaining canonical normalization and targeted uniqueness-error translation; verify invalid-address and concurrent PostgreSQL registration tests return validation errors or `email_exists`, never a server error
- [x] 4.2 Implement a configurable authentication rate-limit interface, deterministic test store, production shared-store adapter, privacy-preserving keys, and trusted-proxy policy; verify tests cover per-endpoint limits, successful/failed attempts, 429 error shape, `Retry-After`, multi-worker semantics, and store failure policy
- [x] 4.3 Implement verification challenge issuance, generic resend responses, delivery abstraction, single-use consumption, expiry, and public verification state; verify tests cover known/unknown emails, token digest storage, reuse, expiration, rate limits, and delivery failure reporting
- [x] 4.4 Implement password-reset challenge issuance and consumption with policy-compliant password hashing and atomic all-session revocation; verify tests cover enumeration resistance, invalid/reused/expired tokens, successful login with the new password, and failure of every old session
- [x] 4.5 Register and document the verification, reset, and logout-all routes using the existing API error envelope; verify OpenAPI/route tests confirm request validation, response schemas, cookie behavior, and protected-route enforcement

## 5. Request Correlation, Logs, and Error Reporting

- [x] 5.1 Add outer request-context middleware that validates or generates bounded request IDs, returns them on responses, and makes them available to handlers/services; verify tests cover absent, accepted, invalid, and oversized IDs across success and error responses
- [x] 5.2 Add structured request completion and application-error events using route templates and allowlisted bounded fields; verify captured-log tests cover handled and unexpected errors and assert that credentials, cookies, tokens, secrets, payloads, and raw personal paths are absent
- [x] 5.3 Add a configurable, time-bounded error-reporter interface for sanitized unexpected exceptions; verify tests prove correlated reports are emitted and reporter failures do not replace the standard server-error response

## 6. Payment Monitoring and Administrative Audit

- [x] 6.1 Emit structured payment signals for webhook failures, payment-attempt transitions, overdue reservations, and reconciliation summaries from existing durable state; verify payment and reconciliation tests assert categories/counts while excluding provider secrets and webhook payloads
- [x] 6.2 Add an operator-facing payment health check or command for failed/stale attempts and overdue reservations with bounded output; verify tests cover healthy, degraded, and database-error outcomes without exposing customer or credential data
- [x] 6.3 Write allowlisted audit records in the same transaction as administrator role changes and administrator inventory quantity/status mutations; verify success and rollback tests prove records are attributable, request-correlated, sanitized, and transactionally atomic
- [x] 6.4 Add a protected, newest-first paginated administrator audit query with bounded actor/action/target/time filters and no mutation endpoints; verify authorization, filtering, stable ordering, pagination limits, and response redaction tests

## 7. Dependency Reproducibility and Warning Cleanup

- [x] 7.1 Select and configure a Python 3.12-compatible lock workflow, update direct dependency declarations required by this change, and generate a committed lock containing production and development transitive versions; verify a clean environment installs exact versions without an unconstrained solve
- [x] 7.2 Update project-owned deprecated usage and compatible dependency versions until actionable deprecation warnings are removed; verify the backend suite passes with the selected warning categories treated as errors
- [x] 7.3 Add a lock-consistency check to the trusted backend verification workflow and document locked installation/update commands; verify an unchanged lock passes and a stale lock is detected

## 8. Integrated Verification

- [x] 8.1 Extend the auth smoke path through registration, verification, login, refresh, replay rejection, password reset, restored login, and logout-all; verify the smoke command completes against local PostgreSQL without printing secrets or raw action tokens
- [x] 8.2 Run the complete backend unit and PostgreSQL test suites, Alembic upgrade/downgrade/upgrade cycle, lock consistency check, and production configuration startup matrix; verify every command succeeds with actionable deprecation warnings enabled
- [x] 8.3 Update backend operator documentation and environment examples for production settings, secure cookies/CORS, shared rate limits, delivery/error-reporting adapters, readiness, request IDs, payment monitoring, audit access, migration order, and rollback; verify every documented command and setting name matches the implemented CLI and settings model
