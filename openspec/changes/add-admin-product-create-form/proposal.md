## Why

Admins can create products through backend APIs, but the Next.js storefront has no admin-facing product form. Adding an admin-only form lets catalog managers add products with category, name, price, size, and image data without giving sellers product creation access.

## What Changes

- Add an admin-only frontend product creation workflow.
- Let admins choose an existing category, enter product name, price, size, and image URL, then submit the product to the existing admin product APIs.
- Generate the product slug from the product name for the first version, while surfacing duplicate-slug API errors clearly.
- Create an initial product variant from the entered size after the product is created.
- Keep seller `/sell` behavior limited to creating listings for existing catalog products.
- Keep file/image upload storage out of scope; the first version accepts an image URL.

## Capabilities

### New Capabilities

- `admin-product-management-ui`: Admin-only frontend behavior for creating catalog products and initial variants from a form.

### Modified Capabilities

- None.

## Impact

- Frontend: adds an admin product creation route or admin-only account/admin surface, admin form component, typed API helpers, and admin navigation affordance.
- Backend: reuses existing `/api/v1/admin/products` and `/api/v1/admin/products/{id}/variants` routes; no new database model is expected.
- Authorization: frontend hides the form from non-admin users, while backend admin authorization remains the enforcement point.
- Seller flow: remains focused on listing existing catalog products and does not gain product creation controls.
