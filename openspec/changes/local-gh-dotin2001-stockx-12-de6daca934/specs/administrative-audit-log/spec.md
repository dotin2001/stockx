## Purpose

Maintain a durable, privacy-conscious accountability trail for administrative actions and inventory changes, with enough context for authorized operational review.

## ADDED Requirements

### Requirement: Sensitive mutations create durable audit records
The system SHALL create an audit record for every successful administrative action and every inventory quantity change. Each record MUST identify the authenticated actor, action, affected record type and identifier, server-generated timestamp, and request ID, and MUST be committed atomically with the mutation it describes.

#### Scenario: Administrator changes a managed record
- **WHEN** an authenticated administrator successfully creates, updates, deletes, or changes access on a managed record
- **THEN** the same transaction persists an audit record identifying the administrator, action, target, timestamp, and request correlation

#### Scenario: Inventory quantity changes
- **WHEN** available inventory changes through an administrative edit, listing operation, checkout reservation, release, or completed sale
- **THEN** the same transaction persists an audit record identifying the actor or accountable system context, affected inventory record, timestamp, and bounded before-and-after quantity facts

#### Scenario: Mutation rolls back
- **WHEN** a protected mutation fails or its database transaction is rolled back
- **THEN** no audit record claiming that mutation succeeded remains committed

### Requirement: Audit facts are bounded and non-sensitive
Audit records SHALL store only allowlisted before-and-after facts needed to explain the mutation. They MUST NOT store passwords, authentication tokens, payment secrets, raw webhook payloads, or unrestricted request bodies, and stored fact payloads MUST have an enforced size bound.

#### Scenario: Mutation contains sensitive input
- **WHEN** an audited operation processes credentials, tokens, payment data, or other non-allowlisted fields
- **THEN** those values are excluded from the audit record

### Requirement: Audit history is restricted and queryable
Only an authorized administrator SHALL be able to retrieve audit history. Retrieval SHALL support bounded pagination and filtering by actor, action, target, and timestamp range, and SHALL return records in deterministic newest-first order.

#### Scenario: Authorized administrator filters audit history
- **WHEN** an authorized administrator requests audit history with supported filters and pagination
- **THEN** the service returns only matching records in deterministic newest-first order with a bounded page size

#### Scenario: Unauthorized caller requests audit history
- **WHEN** a guest or non-administrator requests audit history
- **THEN** the service rejects the request without disclosing audit data
