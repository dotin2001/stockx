## Why

Production operators need a reliable way to distinguish process liveness from database readiness, correlate requests across logs and errors, detect payment-processing failures, and reconstruct sensitive administrative or inventory mutations. Without a unified operational contract, failures can remain silent or be difficult to diagnose and accountability records can be incomplete.

## What Changes

- Add a database-backed readiness probe that fails safely when PostgreSQL is unavailable while retaining a separate liveness signal.
- Emit structured request and application logs with a validated or generated request ID, and return that correlation ID to callers.
- Report unexpected application errors through a configurable, failure-isolated reporting integration without exposing secrets or customer data.
- Emit monitorable events for payment failures and Stripe webhook processing errors, including stable categories and safe correlation fields.
- Persist queryable audit records for administrative actions and inventory changes with the actor, affected record, timestamp, request correlation, and bounded non-sensitive change facts.

## Capabilities

### New Capabilities

- `production-observability`: Defines service readiness, request correlation, structured operational events, error reporting, and payment/webhook failure monitoring.
- `administrative-audit-log`: Defines durable audit records for administrative and inventory mutations and authorized audit retrieval.

### Modified Capabilities

None.

## Impact

- FastAPI application middleware, health/readiness routes, error handling, and environment configuration.
- Payment checkout and Stripe webhook processing services.
- Administrative and inventory mutation services and APIs.
- PostgreSQL models and an Alembic migration for durable audit records and indexes.
- Backend tests and operator-facing environment examples for readiness, telemetry, reporting, and audit behavior.
