## Purpose

Defines durable and privacy-conscious audit evidence for privileged administrator and inventory mutations.

## ADDED Requirements

### Requirement: Privileged mutations create atomic audit records
The system SHALL persist an audit record in the same transaction as each successful administrator access change and administrator inventory mutation, identifying the actor, action, target, timestamp, request ID, and bounded before/after facts.

#### Scenario: Inventory quantity changes
- **WHEN** an administrator successfully changes listing quantity
- **THEN** the transaction stores an audit record with the actor, listing target, prior quantity, new quantity, and request ID

#### Scenario: Mutation rolls back
- **WHEN** the privileged business mutation is rolled back
- **THEN** no success audit record for that mutation remains committed

### Requirement: Audit data excludes secrets and unnecessary personal data
Audit records SHALL use an allowlist of fields and SHALL NOT store credentials, authentication tokens, cookies, payment secrets, raw webhook content, password material, or arbitrary request bodies.

#### Scenario: Privileged request contains sensitive headers
- **WHEN** an audited mutation includes authorization or cookie headers
- **THEN** the audit record contains none of those header values

### Requirement: Audit records are protected and append-only through the API
Only authorized administrators SHALL be able to query bounded, filterable audit results, and no public API SHALL permit audit records to be changed or deleted.

#### Scenario: Unauthorized audit query
- **WHEN** a guest or non-administrator requests audit records
- **THEN** access is denied without revealing audit contents

#### Scenario: Filtered administrator query
- **WHEN** an authorized administrator filters audit records by supported actor, action, target, or time bounds
- **THEN** the API returns a bounded page in stable newest-first order

