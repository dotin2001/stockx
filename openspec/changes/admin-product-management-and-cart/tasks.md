## 1. Database Foundation

- [x] 1.1 Add an Alembic migration for product archive metadata and `cart_items`, and verify the migration defines nullable product archive columns plus a user/listing-scoped cart table with positive quantity and unique `(user_id, listing_id)` constraints.
- [x] 1.2 Update SQLAlchemy models and relationships for product archive metadata and cart items, and verify `Base.metadata.tables` includes `cart_items` with the expected foreign keys and constraints.
- [x] 1.3 Update database foundation tests for archive columns and cart item constraints, and verify `pytest tests/test_database_foundation.py` passes from `apps/api`.
- [x] 1.4 Apply and rollback the new migration against local PostgreSQL, and verify `alembic upgrade head` and `alembic downgrade -1` complete successfully before re-applying head.

## 2. Authorization and Shared Schemas

- [x] 2.1 Add an admin authorization dependency based on the existing current-user dependency and `users.is_admin`, and verify anonymous and non-admin requests receive stable authentication/authorization errors.
- [x] 2.2 Add product management request/response schemas for product create, product update, admin product reads, variant create, and variant update, and verify schema validation rejects invalid slugs, missing required fields, and negative price summary values.
- [x] 2.3 Add cart request/response schemas for cart item add, quantity update, cart item reads, and cart summary data, and verify schema validation rejects missing listing IDs and non-positive quantities.

## 3. Admin Product Management

- [x] 3.1 Implement admin product service operations for create, update, archive, restore, and managed list, and verify service tests cover successful admin operations, missing products/categories, duplicate slugs, and archive state transitions.
- [x] 3.2 Implement admin variant service operations for create, update, and remove, and verify service tests cover valid variants, missing products, missing variants, and non-admin rejection through the API layer.
- [x] 3.3 Add an admin API router mounted under `/api/v1/admin`, and verify admin endpoints are reachable only with admin credentials.
- [x] 3.4 Update public catalog services to exclude archived products from product lists, category product lists, search, and detail lookups, and verify public catalog tests cover archived products being hidden.
- [x] 3.5 Add API tests for admin product create/update/archive/restore and managed product listing, and verify non-admin and anonymous clients cannot manage products.
- [x] 3.6 Add API tests for admin variant create/update/delete, and verify public product detail reflects variant changes while preserving the parent product.

## 4. Shopping Cart

- [x] 4.1 Implement cart service operations for list, add or merge listing, update quantity, and remove item, and verify service tests cover user scoping, duplicate listing merge behavior, missing listings, inactive listings, and archived products.
- [x] 4.2 Add a cart API router mounted under `/api/v1/cart`, and verify authenticated users can list, add, update, and remove their own cart items.
- [x] 4.3 Add cart API tests for anonymous rejection and cross-user update/delete rejection, and verify one user's cart operations cannot read or mutate another user's cart items.
- [x] 4.4 Add cart availability behavior for inactive listings and archived products, and verify cart responses mark existing unavailable items instead of silently deleting them.

## 5. Documentation and Smoke Coverage

- [x] 5.1 Update `apps/api/README.md` with admin product management and cart endpoint summaries, and verify the documented routes match the implemented router paths.
- [x] 5.2 Extend or add running-service smoke coverage for admin product archive/restore and authenticated cart add/list/remove, and verify the smoke command passes against local PostgreSQL with migrations and seed data applied.
- [x] 5.3 Run the backend test suite from `apps/api`, and verify `pytest` passes.
- [x] 5.4 Run seed data after the new migration, and verify `python -m app.db.seed` remains idempotent and public product browsing still returns active seeded products.
- [x] 5.5 Run `openspec validate admin-product-management-and-cart --strict`, and verify the change remains valid after implementation updates.
