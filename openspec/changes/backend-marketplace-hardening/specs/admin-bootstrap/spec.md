## Purpose

Defines a supported backend administration bootstrap path so project operators can grant initial admin access without editing the database by hand.

## ADDED Requirements

### Requirement: Operators can promote an existing user to admin
The system SHALL provide a backend command for promoting an existing user account to admin status.

#### Scenario: Promote existing non-admin user
- **WHEN** an operator runs the admin promotion command for an existing non-admin user email
- **THEN** the system marks that user as an admin and reports success

#### Scenario: Promote existing admin user is idempotent
- **WHEN** an operator runs the admin promotion command for a user who is already an admin
- **THEN** the system reports success without creating another user or changing unrelated fields

#### Scenario: Promote missing user is rejected
- **WHEN** an operator runs the admin promotion command for an email that does not belong to an existing user
- **THEN** the system reports a failure and does not create a user

### Requirement: Admin bootstrap command normalizes user email
The system SHALL apply the same email normalization used by authentication when locating users for admin promotion.

#### Scenario: Promotion accepts mixed-case email input
- **WHEN** an operator runs the admin promotion command with mixed-case or surrounding-space email input for an existing user
- **THEN** the system locates the normalized user and promotes that account

### Requirement: Admin bootstrap command avoids password handling
The system SHALL NOT accept, display, or change user passwords as part of admin promotion.

#### Scenario: Promotion does not require password input
- **WHEN** an operator promotes an existing user to admin
- **THEN** the command completes without asking for the user's password

#### Scenario: Promotion preserves authentication data
- **WHEN** an operator promotes an existing user to admin
- **THEN** the user's existing password hash and refresh token records remain valid according to the normal auth rules
