## 1. Service Health and Request Correlation

- [x] 1.1 Add separate liveness and database-backed readiness endpoints with a minimal query, bounded connection behavior, and sanitized 503 errors; verify tests cover healthy, unavailable-database, and liveness-during-outage cases.
- [x] 1.2 Add request-context middleware that validates or generates bounded request IDs, stores the effective ID for downstream use, and exposes it on success, validation-error, not-found, and unexpected-error responses; verify middleware tests cover valid, missing, invalid-character, and oversized IDs.

## 2. Structured Events and Error Reporting

- [x] 2.1 Implement a centralized structured-event helper that emits parseable JSON with allowlisted bounded scalar fields and route templates; verify tests prove request completion fields are present and raw paths, credentials, personal data, payloads, and exception messages are absent.
- [x] 2.2 Emit correlated request-completion and unexpected-application-error events from middleware while preserving the existing sanitized API error contract; verify focused API tests cover successful and failing requests.
- [x] 2.3 Add validated disabled/webhook error-reporter configuration and a narrow timeout-bounded adapter; verify tests cover successful reporting, disabled mode, reporter rejection, and timeout without changing the client response.
- [x] 2.4 Document safe production configuration for readiness probes, structured-log forwarding, reporter settings, and request-ID response exposure in the API environment example and README; verify every documented setting is accepted by configuration tests.

## 3. Payment and Stripe Webhook Monitoring

- [x] 3.1 Emit structured events for payment attempts entering failed terminal states with stable categories, safe attempt identifiers, transition states, and source; verify checkout and payment service tests cover each failure path without customer or provider-secret data.
- [x] 3.2 Persist a stable failure summary and emit a webhook-failure event for Stripe verification, correlation, validation, and processing failures while preserving terminal-event idempotency; verify webhook tests cover each category and duplicate delivery.
- [x] 3.3 Add an operator-facing mapping of payment/webhook event names and categories to recommended alerts or reconciliation actions; verify the documented names match emitted event assertions in tests.

## 4. Durable Administrative and Inventory Audit

- [x] 4.1 Add the append-only audit model and deterministic Alembic migration with actor identity, action, target, request ID, bounded facts, server timestamp, constraints, and supported query indexes; verify migration upgrade and downgrade plus model constraint tests against PostgreSQL.
- [x] 4.2 Implement a centralized audit writer that allowlists bounded before/after facts and participates in the caller transaction without committing independently; verify unit tests exclude sensitive and unknown fields and prove rollback removes the audit row.
- [x] 4.3 Integrate audit writes into every administrative create/update/delete/access mutation and verify service/API tests assert the actor, action, target, timestamp, and request ID for each successful path.
- [x] 4.4 Integrate audit writes into every inventory quantity transition, including administrative edits, listing changes, checkout reservation, release, and completed sale, using an authenticated actor or explicit accountable system identity; verify tests assert before/after quantity facts and atomic rollback behavior.
- [x] 4.5 Add administrator-protected, bounded audit-history retrieval with actor/action/target/time filters, deterministic newest-first ordering, and pagination; verify authorization, filtering, ordering, and page-limit API tests.

## 5. Integrated Verification

- [x] 5.1 Run the backend test suite and verify readiness, observability, payment/webhook, audit, and existing marketplace/auth tests pass with no regression.
- [x] 5.2 Apply the Alembic migration to PostgreSQL, run the audit and payment smoke paths, then downgrade and re-upgrade; verify the migration is reversible and the final schema is current.
- [x] 5.3 Exercise a production-like configuration with database readiness, request correlation, log capture, a failing error reporter, a failed payment, a failed/duplicate webhook, and an audited inventory mutation; verify expected sanitized responses, structured events, alerts, and durable audit records end to end.
