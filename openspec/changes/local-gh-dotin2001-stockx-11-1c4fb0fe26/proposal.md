## Why

Authentication must remain correct under concurrent requests and resistant to token replay and endpoint abuse. Users also need complete account lifecycle controls without account-enumeration leaks or unstable server errors during registration races.

## What Changes

- Make refresh-token rotation atomic with PostgreSQL row locking and explicit token families.
- Treat reuse of an already-rotated refresh token as replay, revoke its active family, clear the refresh cookie, and reject the request.
- Add independently configurable rate limits for registration, login, refresh, verification requests, and password-reset requests.
- Apply standards-aware email validation while preserving canonical normalization and deterministic `409 email_exists` responses for concurrent duplicate registrations.
- Add non-enumerating email-verification and password-reset flows backed by single-use, expiring, digest-only tokens.
- Add authenticated logout across all devices and revoke all existing sessions after a successful password reset.

## Capabilities

### New Capabilities

- `authentication-hardening`: Concurrency-safe refresh-token rotation and replay handling, authentication rate limits, email validation and verification, password recovery, global logout, and deterministic registration conflicts.

### Modified Capabilities

- None. The main specification set does not currently define authentication requirements.

## Impact

- Affected backend areas include auth schemas, versioned auth routes, auth and rate-limit services, security utilities, settings, delivery adapters, and API error handling.
- PostgreSQL persistence and migrations will cover refresh-token family identity, user verification state, and single-use verification/reset challenges with supporting indexes and constraints.
- Existing login, refresh, logout, and registration contracts remain compatible except for stricter invalid-email rejection, explicit rate-limit responses, and deterministic replay/session revocation behavior.
- Backend unit, PostgreSQL concurrency, migration, route, and smoke tests will cover the new security and account-lifecycle behavior.
