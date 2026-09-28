## Purpose

Defines the customer action boundary for the storefront: guests can browse and build a cart, while authenticated customers can additionally use account actions such as watchlist and store-admin messaging.

## ADDED Requirements

### Requirement: Guests can browse and cart without account actions
The system SHALL allow guests to browse public catalog content and add active sellable items to a guest cart without exposing watchlist or message-admin actions.

#### Scenario: Guest views public product content
- **WHEN** a guest opens home, category, search, or product detail experiences
- **THEN** the system displays public product information without requiring authentication

#### Scenario: Guest adds active sellable item to cart
- **WHEN** a guest adds an active sellable listing for a public product to cart
- **THEN** the system stores the item in the guest cart and confirms the cart update without requiring login

#### Scenario: Guest does not see watchlist prompt
- **WHEN** a guest views a product detail page
- **THEN** the system does not show Add to Watchlist, Log in to Watch, or equivalent watchlist prompts

#### Scenario: Guest does not use message-admin action
- **WHEN** a guest browses customer-facing storefront or account-gated experiences
- **THEN** the system does not accept a message-admin submission until the shopper authenticates

### Requirement: Authenticated customers can use watchlist actions
The system SHALL allow authenticated non-admin customers to add products to their watchlist and manage watched products from their account.

#### Scenario: Customer watches product
- **WHEN** an authenticated customer adds a product to their watchlist
- **THEN** the system stores the watchlist item for that customer and confirms the update

#### Scenario: Customer removes watched product
- **WHEN** an authenticated customer removes one of their watched products from the account watchlist
- **THEN** the system deletes that watchlist item without affecting other customers' watchlists

#### Scenario: Customer watchlist remains private
- **WHEN** an authenticated customer lists or mutates watchlist items
- **THEN** the system only exposes or changes watchlist records owned by that customer

### Requirement: Authenticated customers can message store admins
The system SHALL allow authenticated non-admin customers to send messages to store admins and view their own message history.

#### Scenario: Customer sends message
- **WHEN** an authenticated customer submits a valid message to the store admin
- **THEN** the system stores the message with sender, subject, body, unread admin state, and timestamps

#### Scenario: Customer sees own recent messages
- **WHEN** an authenticated customer opens the customer account message surface
- **THEN** the system displays only messages sent by that customer

#### Scenario: Empty message is rejected
- **WHEN** an authenticated customer submits a blank or invalid message
- **THEN** the system rejects the message with validation feedback and does not create a message record

### Requirement: Customer account combines cart watchlist and messages
The system SHALL present authenticated customer account functionality for identity, cart, watchlist, checkout state, and message-admin workflows.

#### Scenario: Customer account shows action sections
- **WHEN** an authenticated non-admin customer opens the account dashboard
- **THEN** the system shows account identity, cart, watchlist, checkout state, and message-admin sections

#### Scenario: Guest account access remains gated
- **WHEN** a guest attempts to access account-only customer information
- **THEN** the system requires login or signup before showing account-specific cart, watchlist, or message data
