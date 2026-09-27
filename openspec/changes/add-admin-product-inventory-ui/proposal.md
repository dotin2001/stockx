## Why

Admins currently have backend product-management APIs and a frontend create-product form, but no UI to see and manage all products after creation. Store inventory quantity is also not modeled yet, so admins cannot adjust stock or status from a product management surface.

## What Changes

- Add an admin product management UI where admins can list all products, inspect active and archived products, and open product edit/inventory actions.
- Add frontend API helpers and components for managed product listing, product update, archive/restore, variant management, and inventory controls.
- Add inventory quantity support for sellable product variants/listings so supreme admins can add or remove available quantity.
- Add supreme-admin-only controls for sensitive inventory quantity changes and sellable status changes.
- Keep normal admins able to manage catalog product details and variants, while hiding and backend-rejecting supreme-only inventory controls for normal admins.
- Preserve public catalog behavior: archived products remain hidden publicly, and products with no active available inventory remain visible only according to existing catalog rules unless separately archived.

## Capabilities

### New Capabilities

- `admin-product-inventory-management`: Defines the admin product management UI, catalog edit behavior, supreme-admin inventory quantity and status controls, and public catalog/cart effects of managed inventory.

### Modified Capabilities

None.

## Impact

- Frontend: add `/admin/products` management route, product table/filter UI, product edit controls, inventory controls, and navigation from existing admin links.
- Backend/API: extend admin product/listing APIs for inventory-aware reads, quantity adjustments, and supreme-only status controls.
- Database: add durable inventory quantity to the sellable inventory model, most likely on listings or a listing-like inventory record rather than on catalog products.
- Auth/authorization: keep normal admin catalog operations under `is_admin`; require `is_supreme_admin` for quantity and status mutations.
- Tests/smoke: cover normal-admin visibility, supreme-admin controls, quantity updates, status changes, public availability, and rejected unauthorized mutations.
