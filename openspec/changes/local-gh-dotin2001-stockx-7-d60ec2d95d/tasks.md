## 1. Establish PostgreSQL Evidence and Migration Design

- [x] 1.1 Add guarded representative query-plan fixtures for catalog text search, category/brand/size/price/availability filters, lowest-listing aggregation, price sorting, and admin listing queries; verify the fixture setup refuses unproven databases and cleanup removes only tracked fixture rows.
- [x] 1.2 Inventory existing PostgreSQL indexes and capture baseline `EXPLAIN (FORMAT JSON)` evidence plus baseline query results for every representative query shape; verify the evidence records parameters and index definitions without assertions on exact costs or planner nodes.
- [x] 1.3 Evaluate trigram search, partial active/available/USD listing, product-and-size variant, and admin status/creation-time candidates against representative data; document accepted and rejected candidates and verify accepted candidates are justified and non-duplicative.

## 2. Enforce the Listing-Derived Lowest Ask

- [x] 2.1 Add an Alembic migration with migration-owned PostgreSQL functions/triggers that serialize by affected product, recalculate the qualifying USD minimum for insert/update/delete mutations, handle product reassignment in stable lock order, and avoid unchanged writes; verify direct SQL mutation tests cover each trigger operation and multi-row statements.
- [x] 2.2 Backfill every product transactionally with the active, positive-quantity USD minimum or `NULL`; verify migration tests cover products with multiple prices, only non-USD/inactive/depleted listings, and no listings.
- [x] 2.3 Add only the indexes accepted by the evidence review, including safe ownership handling for any required extension; verify catalog/admin results match baseline and database inspection finds the exact intended definitions with no equivalent duplicate indexes.
- [x] 2.4 Implement a scoped downgrade that removes only this migration's trigger, functions, indexes, and exclusively owned supporting objects while retaining the pre-existing lowest-ask column and business rows; verify PostgreSQL upgrade, downgrade, and re-upgrade all succeed with representative products, variants, listings, orders, and inventory preserved.

## 3. Align Application Write and Read Semantics

- [x] 3.1 Remove `lowest_ask_cents` from product create/update inputs and defensively exclude it from product persistence; verify API tests show client-supplied values cannot set or overwrite the derived field while response schemas still expose it.
- [x] 3.2 Update catalog discovery, availability, price filters/bounds/sorts, product detail, purchase options, related products, and admin serialization to consistently qualify only active, positively stocked USD listings and use the maintained projection where designed; verify catalog tests cover mixed currencies and preserve deterministic ordering and pagination.
- [x] 3.3 Audit listing creation, repricing, cancellation, sale/reactivation, quantity adjustment, checkout reservation, inventory release, administrative mutation, and authorized deletion paths for transaction boundaries compatible with database enforcement; verify integration tests assert the derived value inside the mutation transaction and after commit.
- [x] 3.4 Update seed data and existing tests that manually assign lowest asks so expectations come from qualifying listings or `NULL`; verify backend tests no longer rely on client-owned or independently seeded lowest-ask values.

## 4. Prove Concurrency and Performance Behavior

- [x] 4.1 Add independent-session tests with deterministic barriers and bounded timeouts for concurrent repricing plus status and quantity qualification changes on one product; verify every completion order ends with the exact minimum qualifying committed price or `NULL`.
- [x] 4.2 Add independent-session coverage for deletion versus update, reservation/depletion versus release/replenishment, product reassignment, and mutations on different products; verify affected products converge correctly without global serialization or deadlock.
- [x] 4.3 Run the representative plan suite after migration and record final evidence for every required query shape; verify accepted indexes are available to relevant workloads, rejected candidates remain absent, and query rows/order match the baseline.
- [x] 4.4 Run the complete backend test suite and PostgreSQL migration lifecycle checks in the configured dedicated test database; verify all tests pass and final cleanup leaves no query-plan fixtures while preserving pre-existing business records.
