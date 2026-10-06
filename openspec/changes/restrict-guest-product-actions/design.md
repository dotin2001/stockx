## Context

The current Next.js frontend already supports guest add-to-cart from `ProductDetailView` through local guest-cart storage, and the account dashboard supports authenticated cart management. The same frontend still exposes product watchlist controls and account-level customer message-to-admin workflows. The FastAPI backend also has watchlist and customer message routers, services, schemas, docs, and smoke-test coverage.

Existing active OpenSpec changes already define guest cart behavior, store-owned selling flow, product action controls, and customer-admin messaging. This change narrows the customer-facing scope: public browsing and cart remain, while watchlist and customer-to-admin messaging are no longer part of the customer experience.

## Goals / Non-Goals

**Goals:**
- Remove customer-facing watchlist controls from product detail and account experiences.
- Remove customer-facing message-admin forms, message history, and API client calls from the account dashboard.
- Preserve guest cart and authenticated cart behavior, including guest checkout authentication gating.
- Update smoke tests and docs so watchlist and customer messages are no longer required customer shopping coverage.
- Keep implementation compatible with the existing store-owned selling direction.

**Non-Goals:**
- No new payment, order, or fulfillment behavior.
- No replacement support/contact workflow.
- No database migration is required solely to remove customer-facing watchlist/message surfaces.
- No change to admin role hierarchy or admin product/inventory management.

## Decisions

### Remove frontend dependencies before deleting backend surfaces

Update `ProductDetailView` and `AccountDashboard` so customer shopping and cart flows no longer import, call, or render watchlist/message-admin behavior. This directly satisfies the visible customer requirement and prevents frontend runtime failures if backend endpoints are later removed.

Alternative considered: delete backend watchlist and customer message modules first. That creates a wider migration because models, migrations, docs, smoke tests, admin message panels, and API clients all need to move together. Decoupling the customer UI first keeps the change easier to verify.

### Keep cart as the only customer action surface

Product detail should keep Add to Cart and Buy Now. Guests should continue storing cart intent locally; authenticated customers should continue using backend cart endpoints. Unavailable products should explain that no active ask exists without suggesting watchlist follow-up.

Alternative considered: require login before add-to-cart. That conflicts with the explicit guest-shopping scope and the existing guest-cart implementation.

### Simplify account dashboard data loading

The account dashboard should load cart data only for the customer shopping surface. It should remove watchlist and customer message state, mutations, sections, and copy that mentions those features. Admin-only pages can be evaluated separately; this change does not require customer account pages to fetch message data.

Alternative considered: hide sections visually but keep API calls. That would preserve unwanted dependencies and still fail if the backend removes or changes those endpoints.

### Treat backend endpoint removal as optional but consistency-bound

The minimum compatible implementation may leave `/api/v1/watchlist` and `/api/v1/messages` in place while no customer-facing UI or required smoke workflow uses them. If implementation removes them, it must also remove or update router registration, services, schemas, model relationships if appropriate, API docs, smoke tests, and any admin message UI that depends on customer messages.

Alternative considered: mandate backend deletion in the spec. The user's requested behavior is about what non-logged-in/customer users can do in the storefront; backend deletion is more invasive and can be handled when the project is ready to retire those APIs fully.

### Update smoke coverage around cart behavior

Smoke tests should keep verifying service readiness, public catalog/search, auth lifecycle, and cart behavior. The protected marketplace action block should stop creating watchlist items or customer messages and instead assert guest cart resolution plus authenticated cart add/list/remove and duplicate merge behavior.

Alternative considered: remove the protected marketplace smoke block entirely. Keeping cart coverage protects the one customer write path that remains in scope.

## Risks / Trade-offs

- Backend APIs may remain callable even though the customer UI no longer exposes them -> document that the visible customer scope is the primary requirement, and only remove backend endpoints if the implementation updates all dependent docs/tests/UI consistently.
- Existing admin message pages may become orphaned if customer messages are later removed from the backend -> leave admin message removal out of the minimum change unless endpoint deletion is chosen.
- Account dashboard may become sparse after removing watchlist and messages -> tighten account copy around cart and checkout state rather than adding unrelated features.
- Active OpenSpec changes still mention watchlist and customer-admin messaging -> this change explicitly supersedes those customer-facing portions while preserving guest cart behavior.

## Migration Plan

1. Update frontend customer surfaces to remove watchlist and message-admin UI and API calls while preserving product browsing, guest cart, authenticated cart, and checkout placeholder behavior.
2. Update API smoke tests to remove watchlist and customer-message steps and verify guest/authenticated cart behavior instead.
3. Update frontend/backend documentation that claims customer watchlist or message-admin support.
4. If backend endpoint removal is selected during implementation, remove the full dependent route/service/schema/test/doc chain in the same change and verify no remaining frontend/admin code imports the removed client methods.
5. Rollback by restoring the previous frontend sections and smoke expectations from version control if the reduced customer scope is rejected.
