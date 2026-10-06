## Why

The storefront should keep unauthenticated shoppers in a simple shopping path: browse products and add sellable items to cart without requiring login. Watchlist and customer-to-admin messaging add account/support surfaces that are no longer desired for the current customer experience.

## What Changes

- Keep public product, category, search, and home browsing available to guests.
- Keep guest add-to-cart behavior for active sellable listings, including buy-now intent flowing through cart/checkout gating.
- Remove product-page watchlist actions, including logged-out "Log in to Watch" prompts and logged-in "Add to Watchlist" controls.
- Remove customer-facing message-to-admin surfaces from the account experience.
- Stop requiring customer watchlist and customer message flows in API smoke coverage and customer-facing frontend behavior.
- Preserve admin-only management surfaces where they are still needed for store operation; this change only removes customer-facing watchlist and customer-to-admin message behavior.

## Capabilities

### New Capabilities
- `customer-shopping-scope`: Defines the reduced customer shopping scope where guests and authenticated customers can browse products and use cart actions, while watchlist and message-admin customer actions are unavailable.

### Modified Capabilities
- `api-smoke-testing`: Update smoke-test expectations so customer watchlist and customer message flows are no longer required protected marketplace smoke coverage.

## Impact

- Frontend: `ProductDetailView`, `AccountDashboard`, customer-facing API client usage, route copy, and any account/product empty states that mention watchlist or message-admin actions.
- Backend/API: watchlist and customer message endpoints may remain temporarily for compatibility, but customer-facing flows and required smoke coverage should stop depending on them; if removed, routers, services, schemas, docs, and tests must be updated consistently.
- Tests/smoke: update API smoke tests and frontend checks to verify browse/add-to-cart behavior without watchlist or customer message steps.
- Documentation/OpenSpec: this change supersedes the customer watchlist and customer-admin messaging portions of earlier active changes while preserving guest-cart behavior.
