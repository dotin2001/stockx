## Purpose

Defines how supreme admins create sellable listing inventory directly from product management so every managed product can become available without leaving the admin product workflow.

## ADDED Requirements

### Requirement: Supreme admins can create sellable listings from product management
The system SHALL allow an authenticated supreme admin to create a sellable listing for a managed product from the admin product management inventory panel.

#### Scenario: Supreme admin creates first listing for product with no listings
- **WHEN** a supreme admin opens a managed product whose listing inventory is empty and submits a valid listing creation form
- **THEN** the system creates a sellable listing for that product and refreshes the product inventory panel with the new listing row

#### Scenario: Supreme admin creates additional listing for product with existing listings
- **WHEN** a supreme admin submits a valid listing creation form for a managed product that already has inventory rows
- **THEN** the system adds a new listing without removing or overwriting existing listings

#### Scenario: Listing can target base product or variant
- **WHEN** a supreme admin creates a listing and selects either no variant or one of the product's variants
- **THEN** the created listing is associated with the selected product and optional variant

### Requirement: Listing creation captures sellable inventory fields
The system SHALL require listing creation from product management to capture the fields needed for the listing to become editable and, when active with positive quantity, publicly buyable.

#### Scenario: Create active listing with available quantity
- **WHEN** a supreme admin submits a valid positive price, valid currency, positive initial available quantity, and active status
- **THEN** the system creates an active listing with that quantity and includes it in public buying availability when the product is not archived

#### Scenario: Create unavailable listing intentionally
- **WHEN** a supreme admin submits a valid listing with sold or cancelled status or zero available quantity
- **THEN** the system creates the listing but excludes it from public buying availability until it is active with available quantity greater than zero

#### Scenario: Invalid listing creation is rejected
- **WHEN** a supreme admin submits an invalid listing creation payload, such as a non-positive price, negative quantity, invalid currency, invalid status, missing product, archived product, or variant that does not belong to the product
- **THEN** the system rejects the request without creating a listing and shows the validation or conflict error in the admin product management UI

### Requirement: Non-supreme users cannot create product inventory listings
The system SHALL restrict admin product inventory listing creation to supreme admins.

#### Scenario: Normal admin sees restricted creation state
- **WHEN** an authenticated normal admin opens the product management inventory panel for a product with no listings
- **THEN** the frontend does not offer a create-listing form and indicates that supreme admin access is required for sellable inventory creation

#### Scenario: Normal admin direct request is rejected
- **WHEN** an authenticated normal admin attempts to create a product inventory listing through direct API use
- **THEN** the backend rejects the request without creating a listing

#### Scenario: Customer or anonymous request is rejected
- **WHEN** a customer or anonymous user attempts to create a product inventory listing through direct navigation or API use
- **THEN** the system rejects the request without creating a listing

### Requirement: Product management reflects newly created listings
The system SHALL update managed product inventory summaries after a listing is created from product management.

#### Scenario: Inventory summary updates after creation
- **WHEN** a supreme admin successfully creates a listing from the product management inventory panel
- **THEN** the product row and selected product detail show updated total listings, active listings, available quantity, and lowest active price when applicable

#### Scenario: New listing is immediately editable
- **WHEN** a supreme admin successfully creates a listing from the product management inventory panel
- **THEN** the new listing appears with the existing quantity adjustment and status controls available for subsequent edits
