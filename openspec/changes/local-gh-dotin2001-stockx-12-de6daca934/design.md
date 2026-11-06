## Context

The FastAPI application already has conventional health routing, centralized error responses, PostgreSQL sessions, Stripe checkout/webhook services, administrative service boundaries, and SQLAlchemy/Alembic persistence. This change crosses request middleware, error handling, payment processing, administrative mutations, inventory flows, configuration, and the database. See `proposal.md` and the two capability specs for the behavioral contract.

## Goals / Non-Goals

**Goals:**

- Establish low-cardinality, privacy-safe operational events that can feed standard log aggregation and alerting.
- Keep readiness, reporting, and auditing failure semantics explicit and testable.
- Make audit creation transactional with the affected mutation and efficient to filter.
- Preserve provider webhook idempotency while surfacing terminal failures.

**Non-Goals:**

- Selecting or provisioning a hosted observability vendor, dashboard, paging service, or log collector.
- Building a general event-sourcing system or storing full entity snapshots.
- Exposing public metrics or audit records to customers.
- Replacing Stripe's webhook delivery and retry behavior.

## Decisions

### Separate process liveness from dependency readiness

Keep the existing lightweight liveness endpoint independent of external services and add a readiness endpoint that executes a minimal `SELECT 1` through the normal session dependency. Catch database-layer failures and return a stable sanitized 503 response. This lets orchestrators restart dead processes without causing database outages to create restart loops. A single combined health endpoint was rejected because it cannot represent these two states independently.

### Centralize request correlation and structured event emission

Use HTTP middleware to validate a bounded caller request ID or generate an opaque one, store it in request state, return it on every response, and emit one JSON completion event. Route templates, not raw paths, prevent identifiers and search terms from becoming log dimensions. A small allowlisting event helper will accept only scalar bounded values. Free-form framework access logs alone were rejected because they do not provide a consistent privacy or correlation contract.

### Isolate error reporting behind a narrow adapter

Represent error reporting with a small backend interface configured from validated settings, initially supporting disabled and outbound webhook modes. Send only request ID, route template, method, and exception type. Bound the call with a short timeout and convert reporter failures into a structured local event. Direct vendor calls from exception handlers were rejected because they couple response reliability and tests to an external service.

### Treat payment observability as domain events

Emit stable event names and failure categories at payment state transitions and Stripe webhook failure boundaries. Persist webhook processing status and an abbreviated error category before emitting, so redelivery remains idempotent and the database remains the reconciliation source of truth. Raw provider payloads, exception text, and customer details stay out of telemetry. Monitoring can alert on these event/category pairs without introducing a metrics dependency.

### Persist append-only administrative audit rows transactionally

Add a dedicated audit table containing actor user ID, action, target type/ID, request ID, allowlisted JSON facts, and a server timestamp. Audit writers run within the caller's database transaction and flush without committing; the mutation service owns the commit. Inventory flows without an interactive administrator use an explicit accountable system context or the authenticated marketplace actor rather than a nullable, ambiguous actor. A generic application log was rejected because it cannot provide transactional durability or indexed review.

Add indexes for newest-first browsing and common actor/action/target filters. Expose bounded, administrator-protected retrieval through the versioned API. Audit update/delete operations are not exposed, preserving append-only application behavior; database privileges and retention policy remain deployment concerns.

## Risks / Trade-offs

- [Synchronous database readiness can amplify an outage] → Keep the query minimal, use the configured short connection timeout, and rely on orchestrator probe intervals.
- [Cardinality or sensitive data can leak through telemetry] → Use route templates, stable categories, scalar allowlists, length bounds, and tests that reject raw paths, payloads, and secrets.
- [A reporter thread or network call can consume resources] → Use a bounded executor, strict timeout, disabled-by-default backend, and local failure events.
- [Audit coverage can drift as mutation paths grow] → Centralize audit writing in mutation services and add tests for each administrative and inventory transition, including rollback cases.
- [Audit rows increase write volume and storage] → Store compact allowlisted deltas, index only supported filters, paginate reads, and define retention separately when operational requirements are known.
- [Existing databases need a safe schema transition] → Use an additive deterministic migration with indexes and verify upgrade and downgrade behavior.

## Migration Plan

1. Add the audit model and additive Alembic migration; apply it before deploying code that writes audit rows.
2. Deploy readiness, request middleware, structured events, error-reporter configuration, payment monitoring, and transactional audit writers with reporting disabled unless explicitly configured.
3. Configure the orchestrator to use liveness and readiness separately, forward structured logs, and alert on application, payment, and webhook failure categories.
4. Enable the error-reporting backend only after its endpoint and egress policy are validated.
5. Roll back application code first if necessary; retain audit data during rollback. Downgrade the migration only after confirming no deployed code depends on the table and after preserving any required audit evidence.
