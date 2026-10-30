## Context

See `proposal.md` for motivation. Products already store `lowest_ask_cents`, but product administration accepts it from clients while catalog and detail services independently scan active, positively stocked listings. Those scans currently omit the USD condition. Listing quantity changes occur through ordinary ORM mutation, bulk SQL updates, checkout reservation/release paths, administrative endpoints, and test/direct SQL; therefore application callbacks alone cannot cover the invariant.

The database has individual indexes on listing status, quantity, price, product, and variant fields, plus individual product brand and variant size indexes. Catalog discovery builds correlated availability/price predicates and a grouped minimum-price subquery; administration orders listings by creation time and may filter status. PostgreSQL integration infrastructure already provides a guarded dedicated test database and independent-session concurrency patterns.

## Goals / Non-Goals

**Goals:**

- Make the persisted lowest ask a transactionally correct cache of qualifying listing data for every write path.
- Bound concurrency coordination to affected products and cover product reassignment without deadlocks.
- Align all public/admin catalog price and availability semantics with active, positive-quantity USD listings.
- Select indexes from repeatable PostgreSQL evidence and verify both definitions and unchanged query results.
- Keep migration and fixture cleanup narrowly scoped and data preserving.

**Non-Goals:**

- Currency conversion, exchange-rate storage, or support for a non-USD displayed lowest ask.
- Replacing listing/order lifecycle states or changing authorization for listing deletion.
- Deleting or denormalizing business records to improve performance.
- Promising exact planner costs, timing thresholds, or a fixed plan-node shape across environments.

## Decisions

### 1. Use a PostgreSQL row trigger backed by a per-product recomputation function

Create a migration-owned function that locks the affected `products` row, computes `MIN(listings.price_cents)` using `status = 'active'`, `available_quantity > 0`, and `currency = 'USD'`, then updates the product. An `AFTER INSERT OR UPDATE OR DELETE` trigger invokes it so the triggering row's new state is visible and direct writes are covered. For an update that changes `product_id`, recalculate both old and new product IDs.

Row locking makes concurrent transactions for the same product serialize before reading the qualifying set, while different products retain independent locks. When two products are affected, acquire/recalculate them in stable UUID order to avoid opposite-direction reassignment deadlocks. An alternative application-only service helper was rejected because bulk checkout SQL and direct database writes can bypass it. A statement trigger with transition tables was considered, but the current workload and required cross-version migration simplicity favor a row trigger; correctness tests will cover multi-row statements.

### 2. Treat the persisted product field as the canonical query projection

Remove `lowest_ask_cents` from product create/update input schemas and explicitly exclude it in service persistence as defense in depth. Update catalog aggregation, price filters, price bounds, availability predicates, detail selection, related-product pricing, and administrative serialization so qualifying listing logic includes USD; where only a lowest price/sort is needed, use the maintained product projection and retain deterministic tie-breakers. Listing detail/purchase choices must also exclude non-USD listings from USD storefront availability.

An alternative is to keep recomputing minimum prices in every read query. That undermines the purpose of the derived field, leaves semantic drift likely, and makes price ordering more expensive. The listing table remains authoritative; the product field is only a database-maintained projection.

### 3. Backfill and install enforcement in one migration transaction

The upgrade creates the function and trigger, then recomputes all products with the exact qualifying predicate. The migration also creates only indexes justified by the plan study. PostgreSQL transactional DDL ensures a failed backfill or object creation does not leave partial enforcement. Downgrade drops introduced triggers, functions, extensions if newly owned and safe to remove, and indexes, but retains the column and all business rows because the column predates this issue.

The alternative of backfilling before trigger installation leaves a write race during deployment. Installing enforcement before the set-based backfill closes that gap; the migration transaction prevents external visibility until both are complete.

### 4. Evaluate composite and partial indexes against real query shapes

Build representative fixtures with enough distribution for the planner to make meaningful choices, run `ANALYZE`, and capture `EXPLAIN (FORMAT JSON)` plus index definitions for baseline and candidate states. Evaluate:

- a trigram GIN index strategy for the multi-column case-insensitive text predicate, including whether a combined searchable expression is needed;
- a partial listing index keyed for product and price where status is active, quantity positive, and currency USD;
- a product/size variant index for correlated size filters;
- a status/creation-time listing index matching admin filtering and ordering.

Existing single-column indexes are inventoried first. Candidate acceptance is based on representative access-path evidence and workload fit, not exact costs or mandatory node names. Result rows and defined ordering are compared independently of `EXPLAIN`. Evidence is stored as a stable test/report artifact in the repository's test suite rather than embedding environment-specific timing assertions.

### 5. Use guarded PostgreSQL integration tests for concurrency and cleanup

Extend the existing PostgreSQL test support so plan and concurrency fixtures require the explicit dedicated test database guard. Concurrency tests use independent sessions, deterministic barriers after locks/mutations are staged, bounded timeouts, and final committed-state assertions. Cases cover concurrent repricing, qualification changes through status/quantity, delete-versus-update, reservation/depletion and release/replenishment, plus different-product independence.

Cleanup tracks fixture identifiers and deletes only those rows in dependency order. It never truncates shared tables or deletes pre-existing products, variants, listings, orders, or inventory. Migration tests snapshot representative business records across upgrade, downgrade, and re-upgrade.

## Risks / Trade-offs

- [A hot product serializes listing writes on its product row] → Keep locking per product, make recomputation use a supporting partial index, and measure representative write plans.
- [Trigger recursion or unnecessary product updates amplify writes] → Limit trigger firing/recalculation to inserts/deletes and updates of product, price, currency, status, or quantity; update the product only when the derived value is distinct.
- [Multi-row statements invoke repeated recalculations] → Preserve correctness first and test bulk paths; if evidence shows material overhead, a later change can adopt transition-table statement triggers without changing the contract.
- [Trigram support may require `pg_trgm` extension ownership decisions] → Detect existing extension state, create it only when the accepted index requires it, and never drop a pre-existing/shared extension on downgrade.
- [Small fixtures cause PostgreSQL to prefer sequential scans] → Use representative cardinality and statistics, record evidence semantically, and avoid assertions tied to exact cost or node choices.
- [Existing tests and seed data supply manual lowest asks] → Update fixtures to create qualifying listings or expect `NULL`; validate public output against the derived invariant rather than seeded product values.

## Migration Plan

1. Add the migration-owned recalculation function and trigger with deterministic per-product lock ordering.
2. Backfill all products in the same migration transaction using the qualifying USD predicate.
3. Add only indexes accepted by representative before/after plan evidence and inventory checks.
4. Deploy application changes that reject client ownership of the field and align all read predicates with USD qualification.
5. Run PostgreSQL invariant, independent-session concurrency, query correctness/plan, and upgrade/downgrade/re-upgrade verification in the dedicated test database.
6. On rollback, drop only objects introduced by this migration, leave the existing product column and every business row intact, and verify the prior application schema remains usable.
