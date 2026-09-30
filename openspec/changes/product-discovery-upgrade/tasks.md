## 1. Backend Discovery Contract

- [x] 1.1 Add backend discovery request/response schema types for filters, sort values, selected filter metadata, facet options, and price bounds; verify Pydantic validation accepts supported parameters and rejects invalid sort or negative price values in backend tests.
- [x] 1.2 Update public catalog route handlers to accept repeated `brand` and `size`, `min_price`, `max_price`, `available_only`, `sort`, `limit`, and `offset` parameters on product, category product, and search endpoints; verify existing unfiltered endpoint tests still pass.
- [x] 1.3 Preserve the existing `ProductPage` fields while adding discovery metadata to responses; verify existing clients can still read `items`, `total`, `limit`, and `offset` in API tests.

## 2. Backend Query Implementation

- [x] 2.1 Refactor catalog product listing, category listing, and search into one shared discovery query path; verify product list, category list, and search tests all exercise the shared behavior.
- [x] 2.2 Implement brand, size, available-only, and inclusive price range filtering using non-archived products and active available listings as required; verify API tests cover each filter independently.
- [x] 2.3 Implement stable `newest`, `price_asc`, `price_desc`, `popular`, and `name_asc` sorting; verify API tests assert ordered response slugs for each sort.
- [x] 2.4 Implement discovery metadata for selected filters, available brand options, available size options, price bounds, total, limit, and offset; verify API tests cover metadata with matching results and zero-result filters.
- [x] 2.5 Evaluate existing product, variant, and listing indexes for the discovery query path and add a deterministic Alembic migration only if missing indexes are needed; verify migration upgrade and downgrade or document why no migration was necessary.

## 3. Frontend API And State

- [x] 3.1 Update frontend TypeScript types and API helpers to represent discovery query parameters and response metadata; verify `npm run build` or the available type check catches no type errors.
- [x] 3.2 Add shared URL parsing and serialization helpers for category/search discovery parameters; verify unit or source-level tests cover repeated brand/size values, price values, available-only, sort, and clearing filters.
- [x] 3.3 Update category and search pages to read discovery state from URL search params and pass it to the API; verify manual route smoke checks load filtered URLs without losing category or query context.

## 4. Frontend Discovery UI

- [x] 4.1 Replace static category side filter links with reusable discovery controls driven by API metadata; verify category pages show brand, size, price, available-only, and sort controls when metadata is present.
- [x] 4.2 Add active filter chips with individual removal and clear-all behavior; verify changing and clearing filters updates the URL and reloads results for the same category or search text.
- [x] 4.3 Add responsive loading, error, and empty states for filtered results; verify no-match filters display an empty state that mentions active filters and offers a reset path.
- [x] 4.4 Verify discovery controls are keyboard usable with labels, visible focus states, and native form controls across desktop and mobile viewport checks.

## 5. Verification

- [x] 5.1 Add or update backend tests for combined filters, category/search parity, archived product exclusion, and active listing availability semantics; verify `pytest` passes in `apps/api`.
- [ ] 5.2 Update API smoke coverage to exercise at least one filtered/sorted discovery request and metadata response; verify the smoke workflow passes against a running local API when prerequisites are available.
- [x] 5.3 Run frontend lint/type/build checks for `apps/web`; verify category and search pages compile with updated discovery controls and types.
- [ ] 5.4 Perform marketplace smoke checks for home, category filter URL, search filter URL, product detail, cart availability, login, account, and sell routes; verify the discovery upgrade did not regress protected workflows.
