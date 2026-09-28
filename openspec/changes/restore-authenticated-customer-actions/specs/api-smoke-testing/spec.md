## ADDED Requirements

### Requirement: Smoke tests verify authenticated customer account actions
The system SHALL provide running-service smoke coverage for guest cart behavior and authenticated customer cart, watchlist, and message-admin behavior.

#### Scenario: Guest cart can resolve active listing
- **WHEN** the smoke-test workflow resolves a guest cart containing an active seeded listing
- **THEN** it verifies the response includes the listing as available with product, listing, quantity, and pricing data

#### Scenario: Authenticated cart add list and remove succeeds
- **WHEN** the smoke-test workflow adds an active seeded listing to the authenticated user's cart, lists the cart, and removes the item
- **THEN** it verifies the cart item appears only for that user and is removed successfully

#### Scenario: Duplicate authenticated cart add merges quantity
- **WHEN** the smoke-test workflow adds the same active listing to the same authenticated user's cart more than once
- **THEN** it verifies the API keeps one cart item for the listing and reflects the merged quantity

#### Scenario: Authenticated watchlist add list and remove succeeds
- **WHEN** the smoke-test workflow adds a seeded product to the authenticated user's watchlist, lists the watchlist, and removes the item
- **THEN** it verifies the watchlist item appears only for that user and is removed successfully

#### Scenario: Duplicate authenticated watchlist add is rejected
- **WHEN** the smoke-test workflow adds the same product to the same authenticated user's watchlist more than once
- **THEN** it verifies the API returns a conflict-style JSON error and does not create a duplicate item

#### Scenario: Authenticated customer message create and list succeeds
- **WHEN** the smoke-test workflow creates a customer-to-admin message as an authenticated customer and lists customer messages
- **THEN** it verifies the created message is visible in that customer's message list

## REMOVED Requirements

### Requirement: Smoke tests verify protected marketplace actions
**Reason**: The storefront is now store-owned, so customer listing creation is no longer part of the customer shopping smoke path, and customer account actions need clearer cart, watchlist, and message coverage.

**Migration**: Use `Smoke tests verify authenticated customer account actions` for guest cart, authenticated cart, authenticated watchlist, and authenticated customer message coverage.
