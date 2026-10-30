## Why

`products.lowest_ask_cents` is currently writable independently of listings, while catalog queries repeatedly derive similar availability and price data without an evidence-based indexing contract. Making qualifying listings authoritative prevents stale storefront prices across API, checkout, administrative, and direct-database mutations, and representative PostgreSQL plan evidence can guide targeted indexes without changing query results.

## What Changes

- Maintain each product's lowest ask as the minimum USD price among active listings with positive available quantity, or `NULL` when none qualify.
- Enforce the derived value inside PostgreSQL with per-product serialization so application paths and direct database writes preserve the same invariant under concurrency.
- Recalculate on every listing mutation that can affect qualification or price, including reservations, releases, sales, administrative changes, replenishment, deletion, and changes that move a listing between products.
- Backfill existing products and stop product create/update clients from supplying or overriding the derived field.
- Add deterministic PostgreSQL concurrency and migration lifecycle coverage for the invariant.
- Capture representative `EXPLAIN` evidence for catalog discovery, listing aggregation, price ordering, variant filters, and administrative listing queries; add only non-duplicative indexes justified by that evidence.
- Keep performance work data-preserving: query results remain unchanged, query-plan fixtures are confined to the configured dedicated test database, and rollback removes only objects introduced by this change.

## Capabilities

### New Capabilities

- `listing-derived-lowest-ask`: Defines listing-authoritative lowest-ask maintenance, write-path protection, transactional recalculation, concurrency behavior, and safe migration/backfill semantics.
- `catalog-query-indexing`: Defines evidence-based PostgreSQL query-plan review and result-preserving index lifecycle requirements for catalog and administrative listing workloads.

### Modified Capabilities

None.

## Impact

- PostgreSQL migration objects, listing/product persistence rules, and the `products.lowest_ask_cents` backfill.
- Product administration schemas/services, catalog discovery and price ordering, listing administration, checkout reservation/release, sale completion, and any direct listing mutation path.
- PostgreSQL integration/concurrency tests, migration upgrade/downgrade/re-upgrade tests, and dedicated query-plan fixtures/evidence.
- Existing product and listing records are preserved; no currency conversion is introduced, and non-USD listings do not contribute to the lowest ask.
