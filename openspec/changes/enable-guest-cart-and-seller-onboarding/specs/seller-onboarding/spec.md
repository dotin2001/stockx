## Purpose

Defines how authenticated users become sellers by providing contact details, and how seller eligibility gates listing creation in the marketplace.

## ADDED Requirements

### Requirement: Authenticated users can register as sellers
The system SHALL allow authenticated non-seller users to register as sellers by providing required seller contact information.

#### Scenario: Seller registration succeeds
- **WHEN** an authenticated user submits a valid phone number and address details
- **THEN** the system records the seller profile, marks the user as eligible to sell, and returns the updated seller/account state

#### Scenario: Missing seller contact data is rejected
- **WHEN** an authenticated user submits seller registration without required phone number or address details
- **THEN** the system rejects the request with validation errors and does not mark the user as eligible to sell

#### Scenario: Guest seller registration is rejected
- **WHEN** a guest attempts to register as a seller
- **THEN** the system rejects the request with an authentication error

#### Scenario: Existing seller registration is idempotent
- **WHEN** an authenticated seller submits seller registration again with valid contact details
- **THEN** the system updates or returns the seller profile without creating duplicate seller records

### Requirement: Seller status is visible to authenticated users
The system SHALL expose whether the current authenticated user is eligible to sell and provide their seller contact details where appropriate.

#### Scenario: Current user includes seller eligibility
- **WHEN** an authenticated user restores their session or requests current account data
- **THEN** the system indicates whether the user is eligible to sell

#### Scenario: Seller profile can be viewed by owner
- **WHEN** an authenticated seller views their account or sell flow
- **THEN** the system shows their seller phone and address details needed for seller management

### Requirement: Listing creation requires seller registration
The system SHALL allow only registered sellers to create marketplace listings for existing non-archived catalog products.

#### Scenario: Registered seller creates listing
- **WHEN** a registered seller submits valid listing data for an existing non-archived catalog product
- **THEN** the system creates an active listing owned by that seller

#### Scenario: Non-seller listing creation is rejected
- **WHEN** an authenticated user who has not registered as a seller attempts to create a listing
- **THEN** the system rejects the request without creating a listing and tells the client seller registration is required

#### Scenario: Seller cannot create listing for unavailable product
- **WHEN** a registered seller attempts to create a listing for a missing or archived product
- **THEN** the system rejects the request without creating a listing

### Requirement: Sell page guides users through seller onboarding
The system SHALL guide authenticated non-seller users to complete seller registration before showing the listing creation form.

#### Scenario: Non-seller opens sell page
- **WHEN** an authenticated user who is not seller-eligible opens the sell page
- **THEN** the system shows seller registration fields for phone number and address instead of the listing creation form

#### Scenario: Seller opens sell page
- **WHEN** a registered seller opens the sell page
- **THEN** the system shows the listing creation form for existing catalog products

#### Scenario: Guest opens sell page
- **WHEN** a guest opens the sell page
- **THEN** the system requires login or signup before seller registration or listing creation
