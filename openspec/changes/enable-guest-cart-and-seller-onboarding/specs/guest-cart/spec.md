## Purpose

Defines guest shopping-cart behavior before authentication, including checkout gating and preservation of guest cart contents when the shopper signs in or creates an account.

## ADDED Requirements

### Requirement: Guests can add active listings to a cart
The system SHALL allow unauthenticated guests to add active sellable listings for non-archived products to a cart without requiring login first.

#### Scenario: Guest adds active listing
- **WHEN** a guest adds an active listing for a non-archived product to cart
- **THEN** the system stores the listing and quantity in a guest cart and confirms the cart update

#### Scenario: Guest add merges duplicate listing
- **WHEN** a guest adds a listing that already exists in the guest cart
- **THEN** the system keeps one cart row for that listing and increases or updates the quantity according to the request

#### Scenario: Guest cannot add unavailable listing
- **WHEN** a guest attempts to add a missing, inactive, or archived-product listing to cart
- **THEN** the system rejects the action without adding the item to the guest cart

### Requirement: Guests can view and manage their cart
The system SHALL let guests view, increase quantity, decrease quantity, and remove items from their own guest cart before checkout.

#### Scenario: Guest views cart
- **WHEN** a guest opens the cart experience
- **THEN** the system displays the guest cart items with product, listing, quantity, and availability information

#### Scenario: Guest updates quantity
- **WHEN** a guest changes a cart item quantity to a valid positive integer
- **THEN** the system updates the guest cart item and refreshes the displayed quantity and total

#### Scenario: Guest removes cart item
- **WHEN** a guest removes an item from the guest cart
- **THEN** the system removes that item without affecting other cart items

### Requirement: Checkout requires authentication
The system SHALL require signup or login before checkout can proceed while preserving the shopper's cart intent.

#### Scenario: Guest starts checkout
- **WHEN** a guest with cart items activates checkout
- **THEN** the system routes the guest to login or signup and indicates that authentication is required before checkout

#### Scenario: Guest cart survives authentication redirect
- **WHEN** a guest is sent to login or signup from checkout
- **THEN** the system preserves the guest cart so the items can be restored after successful authentication

#### Scenario: Authenticated checkout remains placeholder
- **WHEN** an authenticated user starts checkout before payments and orders exist
- **THEN** the system displays a checkout placeholder without creating orders, payment sessions, charges, or sold listings

### Requirement: Guest cart merges into account cart after authentication
The system SHALL merge a shopper's guest cart into their authenticated account cart after login or signup.

#### Scenario: Guest cart merges after login
- **WHEN** a guest with cart items logs in successfully
- **THEN** the system transfers the guest cart items into the authenticated user's account cart

#### Scenario: Guest cart merges after signup
- **WHEN** a guest with cart items creates an account successfully
- **THEN** the system transfers the guest cart items into the new authenticated user's account cart

#### Scenario: Merge preserves existing account cart items
- **WHEN** a guest cart is merged into an account that already has cart items
- **THEN** the system keeps existing account cart items and merges duplicate listing quantities without creating duplicate listing rows for the same user

#### Scenario: Merge skips unavailable items
- **WHEN** a guest cart contains a listing that is no longer active or whose product is archived at merge time
- **THEN** the system does not add that unavailable item to the account cart and reports or displays that it was skipped

### Requirement: Account dashboard remains the authenticated marketplace hub
The system SHALL keep authenticated marketplace account activity visible from the account dashboard.

#### Scenario: Dashboard shows listings, watchlist, and cart
- **WHEN** an authenticated user opens the account dashboard
- **THEN** the system displays the user's listings, watchlist, cart, and checkout action or placeholder state

#### Scenario: Guest dashboard access is gated
- **WHEN** a guest attempts to access the account dashboard
- **THEN** the system requires login or signup before showing account-specific listings, watchlist, or cart data
