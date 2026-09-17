# api-smoke-testing Specification

## Purpose

Defines reproducible running-service API smoke tests that verify the FastAPI marketplace backend, PostgreSQL data, authentication cookies, protected actions, and error responses work together through real HTTP requests.

## Requirements

### Requirement: Smoke tests verify service readiness and public catalog access
The system SHALL provide a repeatable smoke-test workflow that can confirm a running API service is reachable and can read seeded public marketplace data.

#### Scenario: Health endpoint is reachable
- **WHEN** the smoke-test workflow targets a running backend service
- **THEN** it verifies `GET /health` returns a successful response indicating the service is available

#### Scenario: Seeded categories are readable
- **WHEN** the smoke-test workflow requests `GET /api/v1/categories`
- **THEN** it verifies the response includes seeded category slugs and display names

#### Scenario: Product listing and detail are readable
- **WHEN** the smoke-test workflow requests product list and product detail endpoints for seeded data
- **THEN** it verifies product responses include stable slugs, names, categories, image URLs, price cents, sold counts, and variants where applicable

### Requirement: Smoke tests verify public search behavior
The system SHALL provide smoke coverage for the public search endpoint using seeded product data.

#### Scenario: Search returns seeded matching products
- **WHEN** the smoke-test workflow searches with a non-empty query matching seeded catalog data
- **THEN** it verifies the response includes matching product summaries

#### Scenario: Empty search is rejected consistently
- **WHEN** the smoke-test workflow searches with an empty or missing query
- **THEN** it verifies the API returns a validation-style JSON error response

### Requirement: Smoke tests verify authentication session lifecycle
The system SHALL provide smoke coverage for registration, login, current-user restore, refresh-token rotation, and logout against the running API service.

#### Scenario: Registration starts an authenticated session
- **WHEN** the smoke-test workflow registers a unique test user
- **THEN** it verifies the API returns public user data, returns an access token, and sets an HTTP-only refresh cookie

#### Scenario: Login restores an authenticated session
- **WHEN** the smoke-test workflow logs in with valid credentials for the test user
- **THEN** it verifies the API returns public user data, returns an access token, and sets or refreshes the HTTP-only refresh cookie

#### Scenario: Current user requires valid access token
- **WHEN** the smoke-test workflow requests the current user with a valid access token
- **THEN** it verifies the API returns the authenticated user's public account data

#### Scenario: Refresh rotates session token
- **WHEN** the smoke-test workflow refreshes with the active refresh cookie
- **THEN** it verifies the API returns a new access token and replaces the refresh cookie

#### Scenario: Logout revokes session
- **WHEN** the smoke-test workflow logs out with the active refresh cookie
- **THEN** it verifies the API clears the refresh cookie and rejects reuse of the logged-out session

### Requirement: Smoke tests verify protected marketplace actions
The system SHALL provide smoke coverage for protected listing and watchlist operations using authenticated requests.

#### Scenario: Listing creation requires authentication
- **WHEN** the smoke-test workflow attempts to create a listing without credentials
- **THEN** it verifies the API returns an authentication error

#### Scenario: Authenticated listing creation succeeds
- **WHEN** the smoke-test workflow creates a listing for an existing seeded product with a valid access token and positive integer price cents
- **THEN** it verifies the API creates an active listing owned by the authenticated user

#### Scenario: Watchlist add list and remove succeeds
- **WHEN** the smoke-test workflow adds a seeded product to the authenticated user's watchlist, lists the watchlist, and removes the item
- **THEN** it verifies the item appears only for that user and is removed successfully

#### Scenario: Duplicate watchlist add is rejected
- **WHEN** the smoke-test workflow adds the same product to the same user's watchlist more than once
- **THEN** it verifies the API returns a conflict-style JSON error and does not create a duplicate item

### Requirement: Smoke-test workflow is deterministic and documented
The system SHALL document how to prepare, run, and interpret API smoke tests in local development.

#### Scenario: Smoke-test setup is documented
- **WHEN** a developer reads the backend API documentation
- **THEN** it explains the required PostgreSQL service, migrations, seed data, running API server, environment variables, and smoke-test command

#### Scenario: Smoke-test data does not require manual cleanup
- **WHEN** the smoke-test workflow creates test users, listings, or watchlist records
- **THEN** it uses unique test data or cleanup behavior so repeated runs do not fail because of data left by a previous run

#### Scenario: Missing running-service prerequisites fail clearly
- **WHEN** the smoke-test workflow cannot connect to the API service or required seeded data is absent
- **THEN** it reports a clear failure message that distinguishes environment setup problems from API behavior regressions
