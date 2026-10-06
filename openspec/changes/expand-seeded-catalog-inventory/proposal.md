## Why

The development catalog has only two seeded products per public category and no purchasable seeded inventory. Expanding it gives catalog, cart, and checkout development a representative sellable dataset.

## What Changes

- Seed exactly five products in each of Sneakers, Streetwear, and Collectibles using repository storefront data.
- Give every seeded product one deterministic purchase option and one active USD inventory record with quantity 10.
- Require an explicitly selected existing admin as inventory owner; create no default credential.
- Keep repeated catalog and inventory seeding idempotent and preserve unrelated admin-created data.
- Add tests and documentation for the expanded seed workflow.

## Capabilities

### New Capabilities

- `seeded-catalog-inventory`: Representative development products, purchase options, admin-owned inventory, and repeatable seed behavior.

### Modified Capabilities

None.

## Impact

- `apps/api/app/db/seed.py`, backend seed/database tests, and local database documentation.
- No schema migration or public API contract change.
