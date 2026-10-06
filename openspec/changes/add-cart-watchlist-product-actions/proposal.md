## Why

The storefront has the backend foundation for carts, watchlists, and listings, but the user-facing flow still stops short of normal marketplace actions. Users need direct controls to add products to cart, buy immediately, manage cart quantities, remove cart items, and manage watched products from their account.

This change keeps checkout UI-first for now so the marketplace can feel usable before introducing orders, payments, inventory locking, or sold-state transitions.

## What Changes

- Add product-detail actions for authenticated users to add an active listing to cart or start a UI-first buy-now flow.
- Show a useful unauthenticated state for add-to-cart and buy-now actions that sends guests to login.
- Add account cart controls to increase quantity, decrease quantity, remove items, and show a checkout button.
- Keep checkout as a UI-first placeholder or disabled action; it does not create orders, payment sessions, charges, or sold listings.
- Add watchlist controls to remove watched products from the account view.
- Reuse existing cart and watchlist mutation APIs where available.

## Capabilities

### New Capabilities
- `marketplace-action-controls`: Product, cart, and watchlist controls for UI-first purchase intent and saved product management.

### Modified Capabilities
- None.

## Impact

- Frontend: product detail action panel, account dashboard cart/watchlist sections, API client methods, TypeScript DTOs, loading/error/empty states.
- Backend: product detail response shape for the lowest active sellable listing, plus tests for product listing availability.
- Database: no schema changes.
- Out of scope: real checkout, payment provider integration, order records, listing reservation, listing sold transitions, shipping, taxes, and inventory settlement.
