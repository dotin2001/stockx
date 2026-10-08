## ADDED Requirements

### Requirement: Smoke tests verify development checkout and customer orders
The system SHALL extend the running-service smoke workflow to verify checkout order creation and customer order retrieval when development manual checkout is explicitly enabled.

#### Scenario: Manual checkout smoke flow succeeds
- **WHEN** the smoke-test workflow adds available seeded inventory to an authenticated customer's cart, reviews checkout, and confirms with unique request data
- **THEN** it verifies one confirmed unpaid order is created, purchased inventory decreases, and the purchased cart rows are cleared

#### Scenario: Created order is visible to its customer
- **WHEN** the smoke-test workflow requests order history and order detail with the creating customer's access token
- **THEN** it verifies the new order and its item, money, status, and shipping snapshots are returned

#### Scenario: Order remains customer scoped
- **WHEN** the smoke-test workflow requests the created order with another customer's access token
- **THEN** it verifies the API does not disclose the order

#### Scenario: Manual checkout prerequisite is absent
- **WHEN** the smoke-test workflow is asked to exercise order creation against a service where development manual checkout is disabled
- **THEN** it fails clearly with setup guidance rather than reporting a misleading checkout regression

