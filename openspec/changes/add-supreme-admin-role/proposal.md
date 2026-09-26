## Why

The project needs a safer admin hierarchy now that store admins can manage catalog and inventory surfaces. Normal admins should operate the store, while a smaller supreme-admin group controls who receives or loses normal admin access.

## What Changes

- Add a supreme-admin privilege level where supreme admins are also normal admins.
- Keep normal admins able to use existing admin catalog, inventory/listing, customer-message, and future order-review surfaces.
- Add supreme-admin-only user administration for promoting customers to normal admin and demoting normal admins back to customers.
- Prevent normal admins from managing admin access.
- Prevent supreme-admin management through the in-app user-management surface for this change; supreme admin creation remains a backend/bootstrap operation.
- Protect against self-demotion and removing the last supreme admin.
- Expose the current user's supreme-admin state to the frontend so navigation and admin screens can show the correct controls.
- Define the order visibility permission for normal and supreme admins while leaving real order persistence and fulfillment workflows to a future order-management change.

## Capabilities

### New Capabilities

- `admin-role-hierarchy`: Defines normal admin versus supreme admin behavior, supreme-admin user-management actions, bootstrap constraints, and frontend visibility expectations.

### Modified Capabilities

None.

## Impact

- Backend/API: add a supreme-admin dependency, expose `is_supreme_admin` in current-user/auth responses, and add supreme-admin-only user-management endpoints under `/api/v1/admin`.
- Database: add a non-null `users.is_supreme_admin` boolean with a false default; keep `users.is_admin` as the existing normal-admin marker.
- Admin bootstrap: extend operator tooling so supreme admins can be granted outside the in-app management flow without handling passwords or invalidating auth data.
- Frontend: add types/API helpers and show user-management navigation/actions only for supreme admins.
- Tests/smoke: cover normal-admin access, supreme-admin promotion/demotion, rejection for normal admins/customers/anonymous users, self-demotion protection, and current-user serialization.
