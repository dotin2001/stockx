## 1. Frontend API Types and Helpers

- [x] 1.1 Add frontend types for admin product create, admin product read, admin product page, and product variant create, and verify TypeScript accepts the API response shapes.
- [x] 1.2 Add `api.createAdminProduct` and `api.createAdminProductVariant` helpers using existing `/api/v1/admin` routes, and verify they attach the bearer token like other protected calls.
- [x] 1.3 Add or reuse a slug-generation helper for product names and verify names produce API-compatible kebab-case slugs.

## 2. Admin Product Creation Route

- [x] 2.1 Add a dedicated admin product creation route such as `/admin/products/new` and verify the route renders inside the existing app layout.
- [x] 2.2 Add an admin-only guard for the route and verify guests see login-required state while authenticated non-admin users see an admin-required state.
- [x] 2.3 Add an authenticated admin navigation affordance to the product creation route and verify non-admin navigation does not show product creation links.

## 3. Product Creation Form

- [x] 3.1 Build the admin product form with category select, product name, price, size, and image URL fields, and verify all controls have semantic labels and required states.
- [x] 3.2 Load categories into the form and verify loading and category-load error states prevent submission.
- [x] 3.3 Validate blank name, missing category, non-positive price, blank size, and invalid image URL values before submission where practical, and verify actionable field or form errors are shown.
- [x] 3.4 Submit product creation with generated slug, selected category, image URL, and price converted to cents, and verify duplicate-slug API errors keep form data available.
- [x] 3.5 Submit initial variant creation with the entered size after product creation succeeds, and verify success state links to the created product.
- [x] 3.6 Handle variant creation failure after product creation and verify the user sees a partial-success message that the product exists but size creation failed.

## 4. Seller Flow Preservation

- [x] 4.1 Verify `/sell` remains limited to seller listing creation for existing products and does not show product name, category, image, or product creation controls.
- [x] 4.2 Verify non-admin sellers cannot access the admin product creation form or create products through frontend admin controls.

## 5. Verification

- [x] 5.1 Add focused frontend tests or route smoke checks for admin, non-admin, and guest product creation states, and verify they pass.
- [x] 5.2 Run `npm run web:typecheck` and verify the new route, form, and API types compile.
- [x] 5.3 Run `npm run web:lint` and verify the new frontend code passes linting.
- [x] 5.4 Run `npm run web:build` and verify the Next.js app builds successfully.
- [x] 5.5 Run `openspec validate add-admin-product-create-form --strict` and verify the change remains valid after implementation.
