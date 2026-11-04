## Purpose

Defines abuse-resistant account and session behavior, including safe token rotation, ownership verification, password recovery, and comprehensive session revocation.

## ADDED Requirements

### Requirement: Refresh tokens rotate atomically within a family
The API SHALL assign refresh tokens to a session family and SHALL serialize replacement of a presented token so that it can issue at most one successor.

#### Scenario: Concurrent refresh requests
- **WHEN** two transactions present the same active refresh token concurrently
- **THEN** at most one transaction receives a replacement session and the other is rejected as replay

### Requirement: Refresh-token replay revokes the family
The API SHALL treat presentation of a previously replaced refresh token as replay, revoke every active token in that family, clear the refresh cookie, and deny a new access token.

#### Scenario: Rotated token is reused
- **WHEN** a client presents a validly identified token that was already replaced
- **THEN** all active tokens in its family are revoked and the API returns HTTP 401 with `invalid_refresh_token`

### Requirement: Users can revoke all sessions
The authenticated API SHALL provide a logout-all operation that revokes every active refresh token for the current user and clears the current refresh cookie.

#### Scenario: Global logout
- **WHEN** an authenticated user requests logout across all devices
- **THEN** every refresh token belonging to that user is revoked, none can be refreshed afterward, and other users' sessions are unchanged

### Requirement: Authentication endpoints are rate limited
The API SHALL enforce separately configurable limits for registration, login, refresh, verification-message requests, and password-reset requests using privacy-preserving client and account keys.

#### Scenario: Limit exceeded
- **WHEN** a caller exceeds an authentication endpoint's configured limit
- **THEN** the API returns HTTP 429 with `rate_limit_exceeded` and a `Retry-After` value without confirming whether an account exists

#### Scenario: Successful requests consume the limit
- **WHEN** successful and unsuccessful attempts share a limited key
- **THEN** both consume that endpoint's configured limit

### Requirement: Registration validates email and resolves conflicts deterministically
The API SHALL canonically normalize and standards-validate email addresses and SHALL return HTTP 409 with `email_exists` whenever canonical email uniqueness conflicts, including during concurrent inserts.

#### Scenario: Invalid email syntax
- **WHEN** registration contains an address rejected by the email validation policy
- **THEN** the API returns its standard validation response and creates no user

#### Scenario: Concurrent duplicate registration
- **WHEN** concurrent registrations use canonically equivalent email addresses
- **THEN** at most one registration succeeds and every uniqueness loser receives HTTP 409 with `email_exists` rather than a server error

### Requirement: Email ownership is verifiable
The API SHALL issue single-use, expiring verification tokens, store only token digests, expose the account's verification state, and keep request responses independent of account existence.

#### Scenario: Valid verification token
- **WHEN** an unverified user presents a valid unused verification token
- **THEN** the account is marked verified and the token cannot be used again

#### Scenario: Verification request does not enumerate accounts
- **WHEN** a verification message is requested for any syntactically valid email
- **THEN** the API returns the same public response whether or not an eligible account exists

### Requirement: Password reset is single-use and revokes existing sessions
The API SHALL support non-enumerating reset requests and single-use, expiring, digest-only reset tokens; successful password reset SHALL atomically consume the token, update the password hash, and revoke all refresh tokens for the user.

#### Scenario: Successful password reset
- **WHEN** a valid unused reset token and policy-compliant new password are submitted
- **THEN** the password changes, the reset token is consumed, all existing sessions are revoked, and the token cannot be reused

#### Scenario: Reset request does not enumerate accounts
- **WHEN** a reset message is requested for an unknown but syntactically valid email
- **THEN** the API returns the same public response as for a known account
