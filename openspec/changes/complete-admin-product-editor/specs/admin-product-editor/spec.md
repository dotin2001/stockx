## Purpose

Defines complete store-owned product editing so admins can control catalog content, storefront presentation, variants, stock, price, and customer product-detail behavior from managed product data.

## ADDED Requirements

### Requirement: Admins can edit complete storefront product content
The system SHALL allow authenticated admins to edit all customer-facing product content needed for a richer store product page, including existing catalog fields and structured storefront fields.

#### Scenario: Admin updates product basics and storefront content
- **WHEN** an authenticated admin submits valid changes for product name, slug, category, brand, description, image data, feature bullets, and product detail/specification fields
- **THEN** the system persists the changes and returns the updated managed product data

#### Scenario: Storefront content appears on public product detail
- **WHEN** a visitor opens a public product detail page for an active product with admin-managed storefront content
- **THEN** the page displays that content using store-oriented product labels

#### Scenario: Blank optional storefront fields are allowed
- **WHEN** an admin clears optional storefront content such as feature bullets, gallery images, or details
- **THEN** the system saves the product without those optional sections and the public page omits empty sections gracefully

#### Scenario: Invalid product content is rejected
- **WHEN** an admin submits invalid product content such as a duplicate slug, missing required category, invalid image data, or malformed structured content
- **THEN** the system rejects the update with an actionable validation or conflict error without changing the product

### Requirement: Admin editor uses store product language
The system SHALL present customer-facing and admin-facing product management controls using store language rather than marketplace ask/seller language.

#### Scenario: Public product labels avoid marketplace ask wording
- **WHEN** a visitor views product cards or product detail pages
- **THEN** price, stock, size, and availability are labeled as store product information rather than lowest ask, seller, or public listing concepts

#### Scenario: Admin inventory labels avoid customer seller wording
- **WHEN** an admin manages product stock
- **THEN** the management UI labels sellable records as inventory or stock records while preserving permissions and behavior

### Requirement: Admins can manage variants and stock records from one product editor
The system SHALL let authorized admins manage product variants and sellable stock records from the product editor without leaving the selected product context.

#### Scenario: Admin manages variants
- **WHEN** an authenticated admin creates, updates, or removes a valid product variant
- **THEN** the system applies the change and returns product data reflecting the updated variant set

#### Scenario: Authorized admin creates stock for a variant
- **WHEN** an authorized admin creates a stock record for an existing product or variant with valid price, quantity, currency, and status
- **THEN** the system creates the stock record and includes it in managed product inventory data

#### Scenario: Mismatched variant is rejected
- **WHEN** an admin attempts to create or move stock to a variant that does not belong to the selected product
- **THEN** the system rejects the request without creating or changing stock

### Requirement: Authorized admins can edit existing stock price and availability
The system SHALL allow authorized admins to update existing stock records' price, currency, variant assignment, quantity, and status while preserving cart and product references.

#### Scenario: Admin updates stock price
- **WHEN** an authorized admin updates an existing active stock record with a valid positive price and currency
- **THEN** the system saves the updated price and public product purchase options use the new price

#### Scenario: Admin updates stock quantity
- **WHEN** an authorized admin updates stock quantity to a valid non-negative value
- **THEN** the system saves the quantity and customer cart availability reflects the updated stock

#### Scenario: Admin updates stock status
- **WHEN** an authorized admin marks stock active, sold, or cancelled
- **THEN** the system saves the status and only active stock with positive quantity remains purchasable

#### Scenario: Invalid stock update is rejected
- **WHEN** an admin submits invalid stock values such as negative quantity, non-positive price, unsupported status, or invalid currency
- **THEN** the system rejects the update without changing the stock record

### Requirement: Product detail exposes store purchase options by variant
The system SHALL expose public product detail data that lets customers choose a size or variant and add the corresponding active in-stock record to cart.

#### Scenario: Product detail lists available purchase options
- **WHEN** a product has active stock with positive quantity
- **THEN** the public product detail response includes purchase options with variant labels, price, currency, stock quantity, and cartable stock identity

#### Scenario: Customer selects a variant before carting
- **WHEN** a customer selects an available size or variant on the public product detail page
- **THEN** the displayed price, stock state, and add-to-cart action correspond to the selected purchase option

#### Scenario: Product with no active stock cannot be carted
- **WHEN** a product has no active stock with positive quantity
- **THEN** the public product detail page shows an out-of-stock state and disables purchase actions while preserving browse/watchlist behavior where applicable

### Requirement: Product detail includes admin-managed stats and related products
The system SHALL enrich public product detail pages with admin-managed product stats and related product recommendations without exposing private admin or seller concepts.

#### Scenario: Product stats are displayed
- **WHEN** a visitor views a product detail page
- **THEN** the page displays relevant store product stats such as sold count, available size count, stock state, category, or brand when data exists

#### Scenario: Related products are shown
- **WHEN** a visitor views an active product with other active products in the same category or brand
- **THEN** the page displays related product cards that exclude the current product

#### Scenario: Related products handle sparse catalogs
- **WHEN** there are no suitable related products
- **THEN** the product detail page remains usable and omits the related-products section gracefully

### Requirement: Admin editor access remains protected
The system SHALL enforce admin-only access for product editing and stricter authorization for stock mutations that require elevated privileges.

#### Scenario: Customer cannot edit products
- **WHEN** an authenticated customer attempts to access product editing data or submit product edits
- **THEN** the system rejects the request without exposing or changing managed product data

#### Scenario: Anonymous user cannot edit products
- **WHEN** an unauthenticated user attempts to access product editing data or submit product edits
- **THEN** the system requires authentication and does not change product data

#### Scenario: Insufficient admin privilege cannot mutate restricted stock
- **WHEN** an admin without the required elevated privilege attempts a restricted stock mutation
- **THEN** the system rejects the mutation without changing stock data
