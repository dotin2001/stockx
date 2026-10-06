## Why

The previous guest-action restriction was too broad: it removed watchlist and message-admin behavior from authenticated customers, even though the intended rule is only that guests should not use those account actions. Authenticated customers should keep watchlist and store-admin messaging while guests can browse and add to cart.

## What Changes

- Restore authenticated customer watchlist behavior on product detail and account surfaces.
- Restore authenticated customer message-to-admin behavior on the account surface.
- Keep guests able to browse public products and add active sellable items to a guest cart.
- Keep guest watchlist and message-admin actions unavailable: no "Log in to Watch" or guest message-admin call-to-action is required.
- Restore customer-facing API client methods/types for authenticated watchlist and customer messages.
- Update smoke tests and docs so authenticated watchlist/message flows are required, while guest behavior remains browse/cart-only.

## Capabilities

### New Capabilities
- `authenticated-customer-actions`: Defines the corrected customer action split: guests can browse/cart, authenticated customers can additionally use watchlist and message-admin workflows.

### Modified Capabilities
- `api-smoke-testing`: Restore running-service smoke expectations for authenticated watchlist and customer message behavior alongside guest/authenticated cart coverage.

## Impact

- Frontend: `ProductDetailView`, `AccountDashboard`, customer-facing API client methods, shared DTO types, `/sell`/footer/protected-gate copy, and README route/data-contract descriptions.
- Backend/API: existing `/api/v1/watchlist` and `/api/v1/messages` routes remain protected authenticated customer APIs; admin message routes remain unchanged.
- Tests/smoke: API smoke should verify guest cart, authenticated cart, authenticated watchlist, and authenticated customer message flows.
- OpenSpec: this change corrects the over-broad scope of `restrict-guest-product-actions` and should be applied before archiving that behavior.
