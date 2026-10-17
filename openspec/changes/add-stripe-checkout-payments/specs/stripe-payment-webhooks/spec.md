## Purpose

Defines secure, replay-safe Stripe webhook processing as the authoritative path for reconciling provider payment outcomes with local orders, payment attempts, and inventory reservations.

## ADDED Requirements

### Requirement: Stripe webhook requests are authenticated before processing
The system SHALL accept Stripe payment events only through a dedicated endpoint that verifies the provider signature over the unmodified request body using the configured endpoint secret.

#### Scenario: Valid signed event arrives
- **WHEN** Stripe sends a supported event with a valid signature and current timestamp
- **THEN** the system accepts the event for idempotent reconciliation without requiring customer authentication

#### Scenario: Signature is missing or invalid
- **WHEN** a request lacks a valid Stripe signature, uses an invalid secret, has an unacceptable timestamp, or its signed body was modified
- **THEN** the system rejects the request and does not create webhook state or mutate orders, payments, carts, or inventory

#### Scenario: Unsupported signed event arrives
- **WHEN** a validly signed event type is not required by the integration
- **THEN** the system acknowledges it without mutating payment or order state

### Requirement: Webhook delivery is durably deduplicated and order independent
The system SHALL record provider event identifiers durably, process supported events idempotently, and produce correct state without assuming events arrive once or in generation order.

#### Scenario: Same event is delivered repeatedly
- **WHEN** Stripe retries an event with an event identifier already processed successfully
- **THEN** the system acknowledges the duplicate without repeating an order transition, inventory change, or other side effect

#### Scenario: Distinct events repeat the same object outcome
- **WHEN** separate Stripe events report the same effective state for one Checkout Session
- **THEN** the payment-attempt and order transition remains idempotent and inventory changes at most once

#### Scenario: Events arrive out of order
- **WHEN** an older or nonterminal event arrives after a terminal paid, failed, expired, or cancelled outcome
- **THEN** monotonic transition rules preserve the terminal outcome and prevent state regression

#### Scenario: Processing fails transiently
- **WHEN** a supported event cannot be committed because of a transient local failure
- **THEN** the endpoint returns a retryable failure and a later delivery can safely complete reconciliation

### Requirement: Webhook reconciliation verifies provider and local payment identity
The system SHALL reconcile an event only when the Checkout Session maps to the expected local payment attempt and order and its provider state, amount, currency, livemode, and metadata agree with authoritative local records.

#### Scenario: Provider data matches the pending attempt
- **WHEN** a supported event identifies the expected session, order, amount, currency, environment, and payment attempt
- **THEN** the system applies the corresponding allowed state transition under row locks

#### Scenario: Amount or currency does not match
- **WHEN** Stripe reports a total or currency different from the local payment attempt or order
- **THEN** the system records the reconciliation failure, leaves the order unconfirmed, and does not release or decrement inventory incorrectly

#### Scenario: Session is unknown or metadata is inconsistent
- **WHEN** a supported event cannot be associated with exactly one expected local payment attempt and order
- **THEN** the system records or reports the anomaly without exposing customer data or mutating unrelated records

#### Scenario: Test and live modes are mixed
- **WHEN** an event's provider environment does not match the configured application environment or stored attempt
- **THEN** the system rejects reconciliation and leaves local payment state unchanged

### Requirement: Paid Stripe state confirms an order exactly once
The system SHALL mark a pending order confirmed and paid only after verified Stripe state reports that funds are available, and SHALL set its confirmation time without decrementing already reserved inventory again.

#### Scenario: Checkout completes with immediate payment
- **WHEN** a verified Checkout Session completion reports paid state
- **THEN** the system marks the payment attempt paid and the order confirmed and paid exactly once while retaining its reserved inventory consumption

#### Scenario: Delayed payment later succeeds
- **WHEN** a verified asynchronous payment-success event arrives for a matching pending attempt
- **THEN** the system marks the attempt paid and the order confirmed and paid exactly once

#### Scenario: Completion is not yet paid
- **WHEN** Checkout completes but the verified provider payment state remains unpaid or processing
- **THEN** the system keeps the attempt and order pending without claiming confirmation or releasing inventory

### Requirement: Terminal unpaid events release reservations exactly once
The system SHALL reconcile verified expiration and terminal payment failure by cancelling the pending order and restoring its reserved inventory once, unless paid state has already won the transition.

#### Scenario: Checkout Session expires
- **WHEN** a verified expiration event arrives for an unpaid open attempt
- **THEN** the system marks the attempt expired, cancels the order with failed payment state, and restores reserved quantities exactly once

#### Scenario: Asynchronous payment fails
- **WHEN** a verified asynchronous payment-failure event arrives for a pending attempt
- **THEN** the system marks the attempt failed, cancels the order with failed payment state, and restores reserved quantities exactly once

#### Scenario: Terminal event is replayed
- **WHEN** an expiration or failure outcome is processed more than once
- **THEN** the system does not increment inventory more than once or change an already terminal order again

#### Scenario: Failure follows verified payment
- **WHEN** an unpaid terminal event arrives after the order was already verified paid
- **THEN** the system preserves confirmed paid state and does not restore inventory

### Requirement: Payment reconciliation is operable and auditable
The system SHALL expose enough non-secret event and attempt state for operators to diagnose and safely retry failed reconciliation without storing card details or treating logs as the source of truth.

#### Scenario: Operator reviews a failed reconciliation
- **WHEN** a webhook event cannot be matched or committed
- **THEN** durable state identifies the event ID, event type, related provider object, processing outcome, and safe error summary without storing raw card data

#### Scenario: Operator retries reconciliation
- **WHEN** an authorized operational workflow reprocesses a previously failed supported event or retrieves the current Checkout Session
- **THEN** the same idempotent transition rules apply and no duplicate payment, order, or inventory side effect occurs

