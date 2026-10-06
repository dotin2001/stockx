## Purpose

Defines admin-only catalog management behavior so privileged users can create, update, archive, restore, and manage marketplace products while normal users retain read-only catalog access.

## ADDED Requirements

### Requirement: Admin users can create products
The system SHALL allow authenticated admin users to create catalog products with required category ownership, stable slugs, display fields, optional pricing summary data, and optional image URLs.

#### Scenario: Admin product creation succeeds
- **WHEN** an authenticated admin submits a valid product with an existing category and unused slug
- **THEN** the system creates the product and returns the created product data

#### Scenario: Non-admin product creation is rejected
- **WHEN** an authenticated non-admin submits a product creation request
- **THEN** the system rejects the request without creating a product

#### Scenario: Anonymous product creation is rejected
- **WHEN** an unauthenticated client submits a product creation request
- **THEN** the system rejects the request without creating a product

#### Scenario: Duplicate product slug is rejected
- **WHEN** an admin submits a product creation request using a slug already assigned to another product
- **THEN** the system rejects the request with a conflict-style error

#### Scenario: Missing product category is rejected
- **WHEN** an admin submits a product creation request referencing a category that does not exist
- **THEN** the system rejects the request with a not-found or validation-style error

### Requirement: Admin users can update products
The system SHALL allow authenticated admin users to update product catalog fields while preserving product identity and relational integrity.

#### Scenario: Admin product update succeeds
- **WHEN** an authenticated admin submits valid updates for an existing product
- **THEN** the system applies the updates and returns the updated product data

#### Scenario: Product slug update remains unique
- **WHEN** an admin updates a product slug to a slug already assigned to another product
- **THEN** the system rejects the request with a conflict-style error

#### Scenario: Non-admin product update is rejected
- **WHEN** an authenticated non-admin submits a product update request
- **THEN** the system rejects the request without changing the product

#### Scenario: Missing product update is rejected
- **WHEN** an admin submits an update for a product that does not exist
- **THEN** the system returns a not-found error

### Requirement: Admin users can archive and restore products
The system SHALL allow authenticated admin users to archive products instead of hard deleting them, and to restore archived products when needed.

#### Scenario: Product archive succeeds
- **WHEN** an authenticated admin archives an existing active product
- **THEN** the system marks the product as archived and prevents it from appearing in public product lists, category product lists, public search results, and public product detail responses

#### Scenario: Archived product can be restored
- **WHEN** an authenticated admin restores an archived product
- **THEN** the system marks the product as active and allows it to appear in public catalog responses again

#### Scenario: Non-admin archive is rejected
- **WHEN** an authenticated non-admin attempts to archive or restore a product
- **THEN** the system rejects the request without changing the product

#### Scenario: Archived product remains referentially intact
- **WHEN** a product is archived
- **THEN** existing listings, cart items, watchlist items, and future historical records that reference the product remain valid database records

### Requirement: Admin users can read managed products
The system SHALL provide authenticated admin users a management view of products that can include both active and archived products.

#### Scenario: Admin product list includes archived filtering
- **WHEN** an authenticated admin requests the managed product list with supported filters
- **THEN** the system returns paginated products and can distinguish active products from archived products

#### Scenario: Non-admin managed product list is rejected
- **WHEN** an authenticated non-admin requests the managed product list
- **THEN** the system rejects the request

### Requirement: Admin users can manage product variants
The system SHALL allow authenticated admin users to create, update, and remove product variants for existing products.

#### Scenario: Admin variant creation succeeds
- **WHEN** an authenticated admin submits a valid variant for an existing product
- **THEN** the system creates the variant and returns the variant data

#### Scenario: Admin variant update succeeds
- **WHEN** an authenticated admin submits valid updates for an existing variant
- **THEN** the system applies the updates and returns the updated variant data

#### Scenario: Admin variant removal succeeds
- **WHEN** an authenticated admin removes an existing variant
- **THEN** the system removes the variant from future product detail responses without deleting the parent product

#### Scenario: Non-admin variant management is rejected
- **WHEN** an authenticated non-admin attempts to create, update, or remove a product variant
- **THEN** the system rejects the request without changing variant data

#### Scenario: Variant for missing product is rejected
- **WHEN** an admin submits a variant creation request for a product that does not exist
- **THEN** the system returns a not-found error

### Requirement: Public catalog remains read-only for normal users
The system SHALL keep public product browsing available to all clients while preventing normal users from managing product records.

#### Scenario: Public active products remain readable
- **WHEN** any client requests active products through the public catalog endpoints
- **THEN** the system returns active product data using the existing public product response shapes

#### Scenario: Public catalog excludes archived products
- **WHEN** any client requests public product lists, category product lists, search results, or product detail for archived products
- **THEN** the system excludes archived products or returns not-found for archived product detail
