## Context

See `proposal.md` for motivation. The backend currently exposes public catalog endpoints under `/api/v1` for categories, products, product details, and search. Authenticated users can create listings and manage watchlists. The database already has `users.is_admin`, `products`, `product_variants`, `listings`, and `watchlist_items`, but there is no admin authorization dependency, admin product router, cart table, or product archival state.

Listings are the current sellable objects because they carry seller ownership, price, currency, status, and optional variant. Products are catalog records. Cart behavior should therefore reference listings rather than products so the cart points at a concrete offer.

## Goals / Non-Goals

**Goals:**

- Add admin-only product and variant management using the existing `users.is_admin` marker.
- Add product archival state so admin removal does not break existing listing, watchlist, cart, or future order references.
- Add authenticated cart persistence scoped by user and listing.
- Preserve the existing public catalog response shapes for active products.
- Keep route handlers thin and put business rules in service modules.

**Non-Goals:**

- Checkout, payment, order creation, inventory reservation, and tax/shipping calculations.
- Production image upload or asset storage.
- Fine-grained roles beyond the existing boolean `is_admin`.
- Guest carts or anonymous cart persistence.
- Hard deletion of products that may be referenced by marketplace records.

## Decisions

### 1. Use admin routes under `/api/v1/admin`

Add a new admin router mounted from the versioned API router, with routes such as:

```text
GET    /api/v1/admin/products
POST   /api/v1/admin/products
PATCH  /api/v1/admin/products/{id}
POST   /api/v1/admin/products/{id}/archive
POST   /api/v1/admin/products/{id}/restore
POST   /api/v1/admin/products/{id}/variants
PATCH  /api/v1/admin/product-variants/{id}
DELETE /api/v1/admin/product-variants/{id}
```

Rationale: A separate admin namespace makes protected management actions obvious and keeps public catalog routes stable. It also avoids overloading `/api/v1/products` with mixed public/admin behavior.

Alternatives considered:

- Add write methods beside public catalog routes: smaller route count, but easier to misread and harder to protect consistently.
- Create separate service or app for admin: unnecessary for the current foundation.

### 2. Add an admin dependency based on `users.is_admin`

Add a `CurrentAdminUser` dependency that reuses current bearer-token authentication and rejects non-admin users with a stable authorization error.

Rationale: The database foundation already chose `users.is_admin BOOLEAN NOT NULL DEFAULT FALSE`, so the first admin workflow should use it directly.

Alternatives considered:

- Introduce roles or permissions tables now: more flexible but explicitly beyond the current project direction.
- Trust frontend admin navigation: unacceptable because protected actions must be enforced in the backend.

### 3. Archive products instead of hard deleting them

Add nullable archive metadata to `products`, likely:

```text
archived_at TIMESTAMPTZ NULL
archived_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL
```

Public catalog queries filter `archived_at IS NULL`. Admin managed queries can include active and archived products with a filter. Product detail for archived products returns not-found on public routes.

Rationale: Products already have references from listings and watchlists, and carts will add another reference. Archive preserves relational integrity and future order/history options.

Alternatives considered:

- Hard delete products: simple but conflicts with references and marketplace history.
- Add a text product status: more expressive, but archive/active is enough for this step.

### 4. Keep variant removal physical for now, but product deletion archival

Product variants may be deleted from future product detail responses. Existing listings already allow `product_variant_id` to become null through `ON DELETE SET NULL`, so removing a variant should not remove the parent product or listing.

Rationale: Variants are optional product attributes and the current schema already models variant deletion as safe for listings.

Alternative considered:

- Archive variants too: more history-preserving, but adds complexity before there is checkout or order history.

### 5. Store cart items as user-owned listing references

Add a `cart_items` table:

```text
id UUID PRIMARY KEY
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE
quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0)
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (user_id, listing_id)
```

Cart add validates that the listing exists, is `active`, and belongs to a non-archived product. If the same user adds the same listing again, the service updates the existing row instead of inserting a duplicate.

Rationale: A cart should reference the actual sellable offer with price/status rather than only the catalog product.

Alternatives considered:

- Store `product_id` in cart items: easier for product detail pages, but loses concrete seller/price/status information.
- Store cart only client-side: simpler now, but prevents backend ownership checks and future checkout continuity.

### 6. Return availability in cart responses

Cart reads should include enough product/listing summary data for display plus an availability indicator derived from listing status and product archive state. Existing cart rows remain visible when a listing later becomes unavailable, but the response marks them unavailable for purchase.

Rationale: Users should understand why an item cannot move forward to checkout later without silently losing cart contents.

Alternatives considered:

- Auto-remove unavailable items: tidy but surprising and lossy.
- Reject cart view when any item is unavailable: poor UX and unnecessary.

### 7. Keep public product response compatibility

Public catalog response shapes should remain compatible for active products. If `archived_at` is added to the model, it does not need to appear in public product responses. Admin product responses can include archive metadata.

Rationale: Existing frontend work can keep consuming public catalog endpoints without learning admin-only fields.

Alternatives considered:

- Add archive fields to every public response: unnecessary exposure of management state.

## Risks / Trade-offs

- [Concurrent duplicate cart add] Two requests can race against the unique `(user_id, listing_id)` constraint. -> Mitigation: catch database integrity errors and translate them into a deterministic update or conflict-safe retry behavior.
- [Admin product archive hides products unexpectedly] Existing public clients may see fewer products when admins archive catalog rows. -> Mitigation: document archive behavior and cover public list/search/detail filtering in tests.
- [Listing status is still coarse] Current listings only support `active`, `sold`, and `cancelled`. -> Mitigation: treat only `active` as cartable and defer richer inventory/reservation states to checkout/order work.
- [Cart quantity may not match marketplace inventory] Listings do not currently store available quantity. -> Mitigation: allow quantity for frontend ergonomics, but keep checkout/inventory validation out of this change.
- [Product variant deletion loses display detail on existing listings] Existing listing variant references can become null. -> Mitigation: accept this for now because checkout/order snapshots are not in scope; revisit when order history exists.

## Migration Plan

1. Add a new Alembic migration for product archive columns and `cart_items`.
2. Update SQLAlchemy models and relationships for archive metadata and cart items.
3. Backfill is not needed because existing products remain active with `archived_at = NULL`.
4. Add services, schemas, routers, and tests.
5. Apply migration locally, run backend tests, seed data, and smoke relevant public catalog/cart/admin flows.

Rollback: downgrade drops `cart_items` and removes product archive columns. Because checkout/order history is out of scope, rollback only loses cart contents and archive markers introduced by this change.
