## Purpose

Defines abuse-resistant account and session behavior, including safe token rotation, account verification, recovery, and revocation.

## ADDED Requirements

### Requirement: Refresh tokens rotate atomically within a family
The API SHALL assign refresh tokens to a session family and SHALL lock the presented token while atomically revoking it and issuing its single replacement.

#### Scenario: Concurrent refresh requests
- **WHEN** two transactions present the same active refresh token concurrently
- **THEN** at most one transaction receives a replacement session and the other is handled as replay

### Requirement: Refresh-token replay revokes the family
The API SHALL treat presentation of a previously rotated token as replay, revoke every active token in that family, clear the refresh cookie, and deny a new access token.

#### Scenario: Rotated token is reused
- **WHEN** a client presents a validly hashed token that was already replaced
- **THEN** all active descendants in its family are revoked and the API returns the stable `invalid_refresh_token` error

### Requirement: Users can revoke all sessions
The authenticated API SHALL provide a logout-all operation that revokes every active refresh token for the current user and clears the current refresh cookie.

#### Scenario: Global logout
- **WHEN** an authenticated user requests logout across all devices
- **THEN** every refresh token belonging to that user is revoked and none can be refreshed afterward

### Requirement: Authentication endpoints are rate limited
The API SHALL enforce separately configurable limits for registration, login, refresh, verification-message requests, and password-reset requests using privacy-preserving client and account keys.

#### Scenario: Limit exceeded
- **WHEN** a caller exceeds an authentication endpoint's configured limit
- **THEN** the API returns HTTP 429 with a stable error code and a `Retry-After` value without confirming whether an account exists

#### Scenario: Successful login does not bypass abuse controls
- **WHEN** repeated successful and unsuccessful attempts share a limited key
- **THEN** both consume the configured limit according to the endpoint policy

### Requirement: Registration validates email and resolves conflicts deterministically
The API SHALL normalize and validate email addresses using standards-aware syntax validation and SHALL return HTTP 409 with `email_exists` whenever a canonical email uniqueness conflict occurs, including concurrent inserts.

#### Scenario: Invalid email syntax
- **WHEN** registration contains an address rejected by the configured email validation policy
- **THEN** the API returns its standard validation response and creates no user

#### Scenario: Concurrent duplicate registration
- **WHEN** concurrent registrations use canonically equivalent email addresses
- **THEN** one registration can succeed and every uniqueness loser returns HTTP 409 with `email_exists` rather than HTTP 500

### Requirement: Email ownership is verifiable
The API SHALL issue single-use, expiring, stored-only-as-a-digest verification tokens and SHALL expose account verification state without leaking the token through logs or API responses.

#### Scenario: Valid verification token
- **WHEN** an unverified user presents a valid unused verification token
- **THEN** the account is marked verified and the token cannot be used again

#### Scenario: Verification request does not enumerate accounts
- **WHEN** a verification message is requested for any syntactically valid email
- **THEN** the API returns the same public response whether or not an eligible account exists

### Requirement: Password reset is single-use and revokes existing sessions
The API SHALL support non-enumerating reset requests and single-use, expiring, stored-only-as-a-digest reset tokens; successful password reset SHALL revoke all refresh tokens for the user.

#### Scenario: Successful password reset
- **WHEN** a valid unused reset token and policy-compliant new password are submitted
- **THEN** the password changes, the reset token is consumed, and all existing sessions are revoked atomically

#### Scenario: Invalid reset request
- **WHEN** a reset message is requested for an unknown but syntactically valid email
- **THEN** the API returns the same public response as for a known account

