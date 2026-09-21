## Purpose

Defines stable conflict behavior for duplicate-sensitive marketplace writes so clients receive API errors instead of raw database failures during races or retries.

## ADDED Requirements

### Requirement: Product slug conflicts are stable
The system SHALL return a conflict-style API error when product slug uniqueness would be violated during admin product creation or update.

#### Scenario: Duplicate product create slug is rejected
- **WHEN** an admin creates a product using a slug already assigned to another product
- **THEN** the system returns a stable conflict error and does not create a duplicate product

#### Scenario: Duplicate product update slug is rejected
- **WHEN** an admin updates a product to use a slug already assigned to another product
- **THEN** the system returns a stable conflict error and does not change the product slug

#### Scenario: Concurrent product slug conflict is rejected cleanly
- **WHEN** two admin writes race to use the same product slug and the database uniqueness constraint detects the conflict
- **THEN** the system returns a stable conflict error without exposing raw database exception details

### Requirement: Cart duplicate listing writes are stable
The system SHALL keep one cart item per user and listing even when duplicate add requests are retried or race concurrently.

#### Scenario: Duplicate cart add merges quantity
- **WHEN** an authenticated user adds a listing that is already in their cart
- **THEN** the system returns one cart item for that user and listing with the merged quantity

#### Scenario: Concurrent duplicate cart add is resolved cleanly
- **WHEN** duplicate add-to-cart requests race for the same user and listing and the database uniqueness constraint detects a conflict
- **THEN** the system resolves the conflict into a single cart item response or returns a stable conflict error without exposing raw database exception details

#### Scenario: Different users carting same listing remains valid
- **WHEN** different authenticated users add the same active listing to their carts
- **THEN** the system stores separate user-scoped cart items without treating them as duplicates

### Requirement: Watchlist duplicate writes are stable
The system SHALL return stable duplicate behavior when a user attempts to watch the same product more than once.

#### Scenario: Duplicate watchlist add is rejected
- **WHEN** an authenticated user adds a product that is already in their watchlist
- **THEN** the system returns a stable conflict error and does not create a duplicate watchlist item

#### Scenario: Concurrent duplicate watchlist add is rejected cleanly
- **WHEN** duplicate watchlist add requests race for the same user and product and the database uniqueness constraint detects a conflict
- **THEN** the system returns a stable conflict error without exposing raw database exception details

### Requirement: Constraint errors use consistent API shape
The system SHALL translate expected database integrity conflicts in marketplace write paths into the established API error response shape.

#### Scenario: Expected integrity conflict response shape
- **WHEN** a known uniqueness or availability conflict occurs in a marketplace write path
- **THEN** the response contains the standard `error.code` and `error.message` structure

#### Scenario: Raw database details are not exposed
- **WHEN** the database reports a handled integrity conflict
- **THEN** the response does not include raw SQL, constraint stack traces, or driver exception text
