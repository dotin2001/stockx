## 1. API Contracts and Session Utilities

- [x] 1.1 Add frontend types and API methods for password-reset request/confirm, verification request/confirm, and logout-all using the confirmed backend payloads, and verify request paths, methods, credentials, and response types with focused API-client tests.
- [x] 1.2 Preserve normalized server error metadata including status, error code, details, and `Retry-After`, and verify tests distinguish validation, `invalid_action_token`, 429, 401, 403, and general API failures.
- [x] 1.3 Add a safe internal return-URL normalizer that rejects external, protocol-relative, malformed, and authentication-entry destinations, and verify unit tests cover accepted path/query/hash values and rejected open-redirect cases.

## 2. Coordinated Session Recovery

- [x] 2.1 Introduce the auth session adapter between `AuthProvider` and authenticated API requests, including session-generation protection against applying stale refresh results, and verify provider/request tests cover token and user updates plus logout races.
- [x] 2.2 Implement single-flight refresh for eligible access-token 401 responses and one retry with the refreshed token, and verify deferred concurrent-request tests produce exactly one refresh and at most one retry per request.
- [x] 2.3 Handle terminal recovery failure by clearing local auth state and routing protected journeys to login with a normalized internal return path, and verify tests cover failed refresh, a second 401, public unauthenticated 401, and safe post-login return behavior.
- [x] 2.4 Keep 403 responses out of the refresh path and expose an access-denied presentation state, and verify a focused test receives access denied with zero refresh calls.
- [x] 2.5 Route existing authenticated API operations through the coordinated request path without changing their external behavior, and verify representative account, cart, watchlist, seller, order, checkout, and admin requests still pass their frontend tests.

## 3. Password Recovery Flows

- [x] 3.1 Add the `/forgot-password` route and accessible responsive form with client validation, pending-state duplicate prevention, neutral accepted confirmation, rate-limit cooldown, and general error feedback; verify interaction tests cover each state and login exposes a recovery link.
- [x] 3.2 Add the `/reset-password` token route and accessible new-password form with confirmed length validation, pending protection, success guidance, and no token persistence; verify interaction tests cover success and missing-token behavior.
- [x] 3.3 Map `invalid_action_token` to invalid/expired/already-used recovery guidance while keeping validation and other API errors distinct, and verify tests offer a new reset request and login path for token failure.

## 4. Verification and Global Logout

- [x] 4.1 Show server-backed verified/unverified status in the account dashboard and add resend-verification handling with pending, success-cooldown, 429 `Retry-After`, validation, and API-error states; verify account interaction tests cover verified and unverified users plus resend outcomes.
- [x] 4.2 Add the `/verify-email` token route, deduplicate confirmation per token, and update authenticated user state only when returned identity matches; verify tests cover success, missing/invalid/consumed token guidance, mismatched signed-in identity, and duplicate-render protection.
- [x] 4.3 Add a keyboard-accessible confirmed “Log out all devices” account action that preserves the session on ordinary failure and clears state then redirects on success; verify tests cover cancel, pending duplicate prevention, success, and failure.

## 5. Accessibility and Verification

- [x] 5.1 Consolidate shared auth-flow status presentation with semantic labels, live regions, focus-visible controls, busy/disabled states, and responsive Tailwind layouts, and verify keyboard navigation and mobile-width rendering for every new route and account control.
- [x] 5.2 Run `npm run lint --workspace apps/web`, `npm run typecheck --workspace apps/web`, `npm run test --workspace apps/web`, and `npm run build --workspace apps/web`, resolving all failures and recording any environment-only blocker.
- [x] 5.3 Smoke test against the existing API: neutral password request, successful and failed reset links, verification status/resend/confirmation, one-refresh recovery under concurrent 401s, 403 access denial, safe failed-session return to login, and logout-all on mobile and desktop; verify no backend, device-listing, or unrelated journey changes are included.
