## Context

See `proposal.md` for motivation. The backend already exposes admin product CRUD, archive/restore, variant management, listing management, cart behavior, and supreme-admin authorization. The frontend currently exposes `/admin/products/new`, `/admin/messages`, and `/admin/users`, but it does not provide an admin product index or edit/inventory workspace. The existing model treats products as catalog records and listings as sellable offers; listings currently have price, currency, optional variant, and a coarse status, but no available stock quantity.

## Goals / Non-Goals

**Goals:**

- Add an admin product management route that normal admins and supreme admins can use to see all managed products.
- Let normal admins edit catalog fields and manage variants through the UI using existing admin product APIs.
- Add durable sellable inventory quantity and expose it in admin product/listing responses.
- Require supreme-admin authorization for inventory quantity adjustments and inventory status changes.
- Keep route handlers thin by placing inventory rules in backend services.
- Keep public catalog reads stable while cart/buying availability respects inventory quantity and status.

**Non-Goals:**

- Building checkout, payment capture, fulfillment, or order history.
- Adding warehouse locations, reservations, purchase-order receiving, or audit ledger tables.
- Replacing existing product archive behavior with a broad product status enum.
- Allowing normal admins to change inventory quantity or inventory status.
- Letting the frontend be the only enforcement point for supreme-only controls.

## Decisions

### Store quantity on listings as sellable inventory

Add an available quantity field to listings, for example `available_quantity INTEGER NOT NULL DEFAULT 1 CHECK (available_quantity >= 0)`. Products remain catalog records, product variants remain descriptive size/color/SKU records, and listings remain the concrete sellable offer used by product detail, cart, and admin inventory flows.

Rationale: Existing cart and product detail behavior already use active listings as the buyable object. Quantity belongs with the sellable offer because the same product and variant can theoretically have different prices or availability records.

Alternatives considered:

- Add `stock_quantity` directly to products: simpler UI, but it breaks the existing separation between catalog product and sellable listing and cannot represent variant-specific stock cleanly.
- Add quantity to product variants: better than product-level stock for sizes, but variants do not currently carry price, status, or cart references.
- Create a new inventory table now: cleaner long-term for warehouses and audit history, but larger than this change needs before checkout/order workflows exist.

### Keep product archive separate from inventory status

Continue using product archive metadata for catalog visibility. Use listing inventory status for sellable availability. A product can be active in the catalog while having zero or no active inventory; that means it can be browsed but cannot be carted until inventory becomes available.

Rationale: Archive is a catalog lifecycle action. Inventory status is an availability action. Combining them would make simple stock changes hide product pages unexpectedly.

Alternatives considered:

- Archive products automatically when quantity reaches zero: too surprising and loses product discovery.
- Add a product status enum for active/inactive/draft: useful later, but it overlaps with archive behavior and is not required for the requested quantity/status controls.

### Use supreme-admin dependency for quantity and status mutations

Existing product catalog update, archive/restore, and variant APIs can stay normal-admin actions. New quantity adjustment and inventory status endpoints should require the supreme-admin dependency and re-check authorization server-side.

Rationale: The user requested quantity and status controls with supreme admin. This also matches the current role hierarchy where normal admins operate store surfaces and supreme admins handle more sensitive control.

Alternatives considered:

- Let normal admins adjust quantity: simpler and closer to day-to-day store operations, but it conflicts with the requested supreme-admin control.
- Make product archive/restore supreme-only too: stricter, but it would change existing normal-admin behavior more broadly than requested.

### Add admin product management frontend as a dense operational screen

Add `/admin/products` as the main admin product management page. It should use table/list ergonomics rather than a marketing-style layout: filters for active/archived/inventory state, compact product rows, edit actions, archive/restore actions, variant summaries, and a details/edit panel or route for product fields and inventory rows. Existing `/admin/products/new` should remain available from this page.

Rationale: Admins need to scan and operate repeated records. A dense, predictable management page fits this workflow better than isolated cards.

Alternatives considered:

- Extend `/admin/products/new` into a combined create/edit page only: too cramped and still lacks a product overview.
- Add only backend helpers and no product index UI: does not solve the user's problem of not being able to manage products in the UI.

### Cart and public availability must enforce inventory server-side

Cart add/update and guest cart resolution should treat active listings with `available_quantity > 0` as available, and reject requested quantities above availability. Existing cart rows should remain visible but flagged unavailable or quantity-limited when stock is reduced.

Rationale: Inventory cannot rely on frontend hiding. Existing cart behavior already preserves unavailable rows instead of silently deleting them.

Alternatives considered:

- Auto-trim cart quantities when inventory decreases: convenient but surprising and lossy.
- Ignore quantity until checkout: easier, but it makes the new quantity controls misleading.

## Risks / Trade-offs

- [Quantity races between carts and admin updates] Multiple users can add cart quantities while inventory changes. -> Mitigation: enforce quantity limits in backend cart services now and defer true reservation semantics to checkout/order work.
- [Existing listings need a default quantity] Existing rows have no quantity. -> Mitigation: migration defaults them to `1`, preserving current single-offer behavior.
- [Status names are coarse] Existing listing status only supports `active`, `sold`, and `cancelled`. -> Mitigation: reuse these states for now and document that richer inventory lifecycle states are future work.
- [Supreme-only inventory may slow store operations] Day-to-day admins cannot adjust stock. -> Mitigation: make the UI state explicit and include backend tests for rejected normal-admin mutations so policy is intentional.
- [Product list can become visually busy] Product, variant, and inventory controls can crowd one page. -> Mitigation: use a compact list with expandable details or a focused edit panel rather than nesting large forms in every row.

## Migration Plan

1. Add an Alembic migration after the current head for listing available quantity with non-negative constraints and a default for existing rows.
2. Update SQLAlchemy models, Pydantic schemas, and admin/listing/cart serializers to include inventory quantity where needed.
3. Add supreme-admin-only backend service operations and API routes for inventory quantity adjustments and status changes.
4. Update cart availability logic to enforce inventory quantity and show reduced/unavailable states.
5. Add frontend API helpers and types for managed product listing, product update, archive/restore, variant management, inventory quantity adjustment, and status changes.
6. Add `/admin/products` UI and link existing admin navigation to it, while keeping `/admin/products/new`.
7. Add tests for backend authorization, quantity validation, cart availability, frontend access states, and build/lint.

Rollback should drop the quantity column and remove new inventory routes/UI. Existing products, variants, listings, carts, and product archive metadata remain otherwise intact.
