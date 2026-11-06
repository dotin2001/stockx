## Purpose

Provide production operators with safe service-health signals, correlated structured telemetry, and actionable visibility into application and payment-processing failures.

## ADDED Requirements

### Requirement: Liveness and database readiness are distinct
The service SHALL expose a liveness response that does not depend on PostgreSQL and a readiness response that verifies the configured database can execute a minimal query. The readiness response MUST return a service-unavailable status and a stable, non-sensitive error code when the database check fails.

#### Scenario: Database is available
- **WHEN** an operator requests readiness and the configured database accepts and executes the check
- **THEN** the service returns a successful readiness response

#### Scenario: Database is unavailable
- **WHEN** an operator requests readiness and the database check raises a connectivity or database error
- **THEN** the service returns HTTP 503 with a stable readiness error code and no database credentials or internal exception detail

#### Scenario: Liveness during database failure
- **WHEN** the process is running but the database is unavailable
- **THEN** the liveness response remains successful while readiness fails

### Requirement: Requests have safe correlation identifiers
The service SHALL associate every HTTP request with a request ID, accept a caller-provided ID only when it matches the documented bounded safe format, generate a new ID otherwise, include the effective ID in the response, and make it available to operational events produced while processing that request.

#### Scenario: Valid request ID supplied
- **WHEN** a caller sends a request ID containing only permitted characters within the maximum length
- **THEN** the response and request-scoped telemetry use that request ID

#### Scenario: Missing or invalid request ID
- **WHEN** the request ID is absent, malformed, or longer than the maximum length
- **THEN** the service generates a new opaque request ID and returns it in the response

### Requirement: Request and application events are structured and privacy-safe
The service SHALL emit machine-parseable structured events for completed requests and unexpected application errors. Events MUST use route templates rather than raw request paths, MUST include the request ID and relevant bounded operational fields, and MUST exclude credentials, raw payment payloads, personal data, and exception messages.

#### Scenario: Request completes
- **WHEN** an HTTP request finishes
- **THEN** one structured completion event records the request ID, method, route template, response status, and duration

#### Scenario: Unexpected error occurs
- **WHEN** request handling raises an unhandled exception
- **THEN** a structured application-error event is emitted and the caller receives a sanitized error response containing the request ID header

### Requirement: Unexpected errors can be reported without affecting responses
The service SHALL support a configurable error-reporting backend for unexpected application failures. Reporter payloads MUST contain only allowlisted, bounded correlation and classification fields, and reporter timeout or failure MUST NOT replace or delay the application response beyond a configured short timeout.

#### Scenario: Reporter is configured
- **WHEN** an unexpected application error occurs and a reporter is enabled
- **THEN** the service sends a sanitized report containing the request ID, route template, method, and exception type

#### Scenario: Reporter is unavailable
- **WHEN** the reporting backend times out or rejects a report
- **THEN** the service emits a reporter-failure operational event and still returns the sanitized application response

### Requirement: Payment and webhook failures produce monitorable events
The service SHALL emit structured operational events for payment attempts that enter a failed terminal state and for Stripe webhook events that cannot be verified, correlated, or processed. Each event MUST include a stable failure category and only safe identifiers needed for diagnosis; monitoring systems MUST be able to alert by event name and category.

#### Scenario: Payment attempt fails
- **WHEN** a payment attempt transitions to a failed terminal state
- **THEN** a structured payment-failure or transition event identifies the attempt, its previous and next states, its source, and a stable failure category when available

#### Scenario: Stripe webhook processing fails
- **WHEN** a supported Stripe webhook cannot be verified, correlated, validated, or applied
- **THEN** the service records the processing outcome and emits a structured webhook-failure event with the provider event identifier and stable failure category

#### Scenario: Duplicate terminal webhook is received
- **WHEN** a previously finalized Stripe webhook event is delivered again
- **THEN** processing remains idempotent and does not emit a new false failure or repeat the payment transition
