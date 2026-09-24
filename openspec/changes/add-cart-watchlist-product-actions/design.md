## Context

The Next.js frontend already has `/product/[slug]`, `/account`, and `/sell` surfaces. Product detail can watch or sell a product, while account currently displays listings, watchlist, and cart in one dashboard. The frontend API client has methods to add cart items, list cart items, list watchlist items, add watchlist items, and remove watchlist items.

The FastAPI backend already supports cart add, cart quantity update, cart item removal, and watchlist item removal. Product detail responses expose catalog product information, but they do not expose an active listing id that the frontend can pass to cart add.

## Goals / Non-Goals

**Goals:**

- Let product detail Add to Cart and Buy Now operate on the lowest active sellable listing for the product.
- Add user-facing cart quantity and removal controls using existing cart mutation behavior.
- Add user-facing watchlist removal controls using existing watchlist removal behavior.
- Keep purchase-intent UI protected by authenticated API requests.
- Keep the implementation consistent with the current `/account` dashboard instead of introducing a large checkout area.

**Non-Goals:**

- No real checkout, order model, payment provider integration, listing reservation, listing sold transition, taxes, shipping, or fulfillment.
- No multi-seller ask table or bid/ask market-depth view.
- No guest cart persistence.
- No separate seller account type.
- No watchlist quantity or desired-quantity tracking.

## Decisions

### Expose a lowest active listing on product detail

Product detail should expose a minimal active listing summary, such as `lowest_active_listing`, containing the listing id, price, currency, status, and enough availability data for frontend actions. The frontend uses that listing id for Add to Cart and Buy Now.

Rationale: the current cart API requires a listing id, and product detail currently only has product ids and display-level lowest ask data. Returning the lowest active listing keeps product detail to one primary buy action without designing a full listing marketplace table.

Alternative considered: create a standalone product listings endpoint and render all active listings. That is more flexible, but it expands the UX beyond this UI-first change.

### Keep checkout as an account-cart placeholder

The checkout button should live in the account cart section for now. Buy Now should add the item to cart and route to the account/cart context, optionally with a query string or local state that displays a checkout placeholder message.

Rationale: the app has no `/cart` or `/checkout` route today, and this change is intentionally UI-first. Keeping it inside `/account` avoids creating a checkout route that looks more complete than it is.

Alternative considered: add a new `/checkout` route. That may be useful later, but it could imply an order/payment capability this change explicitly excludes.

### Use existing cart update and remove APIs

Cart increase/decrease/remove controls should call the existing backend cart endpoints. Decrease should update quantity only when the current quantity is greater than one; removal remains a distinct delete action.

Rationale: the backend already owns cart ownership, availability, quantity validation, and removal behavior. The frontend should not create duplicate mutation semantics.

Alternative considered: treat decrement from one as remove. That is compact, but it makes a quantity control delete an item and can surprise users.

### Pessimistic mutation refresh for controls

Cart and watchlist controls should show disabled/loading states during mutation and update the local dashboard state from API responses. If a mutation fails, preserve the prior item state and show the stable API error message.

Rationale: the current app already favors simple client state and backend error messages. Pessimistic updates avoid quantity drift while the backend remains the source of truth.

Alternative considered: optimistic updates. That would feel faster, but requires careful rollback and is not necessary for the current scale.

## Risks / Trade-offs

- Lowest active listing can be missing for seeded products -> Product detail must show unavailable purchase actions while still supporting watch/sell paths.
- Product display lowest ask can differ from active listing data -> Add/Buy UI should prefer the actionable active listing price, while existing display data can remain as catalog metadata until a later pricing reconciliation.
- Account dashboard may become dense -> Keep controls compact and preserve empty/loading/error states.
- Checkout placeholder may frustrate users -> Copy must clearly indicate checkout is not available yet and avoid implying payment completion.

## Migration Plan

1. Extend product detail API output with the lowest active listing summary.
2. Update frontend DTOs/API helpers and account/product UI.
3. Verify backend tests, frontend typecheck/lint/build, and auth-protected UI smoke flows.

Rollback: remove frontend usage of the product detail listing field and restore the previous product/action UI.
