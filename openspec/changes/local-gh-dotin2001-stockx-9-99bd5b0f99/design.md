## Context

See `proposal.md` for motivation and `specs/frontend-account-session-management/spec.md` for observable behavior. The Next.js frontend currently keeps the access token and `UserPublic` only in `AuthProvider`, calls API methods with a token argument, performs one startup refresh, and does not intercept later 401 responses. The API already confirms the required contracts: `/api/v1/auth/password-reset/request`, `/password-reset/confirm`, `/verification/request`, `/verification/confirm`, `/refresh`, `/me`, and authenticated `/logout-all`; refresh rotates an HTTP-only cookie, action-token failures use `invalid_action_token`, rate limiting uses 429 plus `Retry-After`, and `UserPublic` includes `is_verified` and `verified_at`.

## Goals / Non-Goals

**Goals:**

- Make access-token use and refresh recovery consistent across existing and new authenticated API calls.
- Keep secrets ephemeral: access tokens remain in memory, refresh cookies remain HTTP-only, and action tokens remain URL/input data only until submitted.
- Reuse accessible presentation patterns while distinguishing validation, token, rate-limit, access-denied, and general API failures.
- Make refresh coordination and safe-return handling independently testable.

**Non-Goals:**

- Changing backend endpoints, error codes, token delivery, cookie attributes, or password rules.
- Persisting access or action tokens, rendering a device/session list, or adding cross-tab global session synchronization.
- Refactoring unrelated catalog, checkout, or admin data access beyond adopting the shared authenticated request path where needed for correctness.

## Decisions

### Put authenticated recovery behind the API client and auth session adapter

Extend the request layer with an authenticated execution path that obtains the current access token through an adapter owned by `AuthProvider`. On an eligible 401 it asks the adapter for coordinated refresh, then reconstructs and retries the request once. The adapter applies refreshed `AuthResponse` data or clears the session on terminal failure. Keeping React state ownership in the provider avoids importing hooks into the request layer; leaving every component to catch 401 was rejected because it would duplicate policy and race refresh rotation.

### Use a module-level single-flight promise for refresh rotation

The adapter will return the same in-flight refresh promise to all callers and clear the reference when it settles. A request carries an internal retry marker, so the refresh endpoint, authentication actions, requests without a bearer token, and already-retried calls cannot recurse. This is required because the backend rotates refresh tokens; parallel refresh calls could otherwise invalidate one another. A queue with independently issued refresh calls was rejected for the same reason.

### Classify 401 and 403 before presentation

Only 401 from an access-token-authenticated eligible request starts recovery. A 403 remains an `ApiError` classified for access-denied UI, and other errors preserve the server code, status, details, and response headers needed by callers. The request layer will expose `Retry-After` in normalized error metadata so forms can implement cooldowns. Treating both 401 and 403 as authentication failures was rejected because authorization denial must not rotate credentials or redirect away from useful context.

### Normalize return URLs at the login boundary

Create one helper that accepts only paths beginning with a single `/`, resolves them against the current origin, rejects mismatched origins and authentication-entry destinations, and returns path plus query/hash. Both recovery redirects and login post-success navigation use this helper, defaulting to `/account`. Storing arbitrary `window.location.href` or trusting a raw query parameter was rejected because it enables open redirects and can preserve hostile destinations.

### Model account actions as explicit finite UI states

Forgot/reset/verify/resend/logout-all controls will use explicit idle, submitting, success, token-error, rate-limited, validation-error, access-denied, and API-error states rather than inferring state from one message string. Password reset and verification routes read `token` from the query string under `Suspense`, submit only on deliberate user action for reset and once per token for verification, and never place tokens in logs or persistent storage. This makes duplicate prevention and tests deterministic.

### Update authenticated verification state by identity match

Verification confirmation returns `UserPublic`. `AuthProvider` will expose a narrow user-update operation that accepts the response only when its user id matches the authenticated user; otherwise it displays confirmation success without replacing session identity. Blindly replacing the current user was rejected because a verification link may be opened in a browser authenticated as another account.

### Build routes around reusable auth-flow presentation

Add `/forgot-password`, `/reset-password`, and `/verify-email` App Router pages with focused client components, shared form/status primitives, semantic headings, live regions, and responsive existing Tailwind conventions. The account dashboard hosts verification and logout-all controls because it already receives the authenticated user. A single oversized auth component was rejected because token-driven confirmation and authenticated account actions have different lifecycle and security boundaries.

### Test contracts at request, provider, and flow boundaries

Add frontend tests with mocked fetch/router behavior for neutral recovery, token success/failure, resend cooldown, global logout, one-refresh concurrency, single retry, failed recovery, safe return URLs, and 403 behavior. Source-string assertions alone are insufficient for refresh races; request-level tests must control deferred promises and count refresh calls.

## Risks / Trade-offs

- [Some existing API methods still pass explicit tokens] → Migrate authenticated methods through the shared request option without changing their public behavior, and cover representative existing account calls.
- [A stale request may complete after logout] → Session adapter operations compare the token/session generation that initiated recovery before applying refreshed state or retrying.
- [Client cooldown can differ from server policy] → Treat server 429 and `Retry-After` as authoritative; a short success cooldown is only duplicate-send feedback and does not claim server eligibility.
- [Automatic verification confirmation can double-run in development rendering] → Deduplicate confirmation by token and keep the submit operation idempotent from the component's perspective; surface the backend's consumed-token response if a genuinely separate attempt occurs.
- [Redirecting during shared recovery can produce multiple navigation calls] → Centralize terminal session clearing and redirect selection in the provider, while all waiting requests reject with the same terminal result.

## Migration Plan

1. Add normalized auth payload types, error-header metadata, safe-return utilities, and request-level recovery tests.
2. Add the provider session adapter and single-flight refresh path, then route existing authenticated API calls through it while preserving startup refresh and ordinary logout.
3. Add recovery and verification routes/components, account status/resend/global-logout controls, and focused interaction tests.
4. Run frontend lint, type checking, tests, and production build; manually smoke test mobile and desktop signup/login, recovery links, verification, expired-session recovery, access denial, and logout-all against the existing API.

Rollback removes the new routes and account controls and restores direct authenticated calls. No backend or data migration is required.
