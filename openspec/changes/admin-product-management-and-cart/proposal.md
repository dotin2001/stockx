## Why

The backend can already expose products for public browsing, but product creation and cleanup still require direct database or seed changes. The next marketplace step is to separate admin catalog control from customer shopping behavior: admins manage products, while normal users browse products and maintain a cart.

## What Changes

- Add admin-only product management APIs for creating, updating, archiving, and restoring products.
- Add admin-only product variant management for size, color, and SKU data.
- Preserve public catalog browsing for non-admin users; normal users can view products but cannot create, edit, delete, archive, or restore them.
- Add authenticated customer cart APIs for adding sellable listings to a cart, viewing the cart, updating quantities, and removing cart items.
- Add database persistence for cart items and product archival state.
- Prefer product archiving over hard deletion so listings, cart items, and future order history are not broken.
- Keep checkout, payment, order placement, inventory reservation, and production image upload out of scope.

## Capabilities

### New Capabilities

- `admin-product-management`: Admin-only catalog management for products and variants, including create, update, archive, and restore behavior.
- `shopping-cart`: Authenticated customer cart behavior for viewing cart contents and managing cart items that reference active sellable listings.

### Modified Capabilities

- None.

## Impact

- Backend API: adds protected `/api/v1/admin/...` routes and `/api/v1/cart...` routes.
- Backend auth: adds an admin authorization dependency based on the existing `users.is_admin` boolean.
- Database: adds cart persistence and product archival metadata through Alembic migrations.
- Services/schemas/tests: adds Pydantic schemas, service-layer logic, endpoint tests, and database migration/seed verification for the new workflows.
- Documentation/smoke checks: updates backend README and optional smoke coverage to describe admin product management and cart behavior.
