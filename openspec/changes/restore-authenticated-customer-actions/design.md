## Context

See `proposal.md` for motivation. The current working tree reflects `restrict-guest-product-actions`, which removed customer-facing watchlist and customer message behavior from the Next.js frontend and API client. The FastAPI backend still contains protected watchlist routes and protected customer message routes, plus admin message routes and database models. Earlier active specs already define authenticated watchlist and customer-admin messaging behavior.

The correction is behavioral and user-facing: guests should not see or use watchlist/message-admin actions, while authenticated customers should keep those account features.

## Goals / Non-Goals

**Goals:**
- Restore authenticated customer watchlist UI, API client methods, DTO types, and account management.
- Restore authenticated customer message-admin UI, API client methods, DTO types, and account message history.
- Preserve guest browsing, guest add-to-cart, and checkout authentication gating.
- Keep guest product pages free of "Log in to Watch" prompts.
- Restore smoke/docs expectations for authenticated customer watchlist and messaging.

**Non-Goals:**
- No database schema changes.
- No new support workflow beyond restoring existing customer-to-admin messages.
- No public/guest watchlist or message-admin endpoint.
- No change to admin message management beyond keeping it compatible with restored customer messages.

## Decisions

### Reuse existing backend routes and services

Keep `/api/v1/watchlist`, `/api/v1/messages`, and `/api/v1/admin/messages` as the API contract. They already enforce authentication and ownership/admin access, so implementation should restore frontend clients and UI rather than rebuilding backend behavior.

Alternative considered: create new replacement endpoints. That would add churn without changing the desired behavior.

### Gate by authenticated UI state, not guest prompts

Product detail should render `Add to Watchlist` only when the shopper is authenticated. Guests should still be able to browse and cart, but should not see a `Log in to Watch` prompt. This matches the requested scope: remove the actions from guests, not from authenticated users.

Alternative considered: show login prompts for watchlist/message-admin. The user explicitly asked to remove them from guests, so guest prompts for these features should stay absent.

### Restore account dashboard sections for authenticated customers

The account dashboard should again load cart, watchlist, and customer messages for authenticated customers. Watchlist removal and message submission should use the existing protected APIs and keep cart behavior unchanged.

Alternative considered: split watchlist/messages into separate routes. That is not necessary for this correction and would expand the UI scope.

### Restore smoke coverage for authenticated account actions

Running-service smoke should cover guest cart, authenticated cart, authenticated watchlist, and authenticated customer messages. This protects the exact split between guest browse/cart and authenticated account actions.

Alternative considered: leave watchlist/message coverage only in unit tests. Smoke coverage is valuable here because these flows depend on auth headers, seeded catalog data, and real route registration.

## Risks / Trade-offs

- The completed `restrict-guest-product-actions` change contains artifacts that say authenticated users lose watchlist/messages -> This change should be applied before archiving, and its artifacts should be considered the correcting scope.
- Restoring account dashboard sections increases the page density again -> Keep layout close to the pre-removal dashboard to minimize design churn.
- Guest behavior can regress if restoring watchlist accidentally reintroduces "Log in to Watch" -> Add an explicit implementation task and search check for guest watch prompts.

## Migration Plan

1. Restore frontend DTOs and API client methods for authenticated customer watchlist and messages.
2. Restore product detail authenticated-only watchlist behavior without adding guest watch prompts.
3. Restore account dashboard watchlist and message-admin sections while keeping cart behavior intact.
4. Update docs and smoke tests to describe/verify guest cart plus authenticated cart/watchlist/messages.
5. Run frontend typecheck/lint/build, backend tests, and OpenSpec validation.
