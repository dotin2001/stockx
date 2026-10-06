## Purpose

Defines the reduced customer shopping scope for the store-owned storefront: shoppers can browse public products and use cart actions, while watchlist and customer-to-admin messaging actions are not part of the customer experience.

## ADDED Requirements

### Requirement: Guests can browse and cart without login
The system SHALL allow unauthenticated guests to view public catalog content and add active sellable items to a guest cart without requiring login first.

#### Scenario: Guest views public product content
- **WHEN** a guest opens home, category, search, or product detail experiences
- **THEN** the system displays public product information without requiring authentication

#### Scenario: Guest adds active sellable item to cart
- **WHEN** a guest adds an active sellable listing for a public product to cart
- **THEN** the system stores the item in the guest cart and confirms the cart update without requiring login

#### Scenario: Guest checkout remains authentication gated
- **WHEN** a guest starts checkout from a cart with items
- **THEN** the system routes the guest to login or signup while preserving cart intent

### Requirement: Product pages only expose shopping actions to customers
The system SHALL limit customer-facing product detail actions to viewing product information, adding available items to cart, and starting buy-now cart intent.

#### Scenario: Product page shows cart actions for active listing
- **WHEN** a guest or authenticated customer views a product with an active sellable listing
- **THEN** the system offers cart-oriented actions for that listing without requiring watchlist or admin-message actions

#### Scenario: Product page has no watchlist action
- **WHEN** a guest or authenticated customer views any product detail page
- **THEN** the system does not show Add to Watchlist, Log in to Watch, or equivalent watchlist prompts

#### Scenario: Product page handles unavailable listing
- **WHEN** a guest or authenticated customer views a product with no active sellable listing
- **THEN** the system explains that no active ask is available without offering watchlist-based follow-up actions

### Requirement: Account customer surfaces exclude watchlist and admin messaging
The system SHALL present customer account functionality around identity, cart, and checkout state without customer-facing watchlist management or message-admin workflows.

#### Scenario: Customer account shows cart without watchlist
- **WHEN** an authenticated non-admin customer opens the account dashboard
- **THEN** the system shows account and cart information without a watchlist section or watched-product management controls

#### Scenario: Customer account excludes message-admin workflow
- **WHEN** an authenticated non-admin customer opens the account dashboard
- **THEN** the system does not show a message-admin form, recent admin-message history, or calls to action to contact the store admin from that surface

#### Scenario: Guest account access remains gated
- **WHEN** a guest attempts to access account-only customer information
- **THEN** the system requires login or signup before showing account-specific data

### Requirement: Customer-facing clients do not depend on removed actions
The system SHALL ensure customer-facing shopping flows do not require watchlist or customer-to-admin message APIs in order to browse, cart, or use account cart features.

#### Scenario: Product browsing works without watchlist API usage
- **WHEN** a customer opens a public product detail page
- **THEN** the system can render the page and complete cart actions without creating, listing, or deleting watchlist items

#### Scenario: Account cart works without message API usage
- **WHEN** an authenticated customer opens the account dashboard to manage their cart
- **THEN** the system can render and mutate cart data without listing or creating customer-to-admin messages
