## Purpose

Defines an operator-controlled retention cleanup that removes only explicitly disposable authentication records after a fixed safety window while preserving permanent marketplace and payment data.

## ADDED Requirements

### Requirement: Refresh-token eligibility uses explicit retention timestamps
The cleanup command SHALL consider a refresh-token record eligible only when its `expires_at` is at or before the run cutoff of current time minus 30 days, or its non-null `revoked_at` is at or before that cutoff. It SHALL preserve every refresh token that satisfies neither condition, including all active, unexpired tokens.

#### Scenario: Timestamp exactly on the boundary
- **WHEN** a refresh token has `expires_at` or non-null `revoked_at` exactly 30 days before the run time
- **THEN** the command treats the record as eligible

#### Scenario: Timestamp newer than the boundary
- **WHEN** a refresh token has not expired at least 30 days ago and was not revoked at least 30 days ago
- **THEN** the command preserves the record

#### Scenario: Active token is protected
- **WHEN** a refresh token is unrevoked and its expiration is in the future
- **THEN** the command does not report or delete it

### Requirement: Replacement relationships remain safe
The cleanup command SHALL allow an eligible predecessor token to be removed without removing its replacement token, and SHALL preserve replacement relationships between records that remain. Any reference to a removed token MUST be resolved consistently with the database foreign-key policy.

#### Scenario: Eligible predecessor points to protected replacement
- **WHEN** an eligible expired or revoked token references a replacement that is not eligible
- **THEN** the command removes only the eligible predecessor and preserves the replacement

#### Scenario: Remaining chain is untouched
- **WHEN** related predecessor and replacement records are both ineligible
- **THEN** the command preserves both records and their relationship

### Requirement: Dry-run is non-mutating and observable
The command SHALL provide an explicit dry-run mode that applies the same eligibility cutoff and batch bound as deletion mode, reports the number of records that would be deleted, and commits no data changes.

#### Scenario: Dry-run finds eligible records
- **WHEN** an operator runs dry-run mode with eligible refresh tokens present
- **THEN** the command reports the bounded eligible count and all database records remain unchanged

#### Scenario: Dry-run finds no eligible records
- **WHEN** an operator runs dry-run mode with no eligible refresh tokens
- **THEN** the command reports zero and changes no data

### Requirement: Cleanup executions are bounded and idempotent
The command SHALL require a positive batch-size bound, process no more than that number of eligible records in one execution, and report the number actually deleted. Eligible rows SHALL be selected in a deterministic order so repeated executions safely make progress, and a subsequent execution after all eligible rows are removed SHALL succeed and report zero deletions.

#### Scenario: Eligible population exceeds the batch size
- **WHEN** more eligible records exist than the configured batch size
- **THEN** one execution deletes no more than the batch size and reports the exact deleted count

#### Scenario: Repeated execution drains eligible records
- **WHEN** the command is run repeatedly with the same positive batch size
- **THEN** each execution removes only the next bounded eligible set until a run succeeds with zero deletions

#### Scenario: Invalid batch size
- **WHEN** an operator supplies a non-positive batch size
- **THEN** the command rejects the invocation without changing data

### Requirement: Cleanup is restricted to explicitly disposable records
This cleanup capability SHALL delete only refresh-token records covered by the explicit timestamp policy. It MUST NOT delete or reuse `stripe_webhook_events`, infer webhook retry exhaustion from `processing_status` or `processed_at`, introduce webhook retries, or delete orders, payment attempts, listings, users, products, variants, successful webhook records, or audit records. Any future record type MUST be explicitly designated disposable and have an explicit expiration timestamp before retention cleanup can include it.

#### Scenario: Permanent and undesignated records are present
- **WHEN** eligible refresh tokens coexist with permanent business, payment, webhook, audit, or otherwise undesignated records of any age
- **THEN** the command deletes only eligible refresh tokens and leaves all other record types unchanged

### Requirement: Retention behavior is verified against PostgreSQL
The project SHALL provide PostgreSQL-executed tests for exact retention boundaries, replacement relationships, dry-run behavior, actual deletion, bounded batching, repeated-run idempotency, and protected-record retention. PostgreSQL-specific tests SHALL remain runnable separately from the normal backend suite without requiring a hosted CI workflow.

#### Scenario: Operator runs retention verification
- **WHEN** the documented PostgreSQL test command is run against an explicitly configured PostgreSQL test database
- **THEN** it exercises the retention cleanup scenarios against PostgreSQL

### Requirement: Operators receive safe execution guidance
Backend documentation SHALL provide a recommended daily dry-run and deletion invocation, explain that each execution processes at most one configured batch, and list commands for the normal backend suite and the PostgreSQL-specific retention tests. The guidance SHALL leave scheduling and hosted CI integration to operators.

#### Scenario: Operator follows daily guidance
- **WHEN** an operator consults the backend documentation
- **THEN** they can preview and execute one bounded cleanup batch and run both documented test groups without a repository-managed scheduler
