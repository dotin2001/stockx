## 1. Backend Store-Owned Role Enforcement

- [x] 1.1 Update listing creation authorization so authenticated non-admin customers cannot create user-owned listings, and verify API tests reject customer `POST /api/v1/listings` without creating a listing.
- [x] 1.2 Decide whether admin/seed-created listings remain readable through existing catalog/cart flows, and verify product detail and cart APIs still resolve active sellable items.
- [x] 1.3 Disable active seller profile mutation for normal customers or remove it from the routed API surface, and verify unauthenticated and non-admin requests cannot create active seller eligibility.
- [x] 1.4 Update auth/current-user response handling if needed so legacy `is_seller` state does not drive customer UI, and verify existing login, refresh, and me tests still pass.

## 2. Customer Admin Messaging Backend

- [x] 2.1 Add a deterministic Alembic migration and SQLAlchemy model for customer admin messages with sender, subject/context, body, read state, and timestamps, and verify migration upgrade applies.
- [x] 2.2 Add Pydantic schemas for customer message create/read/list/read-state operations, and verify validation rejects blank or oversized message payloads.
- [x] 2.3 Add authenticated customer message create and own-message list/detail service behavior, and verify customers only see their own messages.
- [x] 2.4 Add admin-protected customer message list/detail/mark-read behavior, and verify admins can read messages while guests and non-admin users receive authorization errors.
- [x] 2.5 Include customer message routes in the versioned API router, and verify route paths match the frontend API client plan.

## 3. Frontend Customer Flow Pivot

- [x] 3.1 Remove seller navigation and product-detail seller actions from guest and authenticated customer UI, and verify product detail still supports add-to-cart and authenticated watchlist actions.
- [x] 3.2 Replace or disable `/sell` customer-facing seller onboarding with store-owned messaging or informational state, and verify guests and customers do not see seller registration or listing creation controls.
- [x] 3.3 Update the account dashboard to focus on customer identity, watchlist, cart, checkout state, and message-admin actions, and verify listing/seller profile sections are absent for normal users.
- [x] 3.4 Keep `/admin/products/new` and admin-only navigation available for admins, and verify non-admin users cannot access catalog product creation controls.
- [x] 3.5 Update frontend type/API helpers for customer messages, and verify TypeScript accepts the new request and response shapes.

## 4. Frontend Messaging Experience

- [x] 4.1 Add an authenticated customer message-admin form from the account or support surface, and verify required labels, validation errors, loading state, and success state render correctly.
- [x] 4.2 Add an admin-protected message list/read-state UI or minimal admin route if in scope for this change, and verify non-admin users see an admin-required state.
- [x] 4.3 Preserve guest login gating for messaging, and verify a guest attempting to message the store is directed to login or signup without losing customer context.

## 5. Documentation and Existing Plan Reconciliation

- [x] 5.1 Update project README or app docs to describe the store-owned model, guest/customer/admin roles, and deferred supreme-admin behavior, and verify docs no longer present normal users as sellers.
- [x] 5.2 Update or supersede smoke/test expectations from seller onboarding so they match the store-owned flow, and verify no test still expects normal users to become sellers.
- [x] 5.3 Note that this change supersedes the seller portion of `enable-guest-cart-and-seller-onboarding` while preserving guest cart behavior, and verify OpenSpec validation still passes.

## 6. Verification

- [x] 6.1 Run backend tests with `cd apps/api && ./.venv/bin/pytest` and verify all tests pass.
- [x] 6.2 Run frontend checks with `npm run web:typecheck`, `npm run web:lint`, and `npm run web:build`, and verify all pass.
- [x] 6.3 Run focused smoke checks for guest browse/cart/login checkout gate, authenticated watchlist/cart/message-admin, disabled seller flow, and admin product creation access.
- [x] 6.4 Run `openspec validate pivot-to-store-selling-flow --strict` and verify the change is valid.
