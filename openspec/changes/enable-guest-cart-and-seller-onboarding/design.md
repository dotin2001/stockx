## Context

The current cart API is authenticated and persists `cart_items` by `user_id` and `listing_id`. Product detail pages can expose a `lowest_active_listing`, but guests are currently sent to login before cart mutation. The account dashboard already groups listings, watchlist, and cart, and checkout is intentionally a placeholder. The sell page is authenticated, but any authenticated user can create a listing immediately. Users currently have `is_admin`; there is no seller profile or seller eligibility state.

## Goals / Non-Goals

**Goals:**
- Let guests build a cart before login without weakening backend availability checks.
- Preserve and merge guest cart intent after login/signup.
- Keep checkout protected and placeholder-only.
- Add a seller profile gate before listing creation.
- Keep seller state separate from admin access.

**Non-Goals:**
- Real checkout, payments, order creation, fulfillment, or listing sale transitions.
- Seller identity verification, KYC, payout onboarding, tax forms, or moderation review.
- Seller-created catalog product records; sellers create listings for existing products only.
- Cross-device guest cart persistence.

## Decisions

### Use localStorage for guest cart storage

Guest cart state should live in the frontend under a versioned localStorage key containing `listing_id` and `quantity`. The frontend can add to cart from product detail using the active listing id already returned by product detail.

Alternative considered: server-side anonymous carts with a guest cart cookie. This would support cross-tab/server ownership more cleanly, but adds session lifecycle, cleanup, and cookie handling before checkout exists. LocalStorage is enough for this UI-first phase.

### Add backend guest cart resolution and authenticated merge endpoints

Add a public cart resolution endpoint that accepts guest cart items and returns cart-display data plus availability state without persisting anything. Add an authenticated merge endpoint that accepts guest items after login/signup, validates each active listing, merges quantities into the user's cart, and returns skipped unavailable items.

This keeps the backend authoritative for listing availability while avoiding a persisted guest-cart table. The existing authenticated cart endpoints continue to own account cart CRUD.

### Merge after auth from the frontend

After `login` or `signup` succeeds, the auth context should detect guest cart contents, call the merge endpoint with the new access token, refresh or return the merged cart state, and clear the local guest cart only after the merge completes. If the merge partially skips unavailable items, the UI can show a concise notice.

Alternative considered: pass guest cart contents directly to `/auth/login` and `/auth/register`. Keeping merge separate avoids coupling auth request schemas to cart behavior and lets users log in normally from other screens.

### Add a seller profile table

Create a `seller_profiles` table keyed one-to-one by `user_id`, with phone number and structured address fields. Treat the existence of a seller profile as seller eligibility. Expose a derived `is_seller` field in current-user/account responses and expose owner-only seller profile read/upsert endpoints.

Alternative considered: add seller columns directly to `users`. A separate table keeps user identity, admin access, and seller contact data separate, and it avoids introducing a text role/access-level column.

### Gate listing creation in the backend

The listing creation service must require a seller profile before creating listings. The frontend sell page should guide non-seller authenticated users through seller registration before rendering the listing form, but backend authorization remains the enforcement point.

## Risks / Trade-offs

- Guest cart in localStorage can be cleared by browser settings or unavailable across devices -> acceptable before real checkout; account cart becomes durable after login/signup merge.
- Listing availability may change between add-to-cart and merge -> resolve/merge endpoints re-check status and report skipped items.
- Quantity merge can surprise users if they already had the same listing in their account cart -> account cart should merge duplicate listing quantities and show the updated total.
- Seller contact data increases privacy sensitivity -> keep profile owner-only and do not expose seller phone/address in public listing responses.
- Product detail currently surfaces only the lowest active listing -> guest add-to-cart remains tied to that listing until a richer listing/variant selector exists.

## Migration Plan

1. Add a migration for `seller_profiles` with a unique `user_id` foreign key and required contact/address fields.
2. Add seller profile model, schema, service, and API router.
3. Extend current-user/auth response shapes with `is_seller` and any owner-only seller profile shape needed by the account/sell UI.
4. Add cart guest resolution and authenticated merge behavior without changing existing account cart persistence.
5. Update frontend guest cart state, auth merge behavior, account dashboard messaging, and sell-page seller gate.
6. Rollback by removing the new routes/UI and downgrading the migration before any production seller profiles depend on it.
