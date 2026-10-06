## Purpose

Defines the admin product and inventory management experience so store admins can review and edit catalog products while supreme admins control sellable stock quantity and status.

## ADDED Requirements

### Requirement: Admin users can browse managed products in the UI
The system SHALL provide an authenticated admin product management page that lists managed products with enough information to inspect catalog state and inventory state.

#### Scenario: Normal admin views product management
- **WHEN** an authenticated normal admin opens the product management page
- **THEN** the frontend shows a paginated or otherwise bounded list of managed products with product identity, category, active or archived catalog state, price or inventory summary, and available admin actions for that role

#### Scenario: Supreme admin views product management
- **WHEN** an authenticated supreme admin opens the product management page
- **THEN** the frontend shows the managed product list and additionally exposes supreme-admin inventory quantity and status controls

#### Scenario: Customer product management is blocked
- **WHEN** an authenticated customer opens the product management page
- **THEN** the frontend shows an access-denied state and the backend rejects managed product data requests

#### Scenario: Anonymous product management is blocked
- **WHEN** an unauthenticated user opens the product management page
- **THEN** the frontend shows a login-required state and the backend rejects managed product data requests

### Requirement: Admin users can edit catalog product details from the UI
The system SHALL allow authenticated admin users to update catalog product details from the admin product management UI while preserving existing backend validation and public catalog behavior.

#### Scenario: Normal admin updates product details
- **WHEN** an authenticated normal admin submits valid catalog field changes for an existing product
- **THEN** the system applies the changes and refreshes the product management UI with the updated product data

#### Scenario: Product detail update validation is shown
- **WHEN** an admin submits invalid catalog product changes
- **THEN** the frontend shows the backend validation or conflict error without silently discarding the admin's entered values

#### Scenario: Non-admin product detail update is rejected
- **WHEN** an authenticated customer or anonymous user attempts to update a product through direct navigation or API use
- **THEN** the system rejects the request without changing the product

### Requirement: Admin users can manage variants from product management
The system SHALL allow authenticated admin users to view and manage product variants from the admin product management UI.

#### Scenario: Admin views product variants
- **WHEN** an authenticated admin opens a product management detail or edit view
- **THEN** the frontend shows the product variants associated with that product

#### Scenario: Admin changes product variants
- **WHEN** an authenticated admin creates, edits, or removes a product variant using valid input
- **THEN** the system applies the variant change and refreshes the product management view

#### Scenario: Variant management errors are shown
- **WHEN** an admin variant action fails validation or targets a missing product or variant
- **THEN** the frontend shows an actionable error state without corrupting the visible product data

### Requirement: Supreme admins can manage inventory quantity
The system SHALL allow only supreme admins to adjust available sellable quantity for managed product inventory.

#### Scenario: Supreme admin increases inventory quantity
- **WHEN** an authenticated supreme admin adds quantity to a product or variant inventory item
- **THEN** the system increases available sellable quantity, keeps the value non-negative, and returns the updated inventory state

#### Scenario: Supreme admin decreases inventory quantity
- **WHEN** an authenticated supreme admin removes quantity from a product or variant inventory item
- **THEN** the system decreases available sellable quantity without allowing the value to go below zero and returns the updated inventory state

#### Scenario: Normal admin quantity mutation is rejected
- **WHEN** an authenticated normal admin attempts to add or remove inventory quantity
- **THEN** the system rejects the request without changing inventory quantity

#### Scenario: Invalid quantity mutation is rejected
- **WHEN** a supreme admin submits a non-positive adjustment amount or otherwise invalid quantity payload
- **THEN** the system rejects the request without changing inventory quantity

### Requirement: Supreme admins can manage inventory status
The system SHALL allow only supreme admins to change sellable inventory status from the product management UI.

#### Scenario: Supreme admin activates inventory
- **WHEN** an authenticated supreme admin marks inventory active
- **THEN** the inventory can be used for public buying flows when its product is not archived and its available quantity is greater than zero

#### Scenario: Supreme admin marks inventory unavailable
- **WHEN** an authenticated supreme admin marks inventory sold, cancelled, or otherwise unavailable
- **THEN** the inventory is excluded from public buying flows and existing carts identify the item as unavailable

#### Scenario: Normal admin status mutation is rejected
- **WHEN** an authenticated normal admin attempts to change inventory status
- **THEN** the system rejects the request without changing inventory status

### Requirement: Inventory quantity affects public buying availability
The system SHALL use managed inventory quantity and status when determining whether customers can add an item to cart or proceed with cart quantities.

#### Scenario: Product with available active inventory can be carted
- **WHEN** a customer adds an active inventory item with available quantity greater than zero to cart
- **THEN** the system accepts the cart action up to the available quantity limit

#### Scenario: Zero quantity inventory cannot be carted
- **WHEN** a customer attempts to add an inventory item with zero available quantity to cart
- **THEN** the system rejects the cart action as unavailable

#### Scenario: Cart quantity above available inventory is rejected
- **WHEN** a customer attempts to add or update a cart quantity above available inventory
- **THEN** the system rejects the request without increasing the cart quantity beyond availability

#### Scenario: Existing cart reflects reduced availability
- **WHEN** an admin reduces inventory below a customer's existing cart quantity or marks the inventory unavailable
- **THEN** the cart response indicates the affected cart item is unavailable or quantity-limited rather than silently deleting it
