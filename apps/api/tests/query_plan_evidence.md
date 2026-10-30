# PostgreSQL catalog query-plan evidence

This artifact defines the repeatable plan study executed by
`test_postgres_query_plans.py`. The test requires the explicitly configured
`TEST_POSTGRES_DATABASE_URL`, confirms that the connected database name matches
that URL, creates only rows carrying a unique `plan-fixture-*` marker, and
removes only those tracked rows in dependency order.

The suite records `EXPLAIN (FORMAT JSON)` for these representative shapes:

| Shape | Stable representative parameters |
| --- | --- |
| Text search | `%plan-fixture%` across name, slug, brand, and description |
| Category | fixture category UUID |
| Brand | `Plan Brand 3` |
| Size | `10` through a correlated product-variant lookup |
| Price and availability | persisted lowest ask from 10,000 through 20,000 cents |
| Lowest-listing aggregation | active, positive-quantity USD listings grouped by product |
| Price sorting | lowest ask ascending with name and UUID tie-breakers |
| Admin listings | active status ordered by creation time descending and UUID |

Exact costs, timings, and plan-node names are intentionally not asserted. The
suite compares the complete ordered query results before and after candidate
indexes and verifies that each captured plan is valid JSON.

## Candidate decisions

Accepted:

- `ix_listings_qualifying_product_price (product_id, price_cents, id) WHERE status = 'active' AND available_quantity > 0 AND currency = 'USD'`: matches lowest-ask recomputation and storefront listing lookup while excluding non-qualifying inventory.
- `ix_product_variants_product_size (product_id, size)`: matches the correlated product-and-size predicate; neither existing single-column index provides this ordered pair.
- `ix_listings_status_created_at_id (status, created_at DESC, id)`: matches the filtered admin listing order with a deterministic UUID tie-breaker.

Rejected:

- Trigram GIN search: the current query is an `OR` over four independently
  stored columns, so a combined expression index would not match it without a
  query/schema rewrite. Four GIN indexes and ownership of `pg_trgm` are not
  justified by this workload study. No extension or trigram index is added.
- Existing single-column listing status, quantity, price, product, variant size,
  and product brand indexes are retained. None is recreated under another name.
