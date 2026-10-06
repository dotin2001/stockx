## 1. Database And Schemas

- [x] 1.1 Add product storefront content persistence for feature bullets, detail/specification rows, and gallery image data; verify Alembic upgrade and downgrade handle existing products with safe defaults.
- [x] 1.2 Update SQLAlchemy product model and backend product schemas for storefront content, purchase options, product stats, and related product summaries; verify schema tests accept valid structured content and reject malformed content.
- [x] 1.3 Update TypeScript product/admin product types to mirror the backend response and payload shapes; verify `npm run build` catches no type errors.

## 2. Backend Product And Stock APIs

- [x] 2.1 Extend admin product create/update behavior to read and write the new storefront content fields; verify backend tests cover create, update, clear optional content, duplicate slug, and invalid structured content errors.
- [x] 2.2 Add authorized stock update behavior for existing stock records covering price, currency, quantity, status, and variant assignment; verify API tests cover valid updates, invalid values, missing stock, mismatched variant, and insufficient privilege.
- [x] 2.3 Preserve existing archive/restore, variant management, cart, watchlist, and guest cart behavior while adding the new fields; verify the existing affected backend tests still pass.
- [x] 2.4 Extend public product detail serialization with purchase options, store price data, stock state, and related products; verify API tests cover in-stock products, out-of-stock products, products with deleted or missing variants, archived products, and sparse related-product catalogs.

## 3. Admin Product Editor UI

- [x] 3.1 Update the admin product management surface into a complete selected-product editor with sections for basics, storefront content, media/gallery URLs, variants, inventory, visibility, and preview links; verify an admin can edit each section from `/admin/products`.
- [x] 3.2 Replace admin-facing marketplace wording with store inventory wording while preserving existing role-specific controls; verify the UI no longer labels customer-facing product management as lowest ask, seller, or public listings.
- [x] 3.3 Add controls for editing structured feature bullets, detail/spec rows, and gallery image URLs with add/remove/reorder or stable ordering behavior; verify validation feedback preserves unsaved input after an error.
- [x] 3.4 Add controls for editing existing stock price, currency, quantity, variant assignment, and status; verify the UI refreshes the selected product after successful stock updates and shows backend errors for rejected mutations.
- [x] 3.5 Update the admin product creation flow so new products can capture the same storefront content or can be saved with sensible defaults; verify product creation still creates an initial variant/stock path as expected.

## 4. Public Product Experience

- [x] 4.1 Update product cards and product detail labels from marketplace price language to store price/stock language; verify customer pages do not display "Lowest Ask" copy.
- [x] 4.2 Add variant or size selection on product detail backed by purchase options; verify selecting an option updates displayed price, stock state, and cart target.
- [x] 4.3 Update add-to-cart and buy-now behavior to use the selected in-stock purchase option for guests and authenticated users; verify unavailable products disable purchase actions while preserving browse/watchlist behavior.
- [x] 4.4 Render admin-managed feature bullets, detail/spec rows, gallery images, and product stats on public product detail; verify empty optional sections are omitted without layout gaps.
- [x] 4.5 Render bounded related products from the product detail response; verify the current product is excluded and the section is omitted when there are no related products.

## 5. Verification And Smoke Coverage

- [x] 5.1 Run backend tests in `apps/api` and verify product editor, stock update, product detail, cart availability, and existing admin/product tests pass.
- [ ] 5.2 Run migration apply/rollback against local PostgreSQL when available and verify existing seed data remains readable after reseeding.
- [x] 5.3 Run frontend lint/type/build checks in `apps/web` and verify the admin product editor and public product detail compile.
- [x] 5.4 Add or update running-service smoke coverage for admin editing storefront content, updating stock price/quantity/status, viewing public product detail, and adding a selected in-stock option to cart; verify the smoke workflow passes when local prerequisites are available.
- [x] 5.5 Run `openspec validate complete-admin-product-editor --strict` and verify the change remains valid after implementation updates.
