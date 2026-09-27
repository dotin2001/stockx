## Context

See `proposal.md` for motivation. Product management currently serializes `inventory_items` directly from a product's listing rows, and the admin panel renders a text-only empty state when that array is empty. Existing listing creation is available through `/api/v1/listings` for admin users, but that route does not accept initial `available_quantity` or `status` and is not scoped to supreme-admin inventory management.

## Goals / Non-Goals

**Goals:**

- Keep listings as the sellable inventory record rather than adding product-level stock.
- Let supreme admins create the first listing for a product from `/admin/products`.
- Support creating additional listings for a base product or one of its variants.
- Let the create flow set price, currency, initial available quantity, and initial status in one request.
- Preserve server-side authorization and validation for inventory-sensitive behavior.
- Refresh the existing admin product list/detail data after creation instead of duplicating summary calculations on the frontend.

**Non-Goals:**

- Adding warehouse, reservation, order, or audit-ledger inventory models.
- Changing product archive semantics or hiding products automatically when they have no listings.
- Replacing the existing normal-admin listing route used outside product management.
- Adding checkout or fulfillment behavior.

## Decisions

### Add a supreme-admin admin listing creation endpoint

Add a new admin-scoped endpoint such as `POST /api/v1/admin/products/{product_id}/listings` that requires the supreme-admin dependency. The request should include optional `product_variant_id`, `price_cents`, `currency`, `available_quantity`, and `status`; the response can return the created listing using the existing management listing shape.

Rationale: the existing `POST /api/v1/listings` route is normal-admin accessible and creates only active listings with the model default quantity. The product-management inventory flow is explicitly sensitive because it sets sellable quantity and status.

Alternatives considered:

- Extend `POST /api/v1/listings` with optional quantity/status fields and make only those fields supreme-only: this creates mixed authorization inside one route and makes frontend behavior less obvious.
- Create the listing through existing route and immediately call quantity/status mutation endpoints: this adds partial-success risk and creates awkward handling for initial zero quantity or unavailable status.

### Put creation rules in listing services

Add a service function for managed listing creation that checks supreme-admin authorization, loads the product, rejects archived products, validates the variant belongs to the product, validates allowed status, and persists the initial quantity and status.

Rationale: route handlers should stay thin, and the same validation patterns already live in listing/admin product services.

Alternatives considered:

- Put validation in the route: quicker but harder to test and inconsistent with existing service boundaries.
- Put creation in admin product services: product loading belongs there today, but listing lifecycle rules already live in listing services.

### Reuse product list reload for frontend consistency

After successful creation, the admin panel should reload managed products using the existing `reloadAfterMutation` path. The UI should not try to manually recalculate `inventory_summary` or splice a partial listing into `inventory_items`.

Rationale: backend serialization already defines the inventory summary, lowest active price, active listing counts, and sorted listing rows. Reloading keeps the product row and selected detail panel in sync.

Alternatives considered:

- Optimistically update local state from the created listing response: faster, but it duplicates summary logic and risks drift.

### Render creation form in the inventory section

For supreme admins, the inventory section should show a compact create-listing form whether `inventory_items` is empty or not. For products with no listings, the empty state should become actionable instead of only saying "No sellable listings yet." For normal admins, keep a restricted message rather than rendering disabled sensitive controls.

Rationale: the user's immediate problem is the empty-state dead end. Showing the same creation control in both empty and non-empty states also supports additional variant listings.

Alternatives considered:

- Put listing creation only on a separate listings page: preserves separation but forces admins away from the product they are editing.
- Automatically create a listing when a product is created: useful later, but it does not solve existing zero-listing products and removes the admin's ability to choose initial status or quantity intentionally.

## Risks / Trade-offs

- [Multiple ways to create listings] Existing `/listings` and new admin product listing creation can overlap. -> Mitigation: keep the new route supreme-admin-only and focused on inventory fields; leave the old route behavior unchanged.
- [Duplicate listings for the same variant] The model currently allows multiple listing rows per product or variant. -> Mitigation: allow duplicates for now because listings represent sellable offers; use clear UI labels so admins see existing rows before adding another.
- [Partial frontend refresh failure] Creation can succeed while reload fails. -> Mitigation: show the created success notice only after reload when possible, and show a recoverable error that lets the admin retry loading.
- [Archived product handling] Admins may try to create inventory for archived products. -> Mitigation: reject on the backend and surface the conflict in the inventory panel.

## Migration Plan

1. Add request schema for admin listing creation with price, currency, optional variant, available quantity, and status.
2. Add a supreme-admin admin route for product-scoped listing creation.
3. Add listing service logic and tests for successful creation, authorization rejection, archived product rejection, invalid variant rejection, invalid quantity/status, and public availability behavior.
4. Add frontend API helper and TypeScript payload type.
5. Extend the admin product panel with create-listing state, validation, empty-state action, variant/status/currency controls, and reload-on-success behavior.
6. Run backend tests and frontend lint/build checks.

Rollback removes the new admin route, request schema, frontend helper, and UI form. Existing listing data created through the feature remains valid listing inventory.
