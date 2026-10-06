## 1. Catalog Seed Data

- [x] 1.1 Expand seed definitions to five products per supported category and verify counts, slugs, prices, and images in tests.
- [x] 1.2 Add deterministic purchase-option metadata and verify all 15 seed SKUs are unique.

## 2. Inventory Seed Behavior

- [x] 2.1 Add an optional inventory-owner argument while preserving product-only seeding and verify CLI parsing.
- [x] 2.2 Validate the owner exists and is an admin before mutation and verify missing/non-admin failures.
- [x] 2.3 Reconcile one active USD listing with quantity 10 per seeded product and verify ownership, linkage, price, and quantity.
- [x] 2.4 Verify running inventory seeding twice creates no duplicates and preserves unrelated data.

## 3. Documentation And Verification

- [x] 3.1 Document product-only and inventory seed commands plus quantity reset semantics.
- [x] 3.2 Run the backend test suite and verify catalog, inventory, and cart behavior.
- [x] 3.3 Run catalog and inventory seeding twice against local PostgreSQL and verify 15 products, variants, and listings.
- [x] 3.4 Run strict OpenSpec validation.
