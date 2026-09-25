## 1. Database and Models

- [x] 1.1 Add a `seller_profiles` Alembic migration with one profile per user, required phone/address fields, timestamps, and a unique `user_id`, and verify `alembic upgrade head` applies successfully.
- [x] 1.2 Add SQLAlchemy seller profile model and user relationship, and verify model metadata includes the `seller_profiles` table in database foundation tests.
- [x] 1.3 Add Pydantic seller profile and seller/account response schemas, and verify validation rejects missing phone/address fields.

## 2. Backend Seller Onboarding

- [x] 2.1 Add seller profile service methods for owner-only get/upsert behavior, and verify unit/API tests cover create, update/idempotent upsert, and unauthenticated rejection.
- [x] 2.2 Add `/api/v1/seller/profile` routes and include them in the versioned router, and verify authenticated users can register as sellers through the API.
- [x] 2.3 Extend auth/current-user responses with derived `is_seller` state, and verify register, login, refresh, and me tests expose the expected seller flag.
- [x] 2.4 Gate listing creation on seller registration in the backend service, and verify non-sellers receive a seller-required error while registered sellers can create listings.

## 3. Backend Guest Cart

- [x] 3.1 Add request/response schemas for guest cart item resolution and authenticated cart merge, and verify invalid quantities and malformed listing ids fail validation.
- [x] 3.2 Add a public guest cart resolution endpoint that returns product/listing display data plus availability without persistence, and verify active, inactive, missing, and archived-product listings are handled.
- [x] 3.3 Add an authenticated cart merge endpoint that merges guest listing quantities into the user cart and reports skipped unavailable items, and verify duplicate listing quantities merge into one user cart row.
- [x] 3.4 Update backend tests and smoke coverage for guest cart resolution, login/signup merge behavior, and checkout-placeholder preservation, and verify `pytest` passes.

## 4. Frontend Guest Cart and Checkout Gate

- [x] 4.1 Add a guest cart client store using a versioned localStorage key with add, update, remove, clear, and total helpers, and verify frontend type checking passes.
- [x] 4.2 Update product detail Add to Cart and Buy Now actions so guests can add active listings locally and Buy Now routes to the auth-gated checkout path, and verify guest and authenticated UI states render correctly.
- [x] 4.3 Add guest cart display/management to the account/cart experience or shared cart panel while keeping `/account` protected for account-only data, and verify guests can view, update, and remove local cart items.
- [x] 4.4 Update login/signup flow to merge guest cart items after successful authentication and clear local cart only after merge succeeds, and verify skipped unavailable items can be surfaced to the user.
- [x] 4.5 Keep checkout placeholder behavior after authentication, and verify checkout does not create orders, payment sessions, charges, or sold listings.

## 5. Frontend Seller Onboarding

- [x] 5.1 Add API client/types for seller profile read/upsert and updated user seller state, and verify frontend type checking passes.
- [x] 5.2 Update the sell page so authenticated non-sellers see seller registration fields for phone/address before the listing form, and verify successful registration reveals listing creation.
- [x] 5.3 Update the listing creation UI to handle seller-required backend errors gracefully, and verify the form cannot create listings as a non-seller.
- [x] 5.4 Update the account dashboard to show seller status/profile context alongside listings, watchlist, cart, and checkout placeholder, and verify empty/error/loading states remain usable.

## 6. Verification

- [x] 6.1 Run backend tests with `cd apps/api && ./.venv/bin/pytest` and verify all tests pass.
- [x] 6.2 Run frontend checks with `npm run web:typecheck`, `npm run web:lint`, and `npm run web:build`, and verify all pass.
- [x] 6.3 Run `openspec validate enable-guest-cart-and-seller-onboarding --type change --strict` and verify the change is valid.
- [ ] 6.4 Perform browser smoke checks for guest add-to-cart, checkout auth gate, login/signup cart merge, seller registration, seller listing creation, and account dashboard listings/watch/cart views.
