## Why

The backend's current development-friendly defaults, refresh-token rotation, authentication surface, and operational signals are not sufficient for a production deployment. Production readiness also requires reproducible Python installs and durable audit evidence for sensitive inventory and administrator actions.

## What Changes

- Add fail-fast production configuration validation for JWT secrets, refresh-cookie policy, explicit CORS origins, database connectivity settings, and internally consistent Stripe mode/credential settings.
- Make refresh-token rotation concurrency-safe with database row locking and token families; treat reuse of a rotated token as replay and revoke the entire family.
- Harden account access with authentication rate limits, standards-based email validation, email verification, password reset, logout on all devices, and stable `email_exists` conflict responses during concurrent registration.
- Separate liveness from database readiness, and add structured request/error logs with propagated request IDs and pluggable error reporting.
- Add payment health monitoring and durable administrator/inventory audit records without logging secrets or sensitive token material.
- Replace open-ended backend dependency ranges with a reproducible Python dependency lock and resolve deprecation warnings covered by the backend test suite.

## Capabilities

### New Capabilities

- `production-configuration`: Startup validation and production-safe configuration rules for authentication, cookies, CORS, database connectivity, and Stripe.
- `authentication-hardening`: Concurrency-safe refresh-token families, replay response, rate limiting, verified-email and password-recovery flows, global logout, and deterministic registration conflicts.
- `service-observability`: Database readiness, request correlation, structured logging, sanitized error reporting, and payment-health monitoring behavior.
- `administrative-audit`: Durable, attributable audit records for administrator and inventory mutations with protected read access.
- `python-dependency-reproducibility`: Reproducible backend dependency installation and deprecation-free supported runtime behavior.

### Modified Capabilities

- None. No corresponding authentication, production operations, audit, or dependency requirements are present in the main specification set.

## Impact

- Affected backend areas include settings/startup, FastAPI middleware and error handling, health endpoints, auth schemas/routes/services, refresh-token and user persistence, payment operations, and administrator inventory services.
- Database migrations will add token-family and account-verification/recovery state plus audit records and supporting indexes/constraints.
- Authentication API behavior will add verification, recovery, and global-logout operations while preserving existing login/refresh/logout routes and stable error envelopes.
- Operations will gain production startup checks, readiness and monitoring signals, structured logs, request correlation, and sanitized error-reporting integration.
- Python dependency metadata and a committed lock artifact will define reproducible production and development environments; backend tests will cover configuration, concurrency, auth abuse controls, observability, and audit behavior.
