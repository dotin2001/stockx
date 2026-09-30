## Why

Category and search pages currently expose API-backed products, but shoppers cannot narrow or reorder results beyond changing the search text. Adding server-backed filters, sorting, and inventory-aware availability will make browsing feel much closer to a real marketplace while reusing the existing catalog, variant, and listing foundations.

## What Changes

- Add public catalog query parameters for brand, size, price range, availability, sorting, pagination, and optional search text.
- Make category and search results use the same server-side discovery behavior so filters, counts, and sorting stay consistent.
- Add filter metadata/facets for available brands, sizes, price bounds, and result totals scoped to the current query/category.
- Update the category and search UI with accessible filter controls, sort controls, active filter chips, reset behavior, loading/error/empty states, and URL-backed state.
- Treat sellable availability and price range filtering as derived from active listings with available quantity, while continuing to exclude archived products.
- Preserve existing product detail, cart, watchlist, auth, and admin management behavior.

## Capabilities

### New Capabilities

- `public-product-discovery`: Defines public category/search filtering, sorting, price range, brand, size, available-only behavior, filter metadata, URL-backed frontend controls, and result states.

### Modified Capabilities

- None.

## Impact

- Backend: `apps/api/app/api/v1/catalog.py`, `apps/api/app/services/catalog.py`, product response schemas, catalog tests, and smoke coverage.
- Database/querying: joins across `products`, `categories`, `product_variants`, and `listings`; likely query helper refactoring and indexes for filtered catalog access.
- Frontend: `apps/web/lib/api.ts`, shared catalog/search types, category/search pages, product grid/card display, and reusable filter/sort controls.
- Verification: backend tests for query combinations and facets; frontend lint/build plus route smoke checks for category and search filter URLs.
