## Purpose

Define canonical, database-protected email and SKU identities so equivalent values cannot create duplicate records, including during concurrent requests.

## ADDED Requirements

### Requirement: Emails have one canonical stored identity
The system SHALL trim surrounding whitespace from an email, convert it to lowercase before storage and lookup, reject an empty normalized value, and require PostgreSQL rows to satisfy the same canonical form.

#### Scenario: Registration canonicalizes an email
- **WHEN** a client registers with an email containing uppercase letters or surrounding whitespace
- **THEN** the account is stored and subsequently resolved using the trimmed lowercase email

#### Scenario: Empty normalized email is rejected
- **WHEN** an email contains only whitespace
- **THEN** the system rejects the request without creating an account

### Requirement: Normalized email uniqueness is concurrency-safe
The system SHALL enforce global normalized email uniqueness in PostgreSQL and SHALL return HTTP 409 with the existing `email_exists` error code whenever registration conflicts with an existing or concurrently inserted equivalent email.

#### Scenario: Equivalent concurrent registrations
- **WHEN** two independently committed registration transactions submit emails that differ only by case or surrounding whitespace at the same time
- **THEN** exactly one user is created and the other request receives the `email_exists` conflict

### Requirement: SKUs have one canonical optional representation
The system SHALL trim surrounding whitespace from a submitted SKU and SHALL store an empty or whitespace-only SKU as `NULL`.

#### Scenario: Non-empty SKU is trimmed
- **WHEN** a variant is created or updated with a SKU containing surrounding whitespace
- **THEN** the stored SKU contains the same non-whitespace content without surrounding whitespace

#### Scenario: Blank SKU becomes absent
- **WHEN** a variant is created or updated with an empty or whitespace-only SKU
- **THEN** the stored SKU is `NULL`

### Requirement: Non-empty SKU identity is globally unique
The system SHALL enforce case-insensitive and surrounding-whitespace-insensitive uniqueness for every non-empty SKU across all product variants in PostgreSQL, while permitting multiple variants with `NULL` SKU values.

#### Scenario: Duplicate SKU creation is rejected
- **WHEN** variant creation submits a non-empty SKU equivalent to one owned by any existing variant
- **THEN** the system returns HTTP 409 with a stable duplicate-SKU error and does not create the variant

#### Scenario: Duplicate SKU update is rejected
- **WHEN** a variant update changes its SKU to a value equivalent to one owned by another variant
- **THEN** the system returns the same HTTP 409 duplicate-SKU error and preserves the existing variant state

#### Scenario: Equivalent concurrent SKU submissions
- **WHEN** two independent transactions concurrently submit non-empty SKUs that differ only by case or surrounding whitespace
- **THEN** exactly one submission succeeds and the other receives the duplicate-SKU conflict

### Requirement: Integrity migration fails safely on existing conflicts
Before enabling normalized email or SKU constraints, the migration SHALL detect existing identities that collide under the new comparison rules and stop with an actionable error without merging, renaming, or deleting users or variants.

#### Scenario: Existing email collision blocks upgrade
- **WHEN** two stored users have emails that normalize to the same value
- **THEN** migration upgrade stops before installing the new constraints and identifies normalized email collisions as the required remediation

#### Scenario: Existing SKU collision blocks upgrade
- **WHEN** two stored non-empty SKUs are equivalent after trimming and case folding
- **THEN** migration upgrade stops before installing the new constraints and identifies normalized SKU collisions as the required remediation

#### Scenario: Migration lifecycle preserves business records
- **WHEN** the migration is upgraded, downgraded, and upgraded again on collision-free data
- **THEN** all pre-existing users and variants remain present with their business relationships intact throughout the lifecycle

### Requirement: PostgreSQL identity tests are isolated and explicit
PostgreSQL-only identity and migration tests SHALL use `TEST_POSTGRES_DATABASE_URL`, SHALL clearly skip when it is absent, SHALL reject a configured non-PostgreSQL URL, and SHALL remove only records they created.

#### Scenario: PostgreSQL test URL is absent
- **WHEN** the PostgreSQL-only suite runs without `TEST_POSTGRES_DATABASE_URL`
- **THEN** those tests are reported as skipped with a clear reason while applicable SQLite tests remain runnable

#### Scenario: PostgreSQL test URL uses another dialect
- **WHEN** `TEST_POSTGRES_DATABASE_URL` is configured with a non-PostgreSQL database URL
- **THEN** the PostgreSQL-only suite fails configuration validation before mutating that database

