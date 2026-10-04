## Why

The project has moved from a seller marketplace feel toward a store-owned brand site, but product management still exposes marketplace wording and only a partial set of customer-facing product fields. Admins need one complete editor that controls the product details, variants, inventory, pricing, and public product-page content customers see.

## What Changes

- Add admin-managed storefront product content: feature bullets, product details/specifications, and optional image gallery data suitable for richer product pages.
- Rename customer-facing and admin UI concepts from marketplace language like "lowest ask" and "listing" toward store language such as price, stock, inventory, and availability while preserving existing backend relationships where practical.
- Extend admin product management so admins can edit all existing product fields plus the new storefront content from one product editor.
- Let authorized admins update inventory price, quantity, variant assignment, status, and stock availability without requiring delete/recreate inventory records.
- Update public product detail responses and UI to display admin-managed content, variant/size options, selected stock availability, product stats, and related products using store-oriented labels.
- Preserve existing archive/restore behavior, cart/listing references, guest cart behavior, watchlist behavior, and admin-only enforcement.

## Capabilities

### New Capabilities

- `admin-product-editor`: Defines a complete admin-controlled product editor, store inventory editing, and public product detail behavior driven by admin-managed product data.

### Modified Capabilities

- None.

## Impact

- Backend: product schemas, admin product/listing schemas, catalog product detail serialization, admin routes/services, and API tests.
- Database: product storefront-content fields and optional image gallery representation; deterministic Alembic migration and seed updates if new persisted fields are added.
- Frontend: admin product management UI, product creation flow, product detail page, TypeScript API types, store-language labels, and route smoke checks.
- Verification: backend tests for product content/inventory edits and product detail responses; frontend build/lint checks; smoke checks for admin edit, public product detail, carting selected inventory, and archived product exclusion.
