## Context

The public catalog API currently has separate list, category, and search service functions that return `ProductPage` with `items`, `total`, `limit`, and `offset`. Products carry `brand`, `lowest_ask_cents`, `total_sold`, and archive state; sizes live on `product_variants`; sellable price and availability live on active `listings` with positive `available_quantity`.

The Next.js category and search pages currently request fixed-size result pages and render product grids without URL-backed filter state. Category side navigation links to search terms rather than applying real category filters.

## Goals / Non-Goals

**Goals:**

- Keep existing public catalog routes working while adding filter, sort, and metadata query support.
- Use one backend discovery query model for product list, category products, and search results.
- Make price and availability filters reflect active sellable listings instead of stale product display fields.
- Keep category and search page state shareable through URL query parameters.
- Add targeted tests around query combinations, metadata, and UI state parsing.

**Non-Goals:**

- Full-text search ranking beyond the existing simple search behavior.
- New product/catalog fields, new category taxonomy, or production image storage.
- Checkout, order creation, payment, or fulfillment behavior.
- Replacing admin product inventory management surfaces.

## Decisions

### Keep and extend existing public endpoints

Extend `GET /api/v1/products`, `GET /api/v1/categories/{slug}/products`, and `GET /api/v1/search` with optional query parameters instead of introducing a separate `/discovery` endpoint.

Rationale: Existing frontend and smoke flows already depend on these routes. Additive query parameters and additive response fields keep current clients compatible while making category/search behavior consistent.

Alternatives considered:

- Add a new `/api/v1/discovery` route. This would simplify endpoint naming but force duplicate route handling or frontend migration before value is visible.
- Collapse search into `/products?q=...`. This is cleaner long-term, but keeping `/search` avoids breaking the current public search contract.

### Use a shared backend query object

Create a catalog discovery filter object that represents `q`, `category_slug`, `brand`, `size`, `min_price`, `max_price`, `available_only`, `sort`, `limit`, and `offset`. Route handlers should validate request parameters and pass this object into one service path.

Rationale: The existing service has three separate query paths with duplicated ordering/count behavior. A shared object avoids divergent category and search semantics.

Parameter conventions:

- `brand` and `size` use repeated query parameters for multi-select values, for example `brand=Nike&brand=Jordan`.
- Prices are integer cents to match the database money representation.
- Sort values are explicit enum strings: `newest`, `price_asc`, `price_desc`, `popular`, and `name_asc`.

### Preserve `ProductPage` compatibility with additive metadata

Keep `items`, `total`, `limit`, and `offset` in the public product page response. Add a nested discovery metadata object containing selected filters, selected sort, available brand options, available size options, and price bounds.

Rationale: Existing frontend code can continue reading the original shape while upgraded pages consume metadata for filters. Additive response fields are less disruptive than replacing the response model.

### Derive sellable price from listings

Use active listings with `available_quantity > 0` as the source of truth for `available_only`, price range filtering, price sorting, and price bounds. Product `lowest_ask_cents` remains display fallback data but should not decide whether an item is sellable.

Rationale: Cart and product detail behavior already treat active positive-quantity listings as purchasable. Discovery should match that customer-facing truth.

Implementation approach:

- Use an aggregate subquery that computes lowest active available listing price per product.
- Use `EXISTS` predicates for availability, price range, and size filters to avoid duplicate product rows.
- Keep archived product exclusion in the base product criteria for both result items and metadata.

### Compute dynamic filter metadata with bounded queries

Facet metadata should be scoped to the current category/search context and archived-product exclusion. Counts should help users understand available choices without requiring frontend hardcoding.

Rationale: Existing category filter chips are curated static labels. Dynamic metadata makes discovery reflect actual catalog and inventory data, especially as admins add products, variants, and listings.

Practical rule:

- Brand and size option counts should be computed for the current context and non-facet filters where practical, so applying a price or availability filter can narrow options.
- Facet counts may ignore the facet's own currently selected values to keep alternative selections visible.

### URL state owns frontend discovery state

Category and search pages should parse filter/sort state from `searchParams`, request the API using those values, and update the URL when controls change. A small shared helper should serialize and parse discovery parameters for both pages.

Rationale: Shareable URLs are a core ecommerce expectation. Using URL state also keeps reloads, back/forward navigation, and copied search links predictable.

### Reuse current UI primitives, add a focused filter component

Build a reusable discovery controls component for category and search pages. It should use native form controls where possible: checkboxes for brand/size/available-only, number inputs for price range, a select for sort, and removable active-filter chips.

Rationale: This fits the existing Tailwind/Next.js app without introducing new UI dependencies, and native controls reduce accessibility risk.

## Risks / Trade-offs

- Query joins become heavier as listings and variants grow -> add focused query tests, inspect generated SQL, and add indexes for listing/product/variant filters if existing indexes are insufficient.
- Dynamic facet counts can be expensive -> keep metadata queries simple and bounded; defer advanced search indexing until catalog size requires it.
- Additive response fields can drift between backend and frontend types -> update Pydantic schemas and TypeScript types together, with build/type checks in verification.
- URL parameter parsing can produce invalid combinations -> backend validation remains authoritative and frontend parsing should normalize only supported values.
- Products without active listings may still appear unless `available_only` or price filters are active -> sort price modes place unsellable products after sellable products while preserving browsing breadth.

## Migration Plan

1. Add backend schemas and shared catalog discovery query/service behavior behind existing endpoints.
2. Add or adjust database indexes only if needed for the filtered listing/variant/product access patterns.
3. Update frontend API helpers/types and category/search pages to read/write URL-backed discovery parameters.
4. Replace static category filter links with dynamic controls driven by API metadata.
5. Add backend and frontend verification before treating the change as complete.

Rollback is straightforward because the change is additive at the route level: frontend pages can return to calling existing endpoint parameters, and any added index migration can be downgraded independently if needed.
