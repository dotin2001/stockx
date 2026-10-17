## Purpose

Defines how authenticated customers start and return from Stripe-hosted payment while the store preserves authoritative pricing, order snapshots, inventory safety, and explicit payment state.

## ADDED Requirements

### Requirement: Stripe checkout is explicitly configured and safely gated
The system SHALL keep checkout disabled by default, SHALL preserve manual checkout as a development-only mode, and SHALL enable Stripe order placement only when Stripe mode and all required provider, webhook, and application URL settings are valid.

#### Scenario: Stripe mode is not configured
- **WHEN** checkout remains disabled or required Stripe settings are absent
- **THEN** the system does not create a pending order, reserve inventory, or contact Stripe and presents checkout as unavailable

#### Scenario: Manual development mode remains enabled
- **WHEN** a developer explicitly selects manual checkout mode
- **THEN** the existing confirmed-unpaid manual order behavior remains available without creating Stripe payment state

#### Scenario: Stripe mode is valid
- **WHEN** Stripe mode is selected with valid secret, webhook, application URL, and reservation settings
- **THEN** the checkout summary identifies Stripe payment as available and permits an authenticated customer to continue to payment

### Requirement: Stripe checkout uses authoritative server-side purchase data
The system SHALL create Stripe payment requests only from a revalidated authenticated cart, current sellable listings, server-calculated money, valid shipping data, and the checkout token the customer reviewed.

#### Scenario: Reviewed checkout remains current
- **WHEN** the customer starts Stripe checkout with a valid current checkout token and shipping details
- **THEN** the Stripe Checkout Session uses server-derived item names, quantities, unit amounts, currency, subtotal, shipping, tax, and total

#### Scenario: Reviewed checkout became stale
- **WHEN** cart contents, price, inventory, listing availability, product archive state, or currency changed after review
- **THEN** the system rejects session creation, asks the customer to review a refreshed summary, and leaves order, payment, cart, and inventory state unchanged

#### Scenario: Client submits authoritative payment values
- **WHEN** a client attempts to supply product prices, totals, currency, or provider identifiers
- **THEN** the system ignores or rejects those values and never uses them as the source of truth for payment

### Requirement: Starting payment creates one pending order and reserves inventory
The system SHALL atomically create a pending-payment order with immutable snapshots, reserve its listing quantities, remove its purchased cart rows, and create a customer-owned payment attempt before exposing a hosted payment URL.

#### Scenario: Payment session starts successfully
- **WHEN** Stripe accepts a session for a valid checkout
- **THEN** the system returns a Stripe-hosted URL associated with one `pending_payment` and `unpaid` order, one open payment attempt, a reservation expiration, decremented available inventory, and cleared purchased cart rows

#### Scenario: Customers compete for the final unit
- **WHEN** multiple customers concurrently start payment for the same final available unit
- **THEN** at most one customer receives a payable session and the others receive a conflict without partial order, payment, cart, or inventory changes

#### Scenario: Local reservation fails
- **WHEN** order, payment-attempt, inventory, or cart persistence fails before a payable URL is returned
- **THEN** the system rolls back the local operation and ensures any unreturned provider session cannot produce a valid local purchase

#### Scenario: Provider session creation fails definitively
- **WHEN** Stripe definitively rejects session creation
- **THEN** the system compensates any pending local checkout state, restores reserved inventory and purchased cart rows exactly once, and reports that payment could not be started

### Requirement: Stripe checkout initiation is idempotent and recoverable
The system SHALL require a customer-scoped idempotency key and SHALL use a stable provider idempotency key so retries cannot create duplicate orders, sessions, reservations, or cart mutations.

#### Scenario: Equivalent initiation is retried
- **WHEN** the same customer repeats an equivalent Stripe checkout request with the same idempotency key
- **THEN** the system returns the existing order and usable open Checkout Session without reserving inventory again

#### Scenario: Initiation key is reused for different data
- **WHEN** the customer reuses an initiation key with different shipping or reviewed-cart data
- **THEN** the system rejects the request without creating or changing order, payment, cart, inventory, or provider state

#### Scenario: Provider response is ambiguous
- **WHEN** the connection fails after Stripe might have accepted the request
- **THEN** a retry uses the same provider idempotency key to recover the original session rather than creating another payment attempt

### Requirement: Payment return and order presentation do not claim unverified success
The system SHALL present pending, paid, cancelled, failed, and expired payment states from authenticated server data and SHALL NOT treat a Stripe browser redirect or query parameter as proof of payment.

#### Scenario: Customer is redirected to Stripe
- **WHEN** checkout initiation returns an open hosted session
- **THEN** the frontend redirects the customer to the provider URL and does not collect or transmit raw card details itself

#### Scenario: Customer returns before webhook reconciliation
- **WHEN** Stripe redirects the customer to the order return page while the order remains pending
- **THEN** the page identifies the order as awaiting payment confirmation and refreshes authenticated order state without marking it paid

#### Scenario: Customer returns after verified payment
- **WHEN** the customer's order has been reconciled to confirmed and paid
- **THEN** order confirmation, history, and detail display the paid state, confirmation time, totals, shipping snapshot, and immutable item snapshots

#### Scenario: Another customer uses a return or session identifier
- **WHEN** an authenticated customer attempts to inspect or resume payment for an order they do not own
- **THEN** the system returns not found and discloses no order or payment-attempt information

### Requirement: Pending reservations end safely
The system SHALL use a 30-minute open-session reservation and SHALL release reserved inventory exactly once when an unpaid order is explicitly cancelled or its Checkout Session expires, while never releasing inventory for a verified paid order.

#### Scenario: Open session expires unpaid
- **WHEN** Stripe reports that an open Checkout Session expired without payment
- **THEN** the system marks the attempt expired, marks the pending order cancelled with failed payment state, and restores each reserved listing quantity exactly once

#### Scenario: Customer cancels a pending payment
- **WHEN** the owning customer explicitly cancels an unpaid pending order
- **THEN** the system expires any open provider session, marks the order and attempt terminal, restores inventory exactly once, and prevents that session from being resumed

#### Scenario: Customer resumes an open payment
- **WHEN** the owning customer reopens a pending order before its current session expires
- **THEN** the system can return the existing open hosted payment URL without changing totals or reserving inventory again

#### Scenario: Payment and cancellation race
- **WHEN** verified paid state races with expiration or cancellation processing
- **THEN** row-locked reconciliation produces one terminal outcome, preserves the paid order when Stripe confirms payment, and never both confirms and releases the same reservation

#### Scenario: Unexpected delayed payment remains processing
- **WHEN** a completed Checkout Session is not yet paid and awaits an asynchronous result
- **THEN** the system keeps the order pending and its inventory reserved until a verified terminal success or failure event is reconciled

