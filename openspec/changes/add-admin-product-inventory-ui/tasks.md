## 1. Database and Backend Inventory Model

- [x] 1.1 Add an Alembic migration after the current head for `listings.available_quantity INTEGER NOT NULL DEFAULT 1` with a non-negative check constraint, and verify `alembic upgrade head` applies against local PostgreSQL.
- [x] 1.2 Update the SQLAlchemy `Listing` model and database foundation tests for `available_quantity`, and verify `pytest tests/test_database_foundation.py` passes from `apps/api`.
- [x] 1.3 Update listing, cart, and product/admin schemas to expose inventory quantity where admin or cart availability responses need it, and verify schema serialization tests cover quantity without changing public product summary shape unexpectedly.

## 2. Backend Inventory Rules and APIs

- [x] 2.1 Update cart availability and guest cart resolution so active listings require `available_quantity > 0`, and verify API tests reject zero-quantity listings and quantities above availability.
- [x] 2.2 Add supreme-admin-only service operations for increasing and decreasing listing inventory quantity, and verify service tests cover increase, decrease, below-zero rejection, invalid adjustment rejection, missing listing rejection, normal-admin rejection, and customer rejection.
- [x] 2.3 Add supreme-admin-only service operations for changing listing inventory status among supported states, and verify tests cover active, sold, cancelled, missing listing, normal-admin rejection, and customer rejection.
- [x] 2.4 Add backend admin API routes for inventory quantity and status mutations under `/api/v1/admin`, and verify API tests cover success, anonymous rejection, customer rejection, normal-admin rejection, and no mutation on rejected requests.
- [x] 2.5 Extend managed product/listing read APIs with inventory summaries needed by the product management UI, and verify normal admins can read managed product inventory summaries while customers and anonymous clients cannot.
- [x] 2.6 Verify existing normal-admin product create/update/archive/restore and variant-management tests still pass without supreme-admin status.

## 3. Frontend Product Management UI

- [x] 3.1 Add frontend types and API helpers for managed product listing, product update, archive/restore, variant management, inventory quantity adjustment, and inventory status change, and verify `npm run typecheck` accepts the new shapes.
- [x] 3.2 Add `/admin/products` as the primary admin product management route with loading, empty, error, login-required, customer-denied, normal-admin, and supreme-admin states, and verify source or component tests cover these states.
- [x] 3.3 Add managed product list controls for active/archived/inventory filtering and product scanning, and verify the UI renders product identity, category, catalog state, inventory summary, and role-appropriate actions.
- [x] 3.4 Add catalog edit controls for normal admins and supreme admins, and verify successful update, validation error display, and stale/error reload behavior.
- [x] 3.5 Add variant management controls for normal admins and supreme admins, and verify create, update, remove, and error states are represented in frontend tests or source smoke checks.
- [x] 3.6 Add supreme-admin-only quantity and inventory status controls, and verify normal admins do not see those controls while supreme admins can submit them and see refreshed inventory state.
- [x] 3.7 Update admin navigation so `Admin Products` links to `/admin/products` and the create-product page remains reachable, and verify existing admin product creation smoke coverage is updated.

## 4. Documentation and Smoke Coverage

- [x] 4.1 Update backend and frontend documentation for `/admin/products`, inventory quantity behavior, and supreme-admin-only status/quantity permissions, and verify documented route names match implemented routes.
- [x] 4.2 Extend backend role-flow or smoke coverage for supreme admin inventory management: promote/grant supreme admin, adjust quantity, change status, confirm public/cart availability changes, and confirm normal admin cannot mutate inventory.
- [x] 4.3 Run backend verification with `cd apps/api && pytest` and local migration apply/rollback checks for the new migration.
- [x] 4.4 Run frontend verification with `cd apps/web && npm run lint`, `cd apps/web && npm run typecheck`, and `cd apps/web && npm run build`, recording any Node/tooling blockers.
- [x] 4.5 Run root frontend source smoke tests affected by admin navigation and product management, and verify the updated tests pass.
