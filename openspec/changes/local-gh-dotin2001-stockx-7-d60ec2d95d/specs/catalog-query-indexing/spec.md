## Purpose

Defines an evidence-based, result-preserving process for selecting and verifying PostgreSQL indexes used by catalog discovery, lowest-listing calculation, and administrative listing workloads.

## ADDED Requirements

### Requirement: Representative catalog workloads have recorded plan evidence
The system MUST record representative PostgreSQL `EXPLAIN` evidence for catalog text search; category, brand, size, price, and availability filters; lowest-listing aggregation; price sorting; and administrative listing queries.

#### Scenario: Representative plans are captured
- **WHEN** query-plan verification runs against the configured representative PostgreSQL dataset
- **THEN** evidence covers each required catalog and administrative query shape with its parameters and relevant index definitions

#### Scenario: Plan verification is stable across PostgreSQL choices
- **WHEN** PostgreSQL selects a different valid plan because of statistics or environment differences
- **THEN** verification does not fail solely because exact costs or specific planner node names differ

### Requirement: Only justified non-duplicative indexes are added
The system SHALL evaluate trigram text search, qualifying active/available/USD listing lookup, product-and-size variant lookup, and administrative status-and-creation-time ordering, and SHALL add an index only when representative evidence justifies it and an equivalent index does not already exist.

#### Scenario: Candidate improves a representative workload
- **WHEN** representative evidence shows a candidate index supports a required query shape without duplicating an existing index
- **THEN** the migration adds that index and records the supporting evidence

#### Scenario: Candidate is redundant or unsupported
- **WHEN** a candidate duplicates an existing index or representative evidence does not justify it
- **THEN** the migration omits the candidate and records the reason

### Requirement: Index changes preserve query behavior
Adding or removing indexes MUST NOT change the rows, filtering semantics, price calculations, deterministic ordering, or pagination tie-breakers returned by catalog and administrative queries.

#### Scenario: Indexed and baseline query results are compared
- **WHEN** index verification executes the representative queries before and after the new indexes are available
- **THEN** the result sets and defined ordering are equivalent

#### Scenario: USD qualification is applied to catalog prices
- **WHEN** catalog availability, price filtering, aggregation, or sorting depends on a qualifying listing
- **THEN** only active, positively stocked USD listings participate consistently with the lowest-ask invariant

### Requirement: Query-plan fixtures are isolated and removable
Query-plan verification MUST create and remove fixtures only in the explicitly configured dedicated test database, and cleanup MUST NOT delete marketplace business records outside those fixtures.

#### Scenario: Dedicated test database is not configured
- **WHEN** query-plan verification cannot prove it is connected to the explicitly configured dedicated test database
- **THEN** it refuses to create or remove query-plan fixtures

#### Scenario: Fixture cleanup runs
- **WHEN** query-plan verification finishes or fails after fixture creation
- **THEN** it removes only the fixtures it created in the dedicated test database

### Requirement: Index migration rollback is scoped
Migration downgrade MUST remove only indexes and supporting database objects introduced by this change and MUST preserve all product, variant, listing, order, and inventory records.

#### Scenario: Index migration is downgraded
- **WHEN** the migration is rolled back
- **THEN** only the introduced indexes and supporting objects are removed and business records remain unchanged

