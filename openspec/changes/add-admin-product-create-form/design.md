## Context

See `proposal.md` for motivation. The backend already has admin-only product and variant management routes under `/api/v1/admin`, including `POST /api/v1/admin/products` and `POST /api/v1/admin/products/{product_id}/variants`. The frontend currently has account, sell, cart, catalog, product detail, search, login, and signup routes, but no admin route or admin product form. The `/sell` form currently lets sellers create listings for existing products and should remain seller-focused.

## Goals / Non-Goals

**Goals:**

- Add a frontend admin product creation surface that is visible only to authenticated admins.
- Reuse existing backend admin product and variant APIs rather than adding a new database model.
- Collect only the fields requested for the first product form: category, product name, price, size, and image URL.
- Keep seller listing creation unchanged and separate from catalog product creation.
- Provide clear loading, success, validation, unauthorized, and API-error states.

**Non-Goals:**

- Do not add production image upload or asset storage; the first form accepts an image URL.
- Do not add seller-created products, product approval queues, or moderation workflows.
- Do not add broad admin dashboard analytics or bulk catalog management.
- Do not add database migrations unless implementation discovers an existing schema gap.

## Decisions

### 1. Add an admin frontend route

Use a dedicated admin route such as `/admin/products/new` for the create form.

Rationale: A dedicated route keeps admin product creation separate from `/sell`, which is for seller listings. It also gives a clean place for admin-only guards and future admin product management screens.

Alternatives considered:

- Add the form to `/sell`: rejected because the user clarified that only admins can add products, and `/sell` is seller-facing.
- Add the form inside `/account` only: possible, but a dedicated route keeps the workflow easier to link, test, and expand.

### 2. Guard in the frontend, enforce in the backend

The frontend should show admin navigation and the form only when the current user has `is_admin = true`. Non-admin and guest states should render a clear access-required state. The backend admin routes remain the actual authorization boundary.

Rationale: The existing auth response already exposes `is_admin`, and backend routes already use `CurrentAdminUser`. Frontend gating improves UX but must not be treated as security.

Alternatives considered:

- Trust frontend-only gating: rejected because product creation is privileged.
- Add a new role model: rejected because the project intentionally uses `users.is_admin` for the initial admin foundation.

### 3. Reuse existing admin product APIs with sequential calls

The form should submit product data to `POST /api/v1/admin/products`, then submit the entered size to `POST /api/v1/admin/products/{product_id}/variants`.

Rationale: The backend already has stable APIs for product creation and variant creation. Reusing them avoids new backend behavior and keeps failures aligned with existing tests.

Alternatives considered:

- Add a combined "create product with variant" endpoint: convenient for the form, but unnecessary for the first version and would expand backend scope.
- Store size directly on the product: rejected because the current schema models size as a product variant.

### 4. Generate slug from product name in the frontend

The form should generate a kebab-case slug from the entered product name and send it with product creation. If the backend rejects a duplicate slug, the form should surface that error and keep the admin's inputs.

Rationale: The requested form does not include a slug field, but the backend requires stable product slugs. Auto-generating keeps the form compact and matches common admin UX.

Alternatives considered:

- Add a visible slug input immediately: more control, but adds another required field beyond the requested form.
- Generate slug in the backend: cleaner long term, but the current backend schema requires the client to send a slug.

### 5. Treat price as product summary price

Map the entered price to `lowest_ask_cents` on product creation. This gives the product card/search/category views a display price even before any seller listing exists.

Rationale: Existing product summaries expose `lowest_ask_cents`, while listings own real sellable offers. For admin product creation, the requested price is best interpreted as the catalog summary price for now.

Alternatives considered:

- Create a listing from admin product creation: rejected because listings are seller-owned offers, and the user asked for admin product creation, not seller inventory.
- Leave price unset: rejected because the requested form includes price.

## Risks / Trade-offs

- [Variant creation can fail after product creation] -> Mitigate by showing a partial-success state that the product was created but the initial size variant failed, with guidance to retry variant creation once management UI exists.
- [Generated slug may conflict] -> Mitigate by surfacing backend duplicate-slug errors and keeping form data for renaming.
- [Image URL can be broken or low quality] -> Mitigate with client-side URL validation and rely on future image upload/storage work for stronger guarantees.
- [Frontend gate can drift from backend authorization] -> Mitigate by verifying non-admin access states in frontend tests and backend 403 behavior through existing API tests.

## Migration Plan

1. Add frontend admin product types and API helpers for admin product create and variant create.
2. Add an admin-only route and guard for the product creation form.
3. Build the form using existing category data and submit product followed by variant.
4. Add admin navigation affordance for authenticated admins.
5. Add focused frontend tests or route smoke checks for admin, non-admin, and guest states.
6. Run frontend type, lint, and build checks; run backend tests only if backend code changes.

## Open Questions

None.
