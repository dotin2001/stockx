## Purpose

Defines seller and admin listing lifecycle behavior so marketplace listings remain manageable, scoped to their owner, and consistent with product availability.

## ADDED Requirements

### Requirement: Listings respect product availability
The system SHALL prevent new marketplace listings from being created for products that are not publicly sellable.

#### Scenario: Create listing for active product succeeds
- **WHEN** an authenticated user creates a listing for an existing non-archived product with valid pricing data
- **THEN** the system creates an active listing owned by that user

#### Scenario: Create listing for archived product is rejected
- **WHEN** an authenticated user creates a listing for an archived product
- **THEN** the system rejects the request without creating a listing

#### Scenario: Create listing for missing product is rejected
- **WHEN** an authenticated user creates a listing for a product that does not exist
- **THEN** the system returns a not-found error without creating a listing

### Requirement: Sellers can view their own listings
The system SHALL allow authenticated users to view listings they own without exposing other users' private listing management views.

#### Scenario: Seller listing list returns owned listings
- **WHEN** an authenticated user requests their own listing management view
- **THEN** the system returns only listings owned by that user

#### Scenario: Anonymous seller listing list is rejected
- **WHEN** an unauthenticated client requests a seller listing management view
- **THEN** the system rejects the request with an authentication error

### Requirement: Sellers can cancel their active listings
The system SHALL allow authenticated users to cancel active listings they own while preventing cross-user mutation.

#### Scenario: Seller cancels own active listing
- **WHEN** an authenticated user cancels an active listing they own
- **THEN** the system marks the listing as cancelled and prevents it from being treated as active

#### Scenario: Seller cannot cancel another user's listing
- **WHEN** an authenticated user attempts to cancel a listing owned by another user
- **THEN** the system rejects the request without changing the listing

#### Scenario: Seller cancellation of missing listing is rejected
- **WHEN** an authenticated user attempts to cancel a listing that does not exist
- **THEN** the system returns a not-found error

#### Scenario: Seller cancellation is idempotent for cancelled listing
- **WHEN** an authenticated user cancels one of their listings that is already cancelled
- **THEN** the system returns the cancelled listing without changing ownership or product data

### Requirement: Admin users can inspect and cancel listings
The system SHALL allow authenticated admin users to inspect marketplace listings and cancel listings for moderation or cleanup.

#### Scenario: Admin listing list returns managed listings
- **WHEN** an authenticated admin requests the managed listing list with supported filters
- **THEN** the system returns paginated listings with owner, product, price, and status data

#### Scenario: Admin cancels any active listing
- **WHEN** an authenticated admin cancels an active listing
- **THEN** the system marks the listing as cancelled without deleting the listing record

#### Scenario: Non-admin listing management is rejected
- **WHEN** an authenticated non-admin requests admin listing management or attempts admin listing cancellation
- **THEN** the system rejects the request without exposing or changing managed listing data

#### Scenario: Anonymous listing management is rejected
- **WHEN** an unauthenticated client requests admin listing management or attempts admin listing cancellation
- **THEN** the system rejects the request with an authentication error
