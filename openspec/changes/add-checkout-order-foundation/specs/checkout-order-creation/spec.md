## Purpose

Defines how an authenticated customer's current cart becomes a durable order safely, consistently, and only when development manual checkout is explicitly enabled.

## ADDED Requirements

### Requirement: Checkout requires an authenticated non-empty account cart
The system SHALL require authentication and at least one available account-cart item before returning an actionable checkout summary or accepting an order.

#### Scenario: Guest starts checkout
- **WHEN** a guest starts checkout from a guest cart
- **THEN** the system routes the guest through login or signup while preserving the existing guest-cart merge intent

#### Scenario: Empty account cart cannot proceed
- **WHEN** an authenticated customer requests checkout with an empty account cart
- **THEN** the system reports that the cart is empty and does not offer order confirmation

#### Scenario: Available account cart can be reviewed
- **WHEN** an authenticated customer with available cart items opens checkout
- **THEN** the system returns a server-calculated summary of the current items, quantities, currency, subtotal, shipping, tax, total, and whether order placement is enabled

### Requirement: Manual order placement is explicitly development-gated
The system SHALL disable order placement by default and SHALL create unpaid manual orders only when an explicit development checkout mode is enabled.

#### Scenario: Checkout mode is disabled
- **WHEN** an authenticated customer attempts to place an order while manual checkout is disabled
- **THEN** the system rejects order placement without changing the cart, inventory, or order records

#### Scenario: Development manual checkout is enabled
- **WHEN** an authenticated customer confirms a valid checkout while development manual checkout is enabled
- **THEN** the system can create a confirmed order with unpaid payment state without contacting or recording a payment provider

### Requirement: Checkout uses authoritative current cart and inventory data
The system SHALL calculate order contents and money from current server-side cart, listing, product, and variant data and SHALL NOT trust client-supplied product details or prices.

#### Scenario: Current cart is converted to order lines
- **WHEN** a customer confirms checkout
- **THEN** the system derives every order line, quantity, unit price, and line total from the customer's current account cart and its current listings

#### Scenario: Listing becomes unavailable
- **WHEN** a cart listing is missing, inactive, out of stock, quantity-limited, or belongs to an archived product at confirmation time
- **THEN** the system rejects checkout with a conflict response and leaves the order, cart, and inventory unchanged

#### Scenario: Reviewed checkout changes before confirmation
- **WHEN** the cart contents, quantities, prices, or currency no longer match the checkout summary the customer reviewed
- **THEN** the system rejects confirmation as changed and requires the customer to review a refreshed summary

#### Scenario: Cart contains multiple currencies
- **WHEN** the current cart contains available listings with different currencies
- **THEN** the system rejects checkout without creating an order or changing inventory

### Requirement: Order confirmation captures customer and shipping snapshots
The system SHALL require valid recipient and shipping-address data and SHALL persist those values as order-owned snapshots rather than depending on mutable account or seller-profile data.

#### Scenario: Valid shipping information is confirmed
- **WHEN** a customer submits valid recipient name, contact details, street address, city, postal code, and country for checkout
- **THEN** the created order retains those values for confirmation and later history

#### Scenario: Required shipping information is invalid
- **WHEN** a customer omits or submits invalid required shipping information
- **THEN** the system rejects the request with validation errors and does not mutate the cart, inventory, or orders

### Requirement: Order creation is atomic with inventory and cart changes
The system SHALL create the order and item snapshots, decrement listing inventory, and remove purchased cart rows as one atomic operation.

#### Scenario: Order confirmation succeeds
- **WHEN** an eligible customer confirms a valid cart in enabled manual checkout mode
- **THEN** the system creates one confirmed unpaid order, stores immutable item snapshots, decrements each listing by the purchased quantity, clears the purchased cart rows, and returns the created order

#### Scenario: Order creation fails
- **WHEN** any validation, persistence, or inventory update fails during confirmation
- **THEN** the system rolls back the entire operation so no partial order, inventory decrement, or cart clearing remains

#### Scenario: Customers compete for the final unit
- **WHEN** multiple customers concurrently confirm orders that require the same final available inventory unit
- **THEN** no more than the available quantity is sold and each unsuccessful checkout receives a conflict response without a partial order

### Requirement: Order confirmation is idempotent
The system SHALL require a customer-scoped idempotency key for order creation so retries cannot create duplicate orders or decrement inventory more than once.

#### Scenario: Same checkout request is retried
- **WHEN** the same customer repeats an equivalent order request with the same idempotency key
- **THEN** the system returns the originally created order without creating another order or changing inventory again

#### Scenario: Idempotency key is reused for different checkout data
- **WHEN** a customer reuses an existing idempotency key with different shipping or reviewed-cart data
- **THEN** the system rejects the conflicting request without mutating any records

### Requirement: Foundation checkout does not process payment
The system SHALL NOT create payment sessions, charges, refunds, provider customer records, or webhook state as part of this order-foundation change.

#### Scenario: Manual order is confirmed
- **WHEN** development manual checkout creates an order
- **THEN** the order remains visibly unpaid and no external payment provider is contacted

