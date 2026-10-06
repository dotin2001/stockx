## Purpose

Defines the store administration role hierarchy so day-to-day admins can operate catalog, inventory, messaging, and order-review surfaces while only supreme admins can grant or remove normal admin access.

## ADDED Requirements

### Requirement: Admin role hierarchy is explicit
The system SHALL distinguish customers, normal admins, and supreme admins with externally observable account state.

#### Scenario: Customer has no admin privileges
- **WHEN** an authenticated user is neither a normal admin nor a supreme admin
- **THEN** the system identifies the user as a customer and rejects admin-only actions

#### Scenario: Normal admin has store operation privileges
- **WHEN** an authenticated user is a normal admin and not a supreme admin
- **THEN** the system allows existing admin-only catalog, inventory/listing, customer-message, and order-review access while rejecting supreme-admin-only actions

#### Scenario: Supreme admin includes normal admin privileges
- **WHEN** an authenticated user is a supreme admin
- **THEN** the system also treats the user as a normal admin for every admin-only store operation

#### Scenario: Current user response exposes role state
- **WHEN** an authenticated user registers, logs in, refreshes a session, or requests the current user
- **THEN** the system returns public user data that includes both normal-admin and supreme-admin state

### Requirement: Supreme admins can manage normal admin access
The system SHALL allow supreme admins to promote customer accounts to normal admin and demote normal admin accounts back to customer.

#### Scenario: Supreme admin promotes customer to normal admin
- **WHEN** a supreme admin promotes an existing customer account to normal admin
- **THEN** the system marks that account as a normal admin, leaves it non-supreme, and returns the updated public user data

#### Scenario: Supreme admin demotes normal admin to customer
- **WHEN** a supreme admin demotes an existing normal admin account that is not supreme
- **THEN** the system removes normal admin access from that account and returns the updated public user data

#### Scenario: Promotion is idempotent for normal admins
- **WHEN** a supreme admin promotes an existing normal admin who is not supreme
- **THEN** the system reports success without changing unrelated account or authentication data

#### Scenario: Missing user management target is rejected
- **WHEN** a supreme admin attempts to promote or demote a user that does not exist
- **THEN** the system returns a not-found error and does not change any account

### Requirement: Admin management is restricted to supreme admins
The system SHALL reject admin-management actions from anonymous users, customers, and normal admins.

#### Scenario: Anonymous admin management is rejected
- **WHEN** an unauthenticated client attempts to list admin-management users or change a user's admin access
- **THEN** the system returns an authentication error and does not reveal protected user-management data

#### Scenario: Customer admin management is rejected
- **WHEN** an authenticated customer attempts to list admin-management users or change a user's admin access
- **THEN** the system returns an authorization error and does not change any account

#### Scenario: Normal admin management is rejected
- **WHEN** an authenticated normal admin attempts to list admin-management users or change a user's admin access
- **THEN** the system returns an authorization error and does not change any account

### Requirement: Supreme admin access is protected from in-app demotion
The system SHALL NOT allow the in-app admin-management surface to create, demote, or otherwise modify supreme-admin status.

#### Scenario: Supreme admin cannot promote another supreme admin in-app
- **WHEN** a supreme admin promotes a customer or normal admin through the in-app management surface
- **THEN** the target becomes or remains a normal admin and does not become supreme

#### Scenario: Supreme admin demotion through in-app management is rejected
- **WHEN** a supreme admin attempts to demote an account that has supreme-admin status
- **THEN** the system rejects the request and does not remove that account's normal-admin or supreme-admin access

#### Scenario: Self-demotion is rejected
- **WHEN** a supreme admin attempts to demote their own account through the in-app management surface
- **THEN** the system rejects the request and preserves the caller's admin access

### Requirement: Supreme admin bootstrap is operator-controlled
The system SHALL provide a backend operator path for granting supreme-admin status to an existing user without using the in-app admin-management surface.

#### Scenario: Operator grants supreme admin to existing user
- **WHEN** an operator grants supreme-admin status to an existing user account
- **THEN** the system marks the user as both supreme admin and normal admin and reports success

#### Scenario: Supreme admin bootstrap preserves auth data
- **WHEN** an operator grants supreme-admin status to an existing user account
- **THEN** the user's password hash, refresh-token records, and unrelated profile data remain valid according to normal auth rules

#### Scenario: Supreme admin bootstrap rejects missing user
- **WHEN** an operator attempts to grant supreme-admin status to an email that does not belong to an existing user
- **THEN** the system reports failure and does not create a user

### Requirement: Supreme admin UI exposes user administration only to supreme admins
The frontend SHALL show admin user-management navigation and actions only to authenticated supreme admins.

#### Scenario: Supreme admin sees user-management controls
- **WHEN** an authenticated supreme admin views the site navigation or admin surfaces
- **THEN** the frontend provides access to user-management controls for normal admin promotion and demotion

#### Scenario: Normal admin does not see user-management controls
- **WHEN** an authenticated normal admin who is not supreme views the site navigation or admin surfaces
- **THEN** the frontend omits user-management controls while retaining normal admin store-operation controls

#### Scenario: Unauthorized direct navigation is blocked
- **WHEN** an anonymous user, customer, or normal admin directly opens the user-management page
- **THEN** the frontend shows an appropriate access state and the backend still rejects unauthorized user-management requests
