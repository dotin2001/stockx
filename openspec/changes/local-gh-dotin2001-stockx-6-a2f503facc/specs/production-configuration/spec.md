## Purpose

Defines fail-fast configuration and health behavior required to run the API safely in production environments.

## ADDED Requirements

### Requirement: Production startup rejects unsafe authentication configuration
The API SHALL refuse to start in production when the JWT signing secret is missing, is a documented development placeholder, or lacks the configured minimum strength, or when refresh cookies are not secure and HTTP-only with an explicitly supported SameSite policy.

#### Scenario: Placeholder signing secret in production
- **WHEN** the API starts in production with the default or otherwise rejected JWT signing secret
- **THEN** startup fails with a configuration error that identifies the invalid setting without exposing secret values

#### Scenario: Insecure refresh cookie in production
- **WHEN** the API starts in production with secure refresh cookies disabled
- **THEN** startup fails before serving requests

### Requirement: Production CORS origins are explicit and safe
The API SHALL accept credentialed production CORS requests only from configured absolute HTTPS origins and SHALL reject wildcard, credential-bearing, path-bearing, query-bearing, fragment-bearing, malformed, duplicate-normalized, and local origins.

#### Scenario: Unsafe production origin
- **WHEN** production configuration contains a wildcard, HTTP non-local origin, local origin, or value that is not an origin
- **THEN** startup fails and identifies the invalid CORS setting

#### Scenario: Allowed production origin
- **WHEN** a request origin exactly matches a validated configured HTTPS origin
- **THEN** the API emits credentialed CORS headers for that origin

### Requirement: Checkout configuration is internally consistent
The API SHALL validate at startup that the checkout mode, Stripe key environment, webhook secret, frontend origin, livemode expectation, and fake-provider setting describe one consistent deployment environment.

#### Scenario: Mixed Stripe environments
- **WHEN** production Stripe mode combines test and live settings or enables the fake provider
- **THEN** startup fails without logging any Stripe secret

#### Scenario: Stripe disabled
- **WHEN** checkout mode is disabled and no Stripe credentials are supplied
- **THEN** startup succeeds with Stripe checkout unavailable

### Requirement: Liveness and readiness are distinct
The API SHALL expose a liveness result that does not depend on PostgreSQL and a readiness result that succeeds only when required startup configuration is valid and the database accepts a bounded probe.

#### Scenario: Database unavailable
- **WHEN** the process is running but PostgreSQL cannot complete the readiness probe
- **THEN** liveness succeeds and readiness returns a non-success status without exposing connection credentials

