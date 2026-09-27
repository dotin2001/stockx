## 1. Backend Contract

- [x] 1.1 Add an admin listing creation request schema with `product_variant_id`, `price_cents`, `currency`, `available_quantity`, and `status`, and verify schema validation covers positive price, non-negative quantity, valid currency, and allowed statuses.
- [x] 1.2 Add a supreme-admin `POST /api/v1/admin/products/{product_id}/listings` route that returns the created listing management response, and verify anonymous, customer, and normal-admin requests are rejected.
- [x] 1.3 Add managed listing creation service logic that validates product existence, archived product state, variant ownership, initial quantity, and status, and verify service tests cover success and each rejection path.
- [x] 1.4 Ensure active positive-quantity listings created through the admin product route participate in public product detail and cart availability, and verify API tests cover active, zero-quantity, and unavailable-status cases.

## 2. Frontend API And Types

- [x] 2.1 Add TypeScript payload types and an API helper for admin product listing creation, and verify frontend type checking accepts the new helper usage.
- [x] 2.2 Add reusable conversion/validation handling for listing price and initial quantity in the admin product panel, and verify invalid local values show an actionable error before the API call.

## 3. Admin Product UI

- [x] 3.1 Add create-listing state to `AdminProductsPanel`, reset it when the selected product changes, and verify switching products does not leak draft values between products.
- [x] 3.2 Render a supreme-admin create-listing form in the inventory section for both empty and non-empty listing states, and verify products with no listings no longer show only the "No sellable listings yet" message.
- [x] 3.3 Support base-product and variant selection, price, currency, initial quantity, and initial status fields in the form, and verify submitted payloads match the selected product and variant.
- [x] 3.4 Submit listing creation through the new admin API helper, reload managed products on success, and verify the newly created listing appears with existing quantity and status controls.
- [x] 3.5 Keep normal admins on a restricted inventory-creation state without sensitive controls, and verify normal-admin UI does not render the create-listing form.

## 4. Verification

- [x] 4.1 Run backend tests for admin product/listing/inventory behavior and verify they pass.
- [x] 4.2 Run frontend lint/type/build checks and verify they pass.
- [x] 4.3 Smoke test the admin flow with a supreme admin on a product that has zero listings and verify it can create a listing, see updated available count, and edit quantity/status afterward.
