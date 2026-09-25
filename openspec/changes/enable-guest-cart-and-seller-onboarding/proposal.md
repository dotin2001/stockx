## Why

Guests should be able to shop naturally before they commit to an account, while checkout remains protected until login or signup. Selling also needs a clear onboarding gate so authenticated users provide seller contact details before they can publish marketplace listings.

## What Changes

- Allow guests to view and add active product listings to a cart before authentication.
- Gate checkout behind login/signup, preserving the guest cart so it can become the authenticated account cart after the user signs in.
- Keep the account dashboard centered on listings, watchlist, cart, and a checkout placeholder until real checkout is built.
- Add seller registration for authenticated users, collecting phone number and address details.
- Require seller registration before users can create seller listings.
- Treat "add product" in this change as creating a seller listing for an existing catalog product; seller-created catalog product records remain out of scope.
- No payment, order, fulfillment, or seller verification workflow is introduced in this change.

## Capabilities

### New Capabilities
- `guest-cart`: Guest cart behavior, authentication-gated checkout, and cart carryover into the account cart after login/signup.
- `seller-onboarding`: Seller registration requirements and seller-gated listing creation.

### Modified Capabilities

None.

## Impact

- Frontend: product detail purchase actions, guest cart state, login/signup redirects, account dashboard cart/listing/watch sections, and sell page seller-onboarding gate.
- Backend/API: cart endpoints or merge flow for guest-to-user cart persistence; seller registration/profile endpoints; listing creation authorization.
- Database: seller profile/contact fields or table, plus any cart/session persistence needed if guest cart is server-backed.
- Tests: backend API coverage for guest cart/merge/seller gate and frontend type/lint/build checks for the updated flows.
