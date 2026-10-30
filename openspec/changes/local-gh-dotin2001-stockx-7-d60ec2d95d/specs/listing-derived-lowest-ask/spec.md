## Purpose

Defines the database-enforced contract that keeps each product's displayed lowest ask consistent with its qualifying marketplace listings across all write paths and concurrent transactions.

## ADDED Requirements

### Requirement: Qualifying listings determine the lowest ask
The system SHALL set `products.lowest_ask_cents` to the minimum `price_cents` among listings for that product whose status is `active`, available quantity is greater than zero, and currency is `USD`; it SHALL set the value to `NULL` when no listing qualifies.

#### Scenario: Lowest qualifying USD listing is selected
- **WHEN** a product has multiple active USD listings with positive available quantity
- **THEN** its lowest ask equals the least of their prices

#### Scenario: Non-qualifying listings are ignored
- **WHEN** a product has listings that are non-USD, inactive, or depleted
- **THEN** those listings do not contribute to its lowest ask and no currency conversion is performed

#### Scenario: No listing qualifies
- **WHEN** a product has no active, positively stocked USD listing
- **THEN** its lowest ask is `NULL`

### Requirement: Listing mutations update affected products transactionally
The system MUST recalculate the derived lowest ask in the same transaction as any listing insert, update, or authorized delete that can affect the result, including creation, repricing, cancellation, sale, reactivation, depletion, replenishment, reservation, inventory release, currency changes, administrative changes, and movement between products.

#### Scenario: Qualifying listing changes
- **WHEN** a listing's price, status, quantity, currency, or product association changes
- **THEN** every affected product has the correct derived lowest ask before the transaction commits

#### Scenario: Reservation depletes the lowest listing
- **WHEN** an order reservation reduces the current lowest qualifying listing to zero available quantity
- **THEN** the product's lowest ask advances to the next qualifying USD listing or becomes `NULL` in the reservation transaction

#### Scenario: Inventory release restores a listing
- **WHEN** an order inventory release or replenishment makes an active USD listing positively stocked
- **THEN** the product's lowest ask includes that listing in the release or replenishment transaction

#### Scenario: Authorized listing deletion
- **WHEN** an authorized workflow deletes a listing
- **THEN** the affected product's lowest ask is recalculated transactionally and unrelated business records are preserved

#### Scenario: Listing moves between products
- **WHEN** a listing's product association changes
- **THEN** the old and new products are both recalculated in the same transaction

### Requirement: Direct and concurrent writes preserve the invariant
The database MUST enforce lowest-ask maintenance for direct SQL writes and MUST serialize recalculation per affected product so concurrent listing mutations cannot commit a stale derived value.

#### Scenario: Direct database mutation
- **WHEN** a client with database write authority inserts, updates, or deletes a listing without using the application service layer
- **THEN** the database still derives the correct lowest ask before commit

#### Scenario: Concurrent qualification changes
- **WHEN** independent transactions concurrently change listing price, status, quantity, currency, product association, or existence for the same product
- **THEN** after both transactions complete, the committed lowest ask equals the minimum qualifying committed listing price or `NULL`

#### Scenario: Concurrent changes affect different products
- **WHEN** independent transactions mutate listings for different products
- **THEN** lowest-ask serialization does not require a single global lock

### Requirement: Product clients cannot override the derived value
Product creation and update interfaces MUST NOT accept a client-supplied lowest ask as authoritative, and the migration MUST backfill every existing product from qualifying listings.

#### Scenario: Product create or update supplies lowest ask
- **WHEN** a client includes a lowest-ask value in a product create or update request
- **THEN** the value cannot override the database-derived value

#### Scenario: Existing products are migrated
- **WHEN** the migration is applied to a database containing products and listings
- **THEN** every product is backfilled to the qualifying minimum USD listing price or `NULL`

### Requirement: Lowest-ask migration is data preserving and reversible
Migration upgrade, downgrade, and re-upgrade MUST preserve products, variants, listings, orders, and inventory records; downgrade SHALL remove only the database objects introduced for lowest-ask maintenance while retaining business data.

#### Scenario: Migration lifecycle completes
- **WHEN** the migration is upgraded, downgraded, and upgraded again against PostgreSQL
- **THEN** each transition succeeds, business records remain present, and the invariant is active after each upgrade

