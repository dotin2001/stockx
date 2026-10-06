## Purpose

Defines the admin-only frontend experience for creating catalog products and initial variants while preserving seller-only listing behavior for normal marketplace users.

## ADDED Requirements

### Requirement: Admins can access product creation
The system SHALL provide an authenticated admin-only frontend surface for creating catalog products.

#### Scenario: Admin opens product creation form
- **WHEN** an authenticated admin opens the admin product creation surface
- **THEN** the system shows a product creation form with category, product name, price, size, and image URL fields

#### Scenario: Non-admin user is denied product creation access
- **WHEN** an authenticated non-admin user attempts to open the product creation surface
- **THEN** the system does not show the product creation form and communicates that admin access is required

#### Scenario: Guest is denied product creation access
- **WHEN** an unauthenticated user attempts to open the product creation surface
- **THEN** the system requires login before any product creation controls are available

### Requirement: Admin product creation form uses catalog categories
The system SHALL let admins choose from existing catalog categories when creating a product.

#### Scenario: Categories load successfully
- **WHEN** an admin opens the product creation form and categories are available
- **THEN** the system shows the available categories as selectable options

#### Scenario: Categories fail to load
- **WHEN** an admin opens the product creation form and categories cannot be loaded
- **THEN** the system shows an error state and prevents product submission until categories are available

### Requirement: Admin product form creates product and initial size variant
The system SHALL create a catalog product and an initial product variant from the submitted admin form data.

#### Scenario: Admin product creation succeeds
- **WHEN** an admin submits valid category, product name, price, size, and image URL values
- **THEN** the system creates the product, creates an initial variant using the submitted size, and reports success with a link or path to the created product

#### Scenario: Product name generates a duplicate slug
- **WHEN** an admin submits a product name whose generated slug conflicts with an existing product
- **THEN** the system rejects the submission, keeps the form data available for correction, and explains that the product slug already exists

#### Scenario: Invalid form values are rejected
- **WHEN** an admin submits missing category, blank product name, non-positive price, blank size, or invalid image URL data
- **THEN** the system rejects the submission before or during API validation and shows actionable validation feedback

### Requirement: Sellers cannot add catalog products
The system SHALL keep seller product management separate from seller listing creation.

#### Scenario: Seller opens sell page
- **WHEN** an authenticated seller opens the sell page
- **THEN** the system only allows listing creation for existing catalog products and does not show product creation fields

#### Scenario: Seller attempts product creation API flow
- **WHEN** a non-admin seller attempts to create a catalog product through admin product creation controls or API calls
- **THEN** the system rejects the action without creating a product or variant
