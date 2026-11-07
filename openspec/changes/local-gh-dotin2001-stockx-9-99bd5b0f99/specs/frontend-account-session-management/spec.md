## Purpose

Defines secure and accessible frontend behavior for account recovery, email verification, global session revocation, and recovery from expired authenticated sessions.

## ADDED Requirements

### Requirement: Password recovery preserves account privacy
The frontend SHALL provide a forgot-password form that validates an email address, prevents duplicate submission while pending, and submits it to the existing password-reset request contract. After any accepted request, the frontend SHALL display the same neutral confirmation regardless of whether the address belongs to an account.

#### Scenario: Accepted recovery request
- **WHEN** a visitor submits a valid email and the server accepts the password-reset request
- **THEN** the frontend displays a neutral instruction-sent confirmation that does not disclose account registration status

#### Scenario: Invalid recovery input
- **WHEN** a visitor submits an invalid email address
- **THEN** the frontend displays an accessible validation error and does not submit the request

#### Scenario: Recovery request is rate limited
- **WHEN** the server rejects a password-reset request with a rate-limit response and retry interval
- **THEN** the frontend displays a retry-later state using the available interval and prevents repeated submission during that interval

### Requirement: Password reset consumes action tokens safely
The frontend SHALL provide a reset-password page that reads the action token from the link, accepts a new password satisfying the confirmed API constraints, prevents duplicate submission, and submits the token and new password to the existing reset confirmation contract. It SHALL not persist or log the action token.

#### Scenario: Password reset succeeds
- **WHEN** a visitor submits a valid action token and valid new password and confirmation succeeds
- **THEN** the frontend displays success, explains that existing sessions were revoked, and provides a path to log in with the new password

#### Scenario: Reset token is missing
- **WHEN** the reset-password page is opened without an action token
- **THEN** the frontend displays an invalid-link state with paths to request another reset or return to login and does not call the confirmation endpoint

#### Scenario: Reset token is invalid, expired, or already consumed
- **WHEN** reset confirmation returns the server's invalid-action-token error
- **THEN** the frontend displays a token-failure state that covers invalid, expired, and already-used links and offers a new reset request

#### Scenario: Reset validation or API failure occurs
- **WHEN** reset confirmation fails because of invalid input or a non-token API error
- **THEN** the frontend displays the appropriate validation or retryable API error without losing the entered password unnecessarily or resubmitting automatically

### Requirement: Email verification reflects server state
The account experience SHALL show verification status from the authenticated user's server representation. It SHALL allow an unverified user to request another verification message, respect pending and cooldown states, and consume a verification-link token on a dedicated page.

#### Scenario: Account status is displayed
- **WHEN** an authenticated user opens the account page
- **THEN** the frontend labels the email as verified or unverified from the current server-provided user state

#### Scenario: Verification resend is accepted
- **WHEN** an unverified user requests another verification email and the server accepts it
- **THEN** the frontend displays neutral success feedback and disables duplicate requests during the client cooldown

#### Scenario: Verification resend is rate limited
- **WHEN** the resend request receives a rate-limit response with a retry interval
- **THEN** the frontend displays when retry is allowed and keeps the resend action unavailable for that interval

#### Scenario: Verification link succeeds for current user
- **WHEN** the verification page confirms a valid token and returns an updated user
- **THEN** the frontend displays success and updates matching authenticated user state so the account view reflects verification without another login

#### Scenario: Verification token fails
- **WHEN** verification confirmation receives a missing or invalid-action-token condition
- **THEN** the frontend displays an invalid, expired, or already-used link state with a path to request another verification email or log in

### Requirement: User can log out all devices
The account page SHALL expose “Log out all devices” only to an authenticated user, require explicit confirmation, and call the authenticated global-logout contract. After success it SHALL clear in-memory authentication state and redirect to login.

#### Scenario: User cancels global logout
- **WHEN** an authenticated user declines the confirmation prompt
- **THEN** the frontend leaves the session unchanged and does not call global logout

#### Scenario: Global logout succeeds
- **WHEN** the authenticated global-logout request succeeds
- **THEN** the frontend clears the current access token and user state and redirects to login with confirmation that all sessions were ended

#### Scenario: Global logout fails
- **WHEN** the global-logout request fails without establishing that the session is expired
- **THEN** the frontend preserves the current local session, displays an actionable API error, and allows a later retry

### Requirement: Expired authenticated requests recover through one coordinated refresh
When an eligible request carrying the current access token receives 401, the frontend SHALL coordinate all concurrent recovery attempts through one refresh request, update authentication state after success, and retry each eligible failed request at most once. Authentication endpoints, a retried request, and responses other than 401 SHALL NOT trigger refresh.

#### Scenario: One expired request recovers
- **WHEN** an eligible authenticated request receives 401 and refresh succeeds
- **THEN** the frontend updates the current token and user and retries the original request once with the new token

#### Scenario: Concurrent expired requests recover
- **WHEN** multiple eligible authenticated requests receive 401 before recovery completes
- **THEN** they await one shared refresh request and each retries at most once after that refresh succeeds

#### Scenario: Retried request remains unauthorized
- **WHEN** a request retried after successful refresh receives another 401
- **THEN** the frontend does not refresh again, clears local authentication state, and proceeds to login recovery

#### Scenario: Forbidden request is denied
- **WHEN** any request receives 403
- **THEN** the frontend displays an access-denied state and does not attempt token refresh

### Requirement: Failed recovery uses a safe return destination
When session recovery fails, the frontend SHALL clear local authentication state and redirect protected browser journeys to login with only a normalized same-origin internal path as the return destination. It MUST reject external, protocol-relative, login-page, or otherwise unsafe return values.

#### Scenario: Protected journey loses its session
- **WHEN** refresh fails while the user is on an internal protected route
- **THEN** the frontend redirects to login with that path and query as the safe post-login return destination

#### Scenario: Proposed return destination is unsafe
- **WHEN** a return destination is external, protocol-relative, malformed, or points back to an authentication entry page
- **THEN** the frontend omits it or replaces it with the default internal account destination

#### Scenario: Public request receives unauthorized response
- **WHEN** a request without an authenticated access token receives 401
- **THEN** the frontend reports the request error without invoking refresh or forcing a login redirect

### Requirement: Account flows are accessible and responsive
All new forms and account-session controls SHALL provide associated labels, keyboard-operable controls, announced status and error feedback, visible disabled or busy states, and layouts usable on mobile and desktop. Pending mutations SHALL prevent duplicate submission.

#### Scenario: Mutation is pending
- **WHEN** a recovery, verification, or logout-all mutation is in progress
- **THEN** its initiating control is disabled, its busy state is communicated, and a second submission is not sent

#### Scenario: Account flow is used with keyboard or narrow viewport
- **WHEN** a user navigates a new flow without a pointing device or on a mobile-width viewport
- **THEN** all content and controls remain reachable, legible, and operable in a logical focus order

