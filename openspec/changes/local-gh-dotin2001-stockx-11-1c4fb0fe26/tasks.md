## 1. Persistence and Migration

- [x] 1.1 Add refresh-token family identity, user verification state, and purpose-bound single-use account-challenge models with required indexes and constraints; verify SQLAlchemy model tests assert columns, relationships, and constraints.
- [x] 1.2 Add an Alembic migration that sanitizes malformed legacy replacement links, backfills deterministic families, enforces non-null family identity, and creates challenge persistence; verify upgrade and downgrade against PostgreSQL, including existing linked and unlinked refresh rows.

## 2. Session Rotation and Revocation

- [x] 2.1 Lock presented refresh-token rows and atomically revoke/link exactly one successor in the same family; verify a barrier-coordinated PostgreSQL test shows two concurrent refreshes cannot both issue replacements.
- [x] 2.2 Detect reuse of a replaced token, revoke every active token in its family, clear the cookie, and return `401 invalid_refresh_token`; verify replay tests reject the replacement and later descendants while leaving unrelated families usable.
- [x] 2.3 Add authenticated logout-all behavior that revokes every active refresh token for the caller and clears the current cookie; verify route/service tests show all caller sessions fail afterward and other users remain unaffected.

## 3. Registration and Abuse Controls

- [x] 3.1 Apply standards-aware email validation before canonical normalization while preserving recognized uniqueness-constraint translation to `409 email_exists`; verify invalid-address tests and concurrent PostgreSQL registration tests produce validation or conflict responses rather than server errors.
- [x] 3.2 Add independently configurable registration, login, refresh, verification, and password-reset policies through a replaceable rate-limit store using keyed digests for client/account identity; verify policy tests cover successful/failed consumption, `429 rate_limit_exceeded`, `Retry-After`, trusted proxy handling, and configured store-outage behavior.
- [x] 3.3 Validate production configuration requires the shared atomic rate-limit backend and safe failure policy while retaining an in-process test/development option; verify settings tests reject unsafe production combinations.

## 4. Verification and Password Recovery

- [x] 4.1 Add a delivery abstraction and issue high-entropy verification/reset tokens while persisting only purpose-bound digests with expiry and consumption state; verify tests prove raw tokens are absent from persistence, responses, and logs.
- [x] 4.2 Implement non-enumerating verification request and single-use confirmation operations that expose updated public verification state; verify known/unknown request responses match and confirmation tests cover success, reuse, expiry, and purpose mismatch.
- [x] 4.3 Implement non-enumerating password-reset request and single-use confirmation operations that atomically update the password and revoke all user sessions; verify tests cover success, password-policy failure, reuse, expiry, session revocation, and unaffected other users.
- [x] 4.4 Register and document versioned verification, reset, and logout-all routes using the existing API error envelope and cookie policy; verify route/OpenAPI tests assert request validation, response schemas, status codes, and auth protection.

## 5. Integrated Verification

- [x] 5.1 Run the backend test suite and dedicated PostgreSQL identity/refresh concurrency tests; verify every trusted test command exits successfully.
- [x] 5.2 Apply the migration to local PostgreSQL, run the auth smoke flow through registration, verification, login, refresh, replay rejection, password reset, restored login, and logout-all, then downgrade; verify all commands succeed without exposing raw credentials or action tokens.
