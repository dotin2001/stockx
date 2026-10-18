## Purpose

Defines secure, read-only order visibility for store administrators so they can review customer purchases and payment state without weakening customer privacy or mutating order history.

## ADDED Requirements

### Requirement: Store admins can list all customer orders
The system SHALL provide normal admins and supreme admins with a paginated list of orders across all customers, ordered newest first with a deterministic tie-breaker.

#### Scenario: Normal admin reviews orders
- **WHEN** an authenticated normal admin requests the admin order list
- **THEN** the system returns a paginated newest-first list containing orders from all customers

#### Scenario: Supreme admin reviews orders
- **WHEN** an authenticated supreme admin requests the admin order list
- **THEN** the system returns the same order-review capability available to a normal admin

#### Scenario: No orders exist
- **WHEN** an authorized admin requests the order list and no orders exist
- **THEN** the system returns an empty paginated result suitable for an admin empty state

#### Scenario: Admin paginates orders
- **WHEN** an authorized admin requests a valid bounded page using limit and offset
- **THEN** the system returns that page with total, limit, and offset metadata and no duplicate or skipped row caused by equal creation timestamps

### Requirement: Admin order list supports bounded search and filters
The system SHALL allow an authorized admin to narrow the order list by a trimmed case-insensitive partial order number or customer email search, order status, and payment status, and SHALL combine supplied criteria using AND semantics.

#### Scenario: Admin searches by order number
- **WHEN** an authorized admin submits a search term matching all or part of an order number
- **THEN** the system returns only orders whose order number matches the normalized search term

#### Scenario: Admin searches by customer email
- **WHEN** an authorized admin submits a search term matching all or part of a customer email snapshot without matching case
- **THEN** the system returns only orders whose customer email snapshot matches the normalized search term

#### Scenario: Admin filters by order and payment status
- **WHEN** an authorized admin supplies supported order-status and payment-status filters
- **THEN** the system returns only orders satisfying both filters and any supplied search term

#### Scenario: Admin supplies invalid list parameters
- **WHEN** an authorized admin supplies an unsupported status, an overlong search term, or pagination outside the documented bounds
- **THEN** the system rejects the request with the standard validation error contract

### Requirement: Admin order summaries expose useful safe state
The system SHALL include each listed order's identifier, public order number, customer name and email snapshots, creation and confirmation times, order and payment states, currency and total, item-line count, total item quantity, and safe latest payment-attempt summary when one exists.

#### Scenario: List contains mixed payment states
- **WHEN** an authorized admin views a page containing pending, paid, failed, expired, cancelled, or manual unpaid orders
- **THEN** each row presents its persisted order and payment state without implying that a browser redirect proves payment

#### Scenario: Manual order has no Stripe attempt
- **WHEN** an authorized admin views a manual order without a payment attempt
- **THEN** the system presents the order as manual and unpaid without requiring provider data

### Requirement: Store admins can review complete order detail
The system SHALL provide normal admins and supreme admins with read-only detail for any existing order, including customer, immutable item, shipping, money, safe payment-attempt, reservation, and lifecycle timestamp snapshots.

#### Scenario: Admin opens customer order detail
- **WHEN** an authorized admin requests an existing order by its internal identifier
- **THEN** the system returns the persisted customer and shipping snapshots, item names and variants, quantities and prices, totals, order and payment states, safe payment-attempt history, and lifecycle timestamps

#### Scenario: Source records changed after purchase
- **WHEN** an authorized admin opens an order after related customer, catalog, variant, listing, or inventory records changed
- **THEN** the order detail continues to show the immutable snapshots captured for that order

#### Scenario: Admin requests missing order
- **WHEN** an authorized admin requests an order identifier that does not exist
- **THEN** the system returns the standard not-found response

### Requirement: Admin order review enforces authorization and data minimization
The system SHALL enforce admin authorization on the backend, SHALL preserve customer-owned order access rules, and SHALL exclude payment secrets and internal request credentials from admin responses.

#### Scenario: Guest requests admin orders
- **WHEN** an unauthenticated client requests the admin order list or detail
- **THEN** the system rejects the request with an authentication error and discloses no order data

#### Scenario: Customer requests admin orders
- **WHEN** an authenticated non-admin requests the admin order list or detail
- **THEN** the system rejects the request with an authorization error and discloses no order data

#### Scenario: Customer uses existing order endpoint
- **WHEN** an authenticated customer requests customer order history or detail
- **THEN** the system continues to return only that customer's orders and returns not found for another customer's order

#### Scenario: Admin reviews payment information
- **WHEN** an authorized admin lists or opens an order with a Stripe payment attempt
- **THEN** the response excludes secret keys, webhook signing secrets, hosted Checkout URLs, raw webhook payloads, idempotency values, and raw card or payment-method data

### Requirement: Admin order review remains read-only
The system SHALL NOT expose admin controls in this capability for refunds, fulfillment, shipment updates, cancellation, customer payment continuation, or manual order or payment state changes.

#### Scenario: Admin views a pending order
- **WHEN** an authorized admin opens a pending-payment order
- **THEN** the interface presents the current state without Resume Payment, Cancel Pending Order, refund, fulfillment, shipment, or status-mutation actions

#### Scenario: Admin views a paid order
- **WHEN** an authorized admin opens a confirmed paid order
- **THEN** the interface presents verified payment and order details without refund, fulfillment, shipment, or status-mutation actions

### Requirement: Admin frontend exposes responsive order review
The system SHALL provide authenticated admins with `/admin/orders` and `/admin/orders/{id}` experiences and an Orders navigation link on desktop and mobile while hiding admin-order navigation from non-admins.

#### Scenario: Admin opens order list
- **WHEN** an authenticated admin follows the Orders navigation link
- **THEN** the interface renders search, status filters, pagination, and order summaries with explicit loading, empty, and error states

#### Scenario: Admin opens order detail
- **WHEN** an authenticated admin selects an order summary
- **THEN** the interface renders the complete read-only snapshot with a path back to the filtered order list

#### Scenario: Non-admin views navigation
- **WHEN** a guest or authenticated customer views desktop or mobile navigation
- **THEN** no admin Orders link is shown

#### Scenario: Role changes during access
- **WHEN** a user without current admin authorization directly opens an admin order route or loses admin access before data loads
- **THEN** the interface presents an admin-required state and does not render cached order data
