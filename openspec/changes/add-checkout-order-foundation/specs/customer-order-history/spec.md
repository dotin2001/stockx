## Purpose

Defines secure customer-facing order confirmation and history so completed checkout intent remains understandable after cart and catalog data change.

## ADDED Requirements

### Requirement: Customers can view their order history
The system SHALL provide authenticated customers with a paginated list containing only their own orders, ordered newest first.

#### Scenario: Customer has orders
- **WHEN** an authenticated customer requests order history
- **THEN** the system returns that customer's orders with order number, creation time, status, payment state, currency, total, and summary item information

#### Scenario: Customer has no orders
- **WHEN** an authenticated customer with no orders requests order history
- **THEN** the system returns an empty paginated result suitable for an order-history empty state

#### Scenario: Guest requests order history
- **WHEN** an unauthenticated client requests customer order history
- **THEN** the system rejects the request with an authentication error

### Requirement: Customers can view their own order detail and confirmation
The system SHALL provide authenticated order detail containing order status, payment state, totals, shipping snapshot, and immutable item snapshots for the owning customer.

#### Scenario: Customer opens a newly created order
- **WHEN** a customer is redirected to the order detail after successful confirmation
- **THEN** the system presents the order as confirmed, identifies it by its public order number, and clearly labels payment as unpaid

#### Scenario: Customer reopens a historical order
- **WHEN** a customer opens one of their orders from order history
- **THEN** the system returns the same persisted order and item snapshots without requiring the original cart rows

#### Scenario: Customer requests another customer's order
- **WHEN** an authenticated customer requests an order owned by another user
- **THEN** the system returns a not-found response without exposing that the order exists

### Requirement: Historical order presentation is independent of mutable catalog records
The system SHALL preserve the product, variant, price, quantity, and recipient information shown for an order even when related live catalog, listing, account, or inventory data changes later.

#### Scenario: Product or listing changes after checkout
- **WHEN** a related product is renamed or archived, a variant changes, a listing price changes, or listing inventory is removed after order creation
- **THEN** the customer's order detail and totals continue to show the original purchase snapshots

#### Scenario: Customer account profile changes
- **WHEN** the customer changes mutable account information after order creation
- **THEN** the historical order continues to show the customer and shipping snapshots captured at checkout

### Requirement: Foundation customer orders are read-only
The system SHALL expose no customer action in this change that changes order status, payment status, item snapshots, totals, or shipping snapshots after creation.

#### Scenario: Customer reviews an unpaid order
- **WHEN** a customer views a confirmed unpaid manual order
- **THEN** the interface provides history and status information without offering payment, cancellation, refund, fulfillment, or shipment actions

