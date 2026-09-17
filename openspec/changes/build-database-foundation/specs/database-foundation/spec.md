## Purpose

Defines the persistent database behavior required for the StockX-style marketplace foundation, including catalog data, user accounts, admin marker storage, sessions, listings, and seed data.

## ADDED Requirements

### Requirement: User accounts identify admin access
The system SHALL persist whether each user account has admin access using an `is_admin` flag.

#### Scenario: New user defaults to non-admin access
- **WHEN** a new account is created without explicit admin access
- **THEN** the system stores the account with `is_admin` set to false

#### Scenario: Admin access can be stored
- **WHEN** an authorized administrative process creates or updates an account with admin access
- **THEN** the system stores the account with `is_admin` set to true

#### Scenario: Admin marker is always boolean
- **WHEN** account data is persisted
- **THEN** the system stores admin access as a boolean value only

### Requirement: User identity is unique and secure
The system SHALL persist user identity data with unique email addresses and password hashes instead of raw passwords.

#### Scenario: Unique email is accepted
- **WHEN** a user record has an email address not used by another user
- **THEN** the system can persist the user record

#### Scenario: Duplicate email is rejected
- **WHEN** a user record uses an email address already assigned to another user
- **THEN** the system rejects the duplicate record

#### Scenario: Raw password is not persisted
- **WHEN** account credentials are stored
- **THEN** the database contains a password hash and does not contain the raw password

### Requirement: Refresh tokens are revocable
The system SHALL persist refresh-token records that can be associated with users, expired, revoked, and rotated.

#### Scenario: Refresh token belongs to a user
- **WHEN** a refresh token record is created
- **THEN** the record is associated with exactly one user

#### Scenario: Revoked token remains unusable
- **WHEN** a refresh token is marked revoked
- **THEN** the token is not accepted as an active session token

#### Scenario: Expired token remains unusable
- **WHEN** a refresh token is past its expiration time
- **THEN** the token is not accepted as an active session token

### Requirement: Categories have stable slugs
The system SHALL persist marketplace categories with unique stable slugs.

#### Scenario: Category slug is unique
- **WHEN** a category is created with a slug not used by another category
- **THEN** the system can persist the category

#### Scenario: Duplicate category slug is rejected
- **WHEN** a category is created with a slug already used by another category
- **THEN** the system rejects the duplicate category

### Requirement: Products belong to categories
The system SHALL persist products with required category ownership, stable product slugs, display names, and pricing summary data.

#### Scenario: Product with valid category is stored
- **WHEN** a product references an existing category
- **THEN** the system can persist the product

#### Scenario: Product without valid category is rejected
- **WHEN** a product references a missing category
- **THEN** the system rejects the product record

#### Scenario: Product slug is unique
- **WHEN** a product is created with a slug not used by another product
- **THEN** the system can persist the product

#### Scenario: Price is stored safely
- **WHEN** product or listing price data is persisted
- **THEN** the system stores price values without floating-point precision loss

### Requirement: Products can have variants
The system SHALL persist optional product variants for attributes such as size, color, or SKU.

#### Scenario: Variant belongs to product
- **WHEN** a variant is created for an existing product
- **THEN** the system persists the variant as belonging to that product

#### Scenario: Variant for missing product is rejected
- **WHEN** a variant references a missing product
- **THEN** the system rejects the variant record

### Requirement: Users can own listings
The system SHALL persist marketplace listings that belong to users and products.

#### Scenario: Listing with valid owner and product is stored
- **WHEN** a listing references an existing user and product
- **THEN** the system can persist the listing

#### Scenario: Listing without valid owner is rejected
- **WHEN** a listing references a missing user
- **THEN** the system rejects the listing record

#### Scenario: Listing without valid product is rejected
- **WHEN** a listing references a missing product
- **THEN** the system rejects the listing record

### Requirement: Users can watch products
The system SHALL persist watchlist records connecting users to products without duplicate watchlist entries for the same user and product.

#### Scenario: Watchlist item is stored
- **WHEN** a user watches a product not already in their watchlist
- **THEN** the system persists the watchlist item

#### Scenario: Duplicate watchlist item is rejected
- **WHEN** a user attempts to watch the same product more than once
- **THEN** the system rejects the duplicate watchlist item

### Requirement: Records are auditable
The system SHALL persist created and updated timestamps for core marketplace records.

#### Scenario: New record includes created timestamp
- **WHEN** a core marketplace record is created
- **THEN** the system stores when the record was created

#### Scenario: Changed record includes updated timestamp
- **WHEN** a core marketplace record is updated
- **THEN** the system stores when the record was last updated

### Requirement: Development seed data is available
The system SHALL provide development seed data for representative categories and products from the current static storefront.

#### Scenario: Seed creates categories
- **WHEN** development seed data is applied to an empty database
- **THEN** the system contains representative marketplace categories including sneakers, streetwear, and collectibles

#### Scenario: Seed creates products
- **WHEN** development seed data is applied to an empty database
- **THEN** the system contains representative products with names, slugs, category links, image URLs, and pricing summary data

#### Scenario: Seed can be re-run safely
- **WHEN** development seed data is applied more than once
- **THEN** the system does not create duplicate categories or products
