## ADDED Requirements

### Requirement: Smoke tests verify customer cart shopping actions
The system SHALL provide smoke coverage for customer shopping actions using public catalog access, guest cart resolution, and authenticated cart requests without requiring customer watchlist or customer-to-admin message flows.

#### Scenario: Guest cart can resolve active listing
- **WHEN** the smoke-test workflow resolves a guest cart containing an active seeded listing
- **THEN** it verifies the response includes the listing as available with product, listing, quantity, and pricing data

#### Scenario: Authenticated cart add list and remove succeeds
- **WHEN** the smoke-test workflow adds an active seeded listing to the authenticated user's cart, lists the cart, and removes the item
- **THEN** it verifies the cart item appears only for that user and is removed successfully

#### Scenario: Duplicate authenticated cart add merges quantity
- **WHEN** the smoke-test workflow adds the same active listing to the same authenticated user's cart more than once
- **THEN** it verifies the API keeps one cart item for the listing and reflects the merged quantity

#### Scenario: Customer watchlist smoke coverage is not required
- **WHEN** the smoke-test workflow verifies customer shopping behavior
- **THEN** it does not need to create, list, remove, or duplicate-check watchlist items

#### Scenario: Customer message smoke coverage is not required
- **WHEN** the smoke-test workflow verifies customer shopping behavior
- **THEN** it does not need to create or list customer-to-admin messages

## REMOVED Requirements

### Requirement: Smoke tests verify protected marketplace actions
**Reason**: Customer shopping scope no longer includes customer watchlist behavior, and store-owned selling changes no longer require authenticated customer listing creation as part of the shopping smoke path.

**Migration**: Use `Smoke tests verify customer cart shopping actions` for guest cart and authenticated cart coverage. Keep unauthenticated listing rejection coverage in another capability only if listing-management smoke coverage remains relevant.
