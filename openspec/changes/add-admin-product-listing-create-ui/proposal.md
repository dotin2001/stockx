## Why

Supreme admins can edit quantity and status only after a product already has a listing, so products with no sellable listings are stuck behind a read-only empty state. This prevents admins from making all catalog products available through the product management screen.

## What Changes

- Add a create-listing control to the admin product inventory panel for products with no sellable listings and for products that need additional product or variant inventory rows.
- Allow supreme admins to create the first sellable listing from a managed product, including price, currency, optional variant, initial available quantity, and initial status.
- Keep normal admins able to view catalog and variant management while hiding or disabling the supreme-only listing creation workflow.
- Ensure backend authorization rejects non-supreme listing creation from the admin inventory route, while preserving existing listing validation for missing products, archived products, and mismatched variants.
- Refresh the admin product inventory summary and listing rows after creation so the new listing immediately becomes editable through existing quantity and status controls.
- Preserve public buying behavior: only active listings with available quantity greater than zero should become cartable.

## Capabilities

### New Capabilities

- `admin-product-listing-creation`: Defines supreme-admin creation of sellable listing inventory from the admin product management UI, including empty-state creation for products with no listings.

### Modified Capabilities

None.

## Impact

- Frontend: extend `apps/web/components/admin/admin-products-panel.tsx` with listing creation state, validation, empty-state controls, variant selection, and API integration.
- Frontend API/types: add or reuse typed helpers for creating a listing from admin product management, including optional product variant and initial quantity/status behavior.
- Backend/API: add a supreme-admin-scoped admin listing creation endpoint or extend the existing listing creation service/API to support initial inventory fields safely.
- Backend services/schemas: validate initial quantity, status, product archive state, and variant ownership in the listing creation flow.
- Tests/smoke: cover products with zero listings, supreme-admin creation, normal-admin rejection, invalid variant/quantity cases, and public availability after active positive-quantity listing creation.
