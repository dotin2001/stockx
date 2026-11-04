## Purpose

Defines privacy-safe operational signals for correlating requests, diagnosing failures, and monitoring payment processing.

## ADDED Requirements

### Requirement: Every HTTP request has a correlation identifier
The API SHALL accept a valid bounded request identifier or generate one, return it in the response, and attach it to logs and reported errors for that request.

#### Scenario: Missing request identifier
- **WHEN** an HTTP request arrives without an accepted request identifier
- **THEN** the API generates one and returns the same value in the response and associated log records

#### Scenario: Invalid request identifier
- **WHEN** the supplied identifier violates the documented character or length policy
- **THEN** the API replaces it with a generated identifier rather than reflecting the unsafe value

### Requirement: Request and error logs are structured and sanitized
The API SHALL emit machine-parseable request completion and application error records containing bounded operational fields while excluding passwords, cookies, authorization headers, tokens, Stripe secrets, webhook payloads, and other configured sensitive data.

#### Scenario: Handled API error
- **WHEN** a request ends in a handled API error
- **THEN** one structured completion record includes request ID, route template, method, status, duration, and stable error code without sensitive request data

#### Scenario: Unexpected exception
- **WHEN** an unhandled exception occurs
- **THEN** the client receives the standard sanitized server-error envelope and the server records correlated diagnostic information

### Requirement: Error reporting is configurable and non-blocking
The API SHALL support a production error-reporting integration that receives sanitized unexpected failures and SHALL continue serving the normal error response if reporting is unavailable.

#### Scenario: Reporter unavailable
- **WHEN** reporting an unexpected exception fails or times out
- **THEN** the API still returns its standard server-error response and records the reporting failure locally

### Requirement: Payment processing health is monitorable
The system SHALL expose operator-consumable, non-secret signals for failed webhook processing, stale or failed payment attempts, overdue inventory reservations, and reconciliation outcomes.

#### Scenario: Failed webhook processing
- **WHEN** a stored Stripe event transitions to failed processing
- **THEN** monitoring records a correlated failure category and event identifier without including payload contents or credentials

#### Scenario: Reconciliation run
- **WHEN** scheduled payment reconciliation completes
- **THEN** it emits structured counts for examined, recovered, failed, and still-stale records

