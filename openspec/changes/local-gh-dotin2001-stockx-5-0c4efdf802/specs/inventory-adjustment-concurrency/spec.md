## Purpose

Ensure inventory reductions remain correct under overlapping PostgreSQL transactions and are proven with deterministic, isolated concurrency tests.

## ADDED Requirements

### Requirement: Inventory adjustments are atomic under concurrency
The system SHALL apply each inventory quantity adjustment atomically against the latest committed quantity so concurrent reductions cannot create a negative quantity or silently lose a successful update.

#### Scenario: Concurrent valid reductions are both retained
- **WHEN** two independent transactions concurrently reduce a listing whose quantity is sufficient for both reductions
- **THEN** both requests succeed and the final quantity reflects both reductions exactly once

#### Scenario: Concurrent reductions exceed availability
- **WHEN** two independent transactions concurrently reduce inventory and satisfying both would take the quantity below zero
- **THEN** only reductions supported by available inventory succeed, rejected requests receive the existing below-zero conflict, and the final quantity is non-negative

### Requirement: Inventory concurrency verification is deterministic and isolated
PostgreSQL inventory concurrency tests SHALL use independent database connections and synchronization barriers to force overlapping operations, use only a validated `TEST_POSTGRES_DATABASE_URL`, and remove only records created by the tests.

#### Scenario: Barrier-coordinated inventory race
- **WHEN** the test suite exercises concurrent reductions
- **THEN** both independent transactions reach a synchronization point before proceeding and the test verifies the committed final quantity and response outcomes

#### Scenario: Test cleanup preserves unrelated records
- **WHEN** a PostgreSQL concurrency test completes or fails after creating fixtures
- **THEN** teardown deletes only fixture records identified as belonging to that test and does not reset or destroy the database
