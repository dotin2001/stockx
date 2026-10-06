## Purpose

Defines the FastAPI backend behavior that lets frontend clients authenticate users, browse and search catalog data, create listings, and manage watchlists through versioned API endpoints backed by the marketplace database.

## ADDED Requirements

### Requirement: API exposes versioned routes
The system SHALL expose backend application routes under `/api/v1` while preserving a simple health endpoint for service checks.

#### Scenario: Health check succeeds
- **WHEN** a client requests the health endpoint
- **THEN** the system returns a successful response indicating the API is available

#### Scenario: Versioned API is available
- **WHEN** a client requests a supported marketplace endpoint under `/api/v1`
- **THEN** the system handles the request through the versioned API surface

### Requirement: Users can register with email and password
The system SHALL allow new users to create accounts with name, email, and password credentials.

#### Scenario: Registration succeeds
- **WHEN** a client submits a valid unused email, display name, and acceptable password
- **THEN** the system creates a user account, stores only a password hash, returns the current user representation, and starts an authenticated session

#### Scenario: Duplicate registration is rejected
- **WHEN** a client submits an email already assigned to an existing account
- **THEN** the system rejects the request with a conflict-style error and does not create a duplicate user

#### Scenario: Invalid registration payload is rejected
- **WHEN** a client submits missing or invalid registration fields
- **THEN** the system returns validation errors without creating a user account

### Requirement: Users can authenticate and restore sessions
The system SHALL authenticate users with email/password credentials, issue short-lived access tokens, store refresh tokens in HTTP-only cookies, rotate refresh tokens on refresh, and expose the current authenticated user.

#### Scenario: Login succeeds
- **WHEN** a client submits valid email and password credentials
- **THEN** the system returns the current user representation, provides an access token, and sets a refresh token in an HTTP-only cookie

#### Scenario: Login rejects invalid credentials
- **WHEN** a client submits an unknown email or incorrect password
- **THEN** the system rejects the request without revealing which credential was invalid

#### Scenario: Current user is restored
- **WHEN** a client requests the current user with a valid access token
- **THEN** the system returns the authenticated user's public account data

#### Scenario: Refresh rotates session token
- **WHEN** a client requests token refresh with a valid refresh cookie
- **THEN** the system revokes or replaces the previous refresh token, sets a new refresh cookie, and returns a new access token

#### Scenario: Logout revokes session
- **WHEN** a client logs out with an active refresh cookie
- **THEN** the system revokes the refresh token, clears the refresh cookie, and prevents the same refresh token from being accepted again

### Requirement: Public catalog data is readable
The system SHALL expose unauthenticated catalog endpoints for categories, product lists, category-specific products, and product details.

#### Scenario: Categories are listed
- **WHEN** a client requests the category list
- **THEN** the system returns categories with stable slugs and display names

#### Scenario: Products are listed
- **WHEN** a client requests products with supported pagination parameters
- **THEN** the system returns a paginated list of products with slugs, names, category references, image URLs, lowest ask cents, and sold counts

#### Scenario: Category products are listed
- **WHEN** a client requests products for an existing category slug
- **THEN** the system returns products belonging to that category

#### Scenario: Missing category is rejected
- **WHEN** a client requests products for a category slug that does not exist
- **THEN** the system returns a not-found error

#### Scenario: Product detail is returned
- **WHEN** a client requests an existing product slug
- **THEN** the system returns product detail data including category and available variants

#### Scenario: Missing product is rejected
- **WHEN** a client requests a product slug that does not exist
- **THEN** the system returns a not-found error

### Requirement: Public search is available
The system SHALL expose an unauthenticated search endpoint for catalog products.

#### Scenario: Search returns matching products
- **WHEN** a client searches with a non-empty query
- **THEN** the system returns products whose searchable fields match the query, using the same public product summary shape as product listing responses

#### Scenario: Empty search is rejected
- **WHEN** a client searches with an empty or missing query
- **THEN** the system returns a validation error

### Requirement: Authenticated users can create listings
The system SHALL allow authenticated users to create marketplace listings for existing products and optional variants.

#### Scenario: Listing creation succeeds
- **WHEN** an authenticated user submits a valid product, optional variant, positive integer price cents, and supported currency
- **THEN** the system creates an active listing owned by that user and returns the listing data

#### Scenario: Anonymous listing creation is rejected
- **WHEN** an unauthenticated client attempts to create a listing
- **THEN** the system rejects the request with an authentication error

#### Scenario: Listing for missing product is rejected
- **WHEN** an authenticated user submits a listing for a product that does not exist
- **THEN** the system returns a not-found error and does not create the listing

#### Scenario: Invalid listing price is rejected
- **WHEN** an authenticated user submits a listing with a non-positive or non-integer price value
- **THEN** the system returns a validation error and does not create the listing

### Requirement: Authenticated users can manage watchlists
The system SHALL allow authenticated users to list, add, and remove watched products without creating duplicate watchlist entries.

#### Scenario: Watchlist is returned
- **WHEN** an authenticated user requests their watchlist
- **THEN** the system returns watched products for that user only

#### Scenario: Product is added to watchlist
- **WHEN** an authenticated user adds an existing product not already watched
- **THEN** the system creates a watchlist item and returns the watched product data

#### Scenario: Duplicate watchlist add is rejected
- **WHEN** an authenticated user adds the same product more than once
- **THEN** the system rejects the duplicate request without creating another watchlist item

#### Scenario: Watchlist item is removed
- **WHEN** an authenticated user removes one of their watchlist items
- **THEN** the system deletes that watchlist item

#### Scenario: Cross-user watchlist removal is rejected
- **WHEN** an authenticated user attempts to remove another user's watchlist item
- **THEN** the system returns a not-found or forbidden-style response without deleting the other user's item

### Requirement: Protected endpoints require backend authorization
The system SHALL enforce authentication and ownership rules in the backend for account, listing, and watchlist operations.

#### Scenario: Account access requires authentication
- **WHEN** an unauthenticated client requests protected account data
- **THEN** the system returns an authentication error

#### Scenario: Protected actions ignore frontend-only state
- **WHEN** a client calls a protected endpoint directly without valid credentials
- **THEN** the system rejects the operation regardless of any frontend UI state

### Requirement: API errors are consistent
The system SHALL return consistent JSON error responses for validation, authentication, authorization, conflict, and not-found failures.

#### Scenario: Validation error response is consistent
- **WHEN** a client submits invalid request data
- **THEN** the system returns a JSON error response with a stable error code or detail structure suitable for frontend display

#### Scenario: Not-found response is consistent
- **WHEN** a client requests a missing resource
- **THEN** the system returns a JSON not-found response without leaking internal implementation details
