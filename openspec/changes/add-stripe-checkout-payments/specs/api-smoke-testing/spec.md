## ADDED Requirements

### Requirement: Smoke tests verify Stripe checkout and payment reconciliation
The system SHALL extend the running-service smoke workflow with a repeatable Stripe sandbox or deterministic provider-harness path that verifies pending checkout, signed payment reconciliation, customer-visible paid state, and inventory safety.

#### Scenario: Stripe checkout smoke flow starts payment
- **WHEN** the smoke workflow authenticates a unique customer, adds available seeded inventory, reviews checkout, and starts Stripe payment with unique request data
- **THEN** it verifies one pending unpaid order and open payment attempt are created, the hosted session is correlated to that order, inventory is reserved, and purchased cart rows are cleared

#### Scenario: Signed paid event confirms the order
- **WHEN** the smoke workflow delivers or observes a valid paid Checkout Session event for the pending attempt
- **THEN** it verifies the order becomes confirmed and paid, its snapshots remain readable, and inventory is not decremented a second time

#### Scenario: Duplicate event is harmless
- **WHEN** the same successful provider event is delivered again
- **THEN** the smoke workflow verifies no duplicate order, payment attempt, webhook side effect, or inventory decrement occurs

#### Scenario: Invalid webhook signature is rejected
- **WHEN** the smoke workflow sends a payment event with an invalid signature
- **THEN** it verifies the API rejects the event and leaves order, payment, cart, and inventory state unchanged

#### Scenario: Expired session releases inventory
- **WHEN** the smoke workflow reconciles a valid expiration for a distinct unpaid pending order
- **THEN** it verifies the order is cancelled, payment is failed or expired, and reserved inventory is restored exactly once

#### Scenario: Stripe prerequisites are absent
- **WHEN** Stripe smoke coverage is requested without sandbox credentials, endpoint secret, provider harness, or Stripe checkout mode
- **THEN** the workflow fails clearly with setup guidance rather than reporting a misleading payment regression

