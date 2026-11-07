## Why

The backend already exposes account recovery, email verification, refresh rotation, and global session revocation, but the frontend does not make those contracts usable and protected requests do not recover safely from expired access tokens. Customers need complete, accessible account flows and deterministic session recovery without exposing account existence or creating refresh loops.

## What Changes

- Add forgot-password and token-driven reset-password pages with neutral request confirmation, successful reset guidance, and clear invalid, expired, or consumed-token recovery paths.
- Surface server-backed email-verification status, allow verification-email resend with cooldown and rate-limit feedback, and consume verification links while updating the authenticated user state.
- Add a confirmed “Log out all devices” account action that clears local authentication state and redirects to login after server success.
- Centralize authenticated request recovery so concurrent eligible 401 responses share one refresh attempt, retry once after success, and safely redirect to login with an internal return URL when recovery fails.
- Treat 403 as access denied without attempting refresh, and provide consistent loading, success, validation, rate-limit, access-denied, and API-error states across the new flows.
- Add focused frontend tests for successful flows, token failures, refresh coordination, retry limits, access denial, and API failures.

## Capabilities

### New Capabilities

- `frontend-account-session-management`: Defines customer-facing password recovery, email verification, global logout, and safe frontend session recovery behavior.

### Modified Capabilities

None.

## Impact

- Next.js routes, authentication context, API client, account UI, shared state presentation, and frontend tests under `apps/web`.
- Existing FastAPI contracts under `/api/v1/auth` are consumed without backend changes: password-reset request/confirm, verification request/confirm, refresh, current-user, and logout-all.
- The HTTP-only refresh cookie remains browser-managed; raw action tokens are accepted only from links and submitted to their confirmation endpoints.
- No backend authentication changes, device/session listing, catalog, checkout, or admin journeys are included.
