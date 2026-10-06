## Purpose

Defines the store-owned selling flow where guests and authenticated users shop as customers, while store admins own catalog and inventory management.

## ADDED Requirements

### Requirement: Guests can shop without seller capabilities
The system SHALL allow guests to browse public catalog content and build a guest cart without exposing seller registration, product creation, or listing creation actions.

#### Scenario: Guest browses catalog
- **WHEN** a guest opens product, category, search, or home catalog experiences
- **THEN** the system displays public product information without requiring authentication

#### Scenario: Guest adds product to cart
- **WHEN** a guest adds an active sellable item to cart
- **THEN** the system stores the cart item in the guest cart and does not require login first

#### Scenario: Guest checkout requires authentication
- **WHEN** a guest starts checkout from a non-empty cart
- **THEN** the system routes the guest to login or signup while preserving cart intent

#### Scenario: Guest cannot access seller flow
- **WHEN** a guest attempts to access a seller registration, seller listing, product creation, or listing creation surface
- **THEN** the system does not show seller controls and directs the guest to customer shopping or authentication as appropriate

### Requirement: Authenticated users are store customers
The system SHALL treat authenticated non-admin users as customers who can manage account information, watch products, manage cart contents, start checkout, and contact the store admin.

#### Scenario: Customer uses account dashboard
- **WHEN** an authenticated non-admin user opens the account dashboard
- **THEN** the system shows customer account information, watchlist, cart, checkout state, and store contact or message actions

#### Scenario: Customer watches product
- **WHEN** an authenticated non-admin user adds a product to their watchlist
- **THEN** the system stores the watchlist item for that user

#### Scenario: Customer cart is durable
- **WHEN** an authenticated non-admin user adds, updates, or removes cart items
- **THEN** the system persists the cart changes for that user account

#### Scenario: Customer does not see seller controls
- **WHEN** an authenticated non-admin user opens product detail, account, navigation, or former seller routes
- **THEN** the system does not show seller registration, seller listing, product creation, or user-owned listing controls

### Requirement: Store admins own selling management
The system SHALL reserve catalog product creation and store selling-management actions for authenticated admins.

#### Scenario: Admin can access catalog management
- **WHEN** an authenticated admin opens admin product management
- **THEN** the system allows admin-only catalog product management actions

#### Scenario: Non-admin cannot manage catalog
- **WHEN** a guest or authenticated non-admin attempts to access admin product management
- **THEN** the system rejects or hides access without relying only on frontend navigation

#### Scenario: Current admin role remains flat
- **WHEN** the system checks admin access during this change
- **THEN** the system uses the existing admin authorization model and does not require supreme-admin behavior

### Requirement: Seller marketplace behavior is inactive for customers
The system SHALL disable customer-facing seller profile and user-created listing behavior for the store-owned selling flow.

#### Scenario: Existing seller entry point is disabled
- **WHEN** a customer opens a route or control that previously created seller profiles or user-owned listings
- **THEN** the system explains that selling is managed by the store and offers customer shopping or admin-appropriate navigation

#### Scenario: Customer listing API creation is rejected
- **WHEN** an authenticated non-admin user attempts to create a listing through an API path
- **THEN** the system rejects the request without creating a listing

#### Scenario: Historical seller data does not break customer flow
- **WHEN** a user already has legacy seller profile or listing records
- **THEN** the system still presents the user as a customer in the storefront and does not expose seller management controls

### Requirement: Checkout remains protected and non-payment
The system SHALL keep checkout protected behind authentication and SHALL NOT create payments, orders, fulfillment records, or sold-listing transitions in this change.

#### Scenario: Customer starts checkout
- **WHEN** an authenticated customer starts checkout from a non-empty cart
- **THEN** the system shows the current checkout placeholder or order-intent state without charging the customer

#### Scenario: Checkout does not mutate sales records
- **WHEN** checkout is started during this change
- **THEN** the system does not create payment sessions, charges, fulfilled orders, or sold listing state
