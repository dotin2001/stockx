## 1. Database and Models

- [x] 1.1 Add an Alembic migration after the current head for `users.is_supreme_admin BOOLEAN NOT NULL DEFAULT FALSE`, and verify `alembic upgrade head` applies the migration.
- [x] 1.2 Update the SQLAlchemy `User` model with `is_supreme_admin` and verify model-backed tests can create customer, normal-admin, and supreme-admin users.
- [x] 1.3 Update public user schemas and frontend shared types to include `is_supreme_admin`, and verify register/login/refresh/me response tests assert the field is present.

## 2. Backend Authorization and User Management

- [x] 2.1 Add a supreme-admin auth dependency next to the existing admin dependency, and verify anonymous, customer, and normal-admin requests receive the expected auth errors on a test supreme-only route or endpoint.
- [x] 2.2 Add admin user-management schemas for paginated user rows and admin-access updates, and verify schema serialization includes id, name, email, `is_admin`, `is_supreme_admin`, and timestamps without password data.
- [x] 2.3 Implement a user-management service for listing users, promoting customers/normal admins to normal admin, and demoting non-supreme normal admins to customers; verify service tests cover idempotent promotion, missing targets, self-demotion rejection, and supreme-target demotion rejection.
- [x] 2.4 Add supreme-admin-only `/api/v1/admin` user-management endpoints, and verify API tests cover success, anonymous rejection, customer rejection, normal-admin rejection, and no mutation on rejected requests.
- [x] 2.5 Verify existing normal-admin catalog, listing/inventory, and customer-message admin tests still pass for `is_admin = true` users who are not supreme.

## 3. Bootstrap and Documentation

- [x] 3.1 Extend backend admin bootstrap tooling with a supreme-admin grant command or explicit promote option, and verify command tests cover existing user success, idempotent success, missing user failure, email normalization, and auth-data preservation.
- [x] 3.2 Update backend documentation for normal admin versus supreme admin commands and permissions, and verify the documented command names match the CLI tests.

## 4. Frontend Admin Management

- [x] 4.1 Update frontend auth types and API helpers for admin user listing, promotion, and demotion, and verify TypeScript type checking accepts the new API shapes.
- [x] 4.2 Add supreme-admin-only navigation and an admin user-management page for normal-admin promotion/demotion, and verify normal admins retain existing admin links while user-management controls only render for supreme admins.
- [x] 4.3 Add frontend access/error states for direct user-management navigation by anonymous users, customers, and normal admins, and verify the page handles backend authorization errors gracefully.

## 5. Integration Verification

- [x] 5.1 Extend backend tests or smoke coverage for the full role flow: bootstrap supreme admin, promote customer to normal admin, confirm normal admin can access existing admin operations, confirm normal admin cannot manage users, demote back to customer, and verify protected admin access is removed.
- [x] 5.2 Run backend verification with `cd apps/api && pytest` and, when local PostgreSQL is available, migration apply/rollback checks for the new migration.
- [x] 5.3 Run frontend verification with `cd apps/web && npm run lint` and `cd apps/web && npm run build`, and record any tooling or environment blockers.
