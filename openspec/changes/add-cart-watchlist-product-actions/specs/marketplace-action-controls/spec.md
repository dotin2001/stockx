## Purpose

Defines the marketplace controls that let authenticated users express purchase intent from product pages, manage cart quantities, and remove watched products before real checkout exists.

## ADDED Requirements

### Requirement: Product pages expose cart and buy-now actions
The system SHALL allow authenticated users to add a product's active sellable listing to their cart or start a UI-first buy-now flow from the product detail page.

#### Scenario: Authenticated user adds product listing to cart
- **WHEN** an authenticated user activates Add to Cart on a product page with an active sellable listing
- **THEN** the system adds that listing to the user's cart and confirms the cart update without leaving the product page

#### Scenario: Authenticated user starts buy-now flow
- **WHEN** an authenticated user activates Buy Now on a product page with an active sellable listing
- **THEN** the system adds that listing to the user's cart and routes the user to the cart or checkout placeholder experience

#### Scenario: Product has no active sellable listing
- **WHEN** a user views a product page that has no active sellable listing available for carting
- **THEN** the system disables or hides Add to Cart and Buy Now while preserving the ability to watch or sell the product where otherwise allowed

#### Scenario: Guest attempts purchase intent action
- **WHEN** a guest activates Add to Cart or Buy Now from a product page
- **THEN** the system sends the guest to authentication or displays an authentication-required state before any cart mutation is attempted

### Requirement: Cart items can be adjusted from account cart view
The system SHALL allow authenticated users to increase quantity, decrease quantity, remove items, and see a checkout action for their own cart items.

#### Scenario: User increases cart item quantity
- **WHEN** an authenticated user increases quantity for one of their cart items
- **THEN** the system persists the larger positive quantity and refreshes the displayed item quantity and cart total quantity

#### Scenario: User decreases cart item quantity
- **WHEN** an authenticated user decreases quantity for one of their cart items whose quantity is greater than one
- **THEN** the system persists the smaller positive quantity and refreshes the displayed item quantity and cart total quantity

#### Scenario: Cart quantity cannot go below one
- **WHEN** an authenticated user views a cart item whose quantity is one
- **THEN** the system prevents decrementing that item below one and offers removal as a separate action

#### Scenario: User removes cart item
- **WHEN** an authenticated user removes one of their cart items
- **THEN** the system deletes that cart item and removes it from the cart view without affecting other cart items

#### Scenario: Cart checkout remains UI-first
- **WHEN** an authenticated user views a non-empty cart
- **THEN** the system displays a checkout action that clearly leads to a placeholder or unavailable checkout state without creating orders, payment sessions, charges, or sold listings

### Requirement: Watchlist items can be removed from account watchlist view
The system SHALL allow authenticated users to remove watched products from their own watchlist.

#### Scenario: User removes watched product from account
- **WHEN** an authenticated user removes one of their watched products
- **THEN** the system deletes that watchlist item and removes it from the watchlist view without affecting other watched products

#### Scenario: Cross-user watchlist removal is rejected
- **WHEN** an authenticated user attempts to remove another user's watchlist item
- **THEN** the system rejects the mutation without changing the other user's watchlist
