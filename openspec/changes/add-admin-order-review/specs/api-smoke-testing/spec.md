## ADDED Requirements

### Requirement: Smoke tests verify admin order review boundaries
The system SHALL extend the running-service smoke workflow to verify that admins can review customer orders while guests and customers cannot use admin order endpoints.

#### Scenario: Admin reviews a customer's order
- **WHEN** the smoke workflow creates or locates an order for a customer and authenticates a normal admin
- **THEN** it verifies the admin order list contains the order and admin detail returns its customer, item, shipping, money, status, and safe payment snapshots

#### Scenario: Admin list filters select the expected order
- **WHEN** the smoke workflow searches by the order number or customer email and combines order-status and payment-status filters
- **THEN** it verifies only matching orders are returned with consistent pagination metadata

#### Scenario: Customer cannot use admin order endpoints
- **WHEN** the smoke workflow requests admin order list and detail using the owning customer's access token
- **THEN** it verifies both requests are rejected without disclosing admin order data

#### Scenario: Guest cannot use admin order endpoints
- **WHEN** the smoke workflow requests admin order list and detail without credentials
- **THEN** it verifies both requests are rejected with authentication errors

#### Scenario: Existing customer order scoping remains intact
- **WHEN** the smoke workflow requests one customer's order through the existing customer endpoint using a different customer's access token
- **THEN** it verifies the order remains undisclosed even though admins can review it through the separate admin endpoint
