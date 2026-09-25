## Why

The project should behave as a store-owned selling website, not a multi-seller marketplace. The current user flow still exposes seller onboarding and user-created listings, which conflicts with the desired model where normal users are buyers and store admins own product/inventory management.

## What Changes

- **BREAKING**: Remove normal-user seller onboarding and seller listing creation from the customer-facing flow.
- Treat all non-admin authenticated users as store customers who can browse, watch products, manage cart contents, start checkout, manage account information, and message the store admin.
- Keep guest users able to browse products/categories/search, add active sellable items to a guest cart, and continue to login/signup before checkout.
- Keep admin-owned catalog/product management as the source of store product creation.
- Keep the current admin model as "normal admin" for this change and explicitly defer "supreme admin" role hierarchy and admin management to a later change.
- Keep checkout as an authentication-gated placeholder/order-intent surface for now; real payments, order fulfillment, and admin order management remain out of scope until requested.
- Add a customer-to-admin messaging capability for authenticated users, with admin-readable messages prepared for a later admin UI.

## Capabilities

### New Capabilities

- `storefront-role-flow`: Defines the store-owned role model, guest/customer shopping behavior, removal of customer seller flows, and deferred admin hierarchy.
- `customer-admin-messaging`: Defines authenticated customer messages to store admins and admin-readable message state.

### Modified Capabilities

None.

## Impact

- Frontend: product detail actions, `/sell` access/navigation, account dashboard seller/listing sections, authenticated customer account surfaces, and a new customer message entry point.
- Backend/API: seller/listing routes must be hidden, disabled, or admin-only for store-owned operation; customer messaging endpoints and schemas are needed.
- Database: seller profile data is no longer part of the active customer model; customer messages need persistence if implemented beyond a frontend placeholder.
- Tests/smoke: update buyer/guest/admin smoke coverage and remove expectations that normal users can register as sellers or create listings.
- OpenSpec: this change supersedes the seller portion of `enable-guest-cart-and-seller-onboarding` while preserving its guest-cart behavior.
