## Purpose

Defines repeatable representative products and optional admin-owned inventory for local catalog, cart, and checkout development.

## ADDED Requirements

### Requirement: Seed catalog contains five products per category
The development seed SHALL define exactly five seeded products for Sneakers, Streetwear, and Collectibles, with stable unique slugs, display images, and positive integer-cent USD prices.

#### Scenario: Fresh catalog seed
- **WHEN** catalog seeding runs on a migrated database
- **THEN** five configured products exist in each supported category

### Requirement: Inventory uses an explicit admin owner
Inventory seeding MUST require an existing admin email and MUST NOT create default credentials or assign inventory to a customer.

#### Scenario: Valid admin owner
- **WHEN** inventory seeding receives an existing admin email
- **THEN** the seeded inventory belongs to that admin

#### Scenario: Invalid owner
- **WHEN** the email is missing or belongs to a non-admin
- **THEN** the operation fails without partial inventory changes

### Requirement: Every seeded product receives sellable inventory
With a valid owner, the seed SHALL create one deterministic purchase option and one active USD listing with quantity 10 for every seeded product.

#### Scenario: Seeded products are available
- **WHEN** inventory seeding completes
- **THEN** all 15 seeded products have active positive-quantity inventory usable by cart flows

### Requirement: Repeated seeding is idempotent
The seed SHALL reconcile its managed records without duplicating them or modifying unrelated administrator-created data.

#### Scenario: Seed runs twice
- **WHEN** catalog and inventory seeding run twice for the same owner
- **THEN** exactly one managed product, purchase option, and listing exist per configured identity

#### Scenario: Unrelated data exists
- **WHEN** unrelated products, variants, or listings exist
- **THEN** rerunning the seed leaves them intact
