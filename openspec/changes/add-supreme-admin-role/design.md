## Context

The backend currently models admin access as a flat `users.is_admin` boolean. `CurrentAdminUser` protects existing `/api/v1/admin` operations, `UserPublic` exposes `is_admin`, the frontend gates admin links with `user.is_admin`, and the `app.admin promote` command marks an existing user as admin while preserving auth data. Existing documentation explicitly defers supreme-admin hierarchy.

There is no durable order model yet. This change can define that normal and supreme admins are authorized for order-review surfaces, but implementation should not invent order persistence or fulfillment workflows.

## Goals / Non-Goals

**Goals:**

- Preserve current normal-admin behavior for product, inventory/listing, and message management.
- Add a separate supreme-admin flag that is always paired with normal-admin privileges.
- Add backend-enforced supreme-admin authorization for normal-admin promotion and demotion.
- Keep supreme-admin creation outside the in-app UI through operator/bootstrap tooling.
- Expose role state to the frontend so navigation and route gates match backend authorization.
- Cover migration, service, API, frontend, and smoke/unit tests.

**Non-Goals:**

- Replacing the current boolean admin model with a string role enum.
- Allowing in-app creation, removal, or transfer of supreme-admin status.
- Building real order tables, checkout capture, payment processing, fulfillment, or order dashboard behavior.
- Adding fine-grained per-feature permissions beyond customer, normal admin, and supreme admin.

## Decisions

### Add `users.is_supreme_admin` instead of replacing `is_admin`

Add a non-null boolean column with `false` default and keep `is_admin` as the existing normal-admin marker. A supreme admin must also have `is_admin = true`.

Rationale: this is the smallest compatible migration. Existing admin checks, product management, listing management, customer messages, and frontend normal-admin behavior continue to work while supreme-only checks can be added incrementally.

Alternatives considered:

- Text `role` column: more expressive, but conflicts with the current project convention to avoid a text user role/access-level column for the initial foundation and would force broader rewrites.
- Single `is_supreme_admin` flag only: loses the existing normal-admin distinction and breaks current admin gates.

### Keep access tokens user-id only and load current roles from the database

Continue decoding access tokens to a user id, then read `is_admin` and `is_supreme_admin` from the database in auth dependencies.

Rationale: promotions and demotions take effect on the next protected request without waiting for access-token expiry, and the current security module already follows this pattern.

Alternative considered:

- Embed role claims in access tokens: reduces a database read only if broader auth architecture changes, but risks stale authorization after demotion.

### Introduce a supreme-admin dependency next to the normal-admin dependency

Add a dependency equivalent to `CurrentSupremeAdminUser` that requires both authentication and `is_supreme_admin`. Keep `CurrentAdminUser` based on `is_admin`.

Rationale: route handlers remain thin and existing admin routes do not need to know about supreme-admin rules unless they expose user-management actions.

Alternative considered:

- Inline role checks in each route: quick for one endpoint, but easier to drift and harder to test consistently.

### Add focused admin user-management endpoints under `/api/v1/admin`

Add supreme-only endpoints for listing manageable users and promoting/demoting normal-admin access. The target model is:

- List users with public management fields, pagination, and optional search by email/name.
- Promote by user id or normalized email to set `is_admin = true` and `is_supreme_admin = false` for non-supreme targets.
- Demote by user id to set `is_admin = false` only for non-supreme normal admins.

Rationale: this keeps user management with the rest of admin operations and gives the frontend stable backend-enforced actions.

Alternative considered:

- CLI-only admin management: simpler, but does not meet the requested supreme-admin in-app management capability.

### Protect supreme admins through policy, not frontend hiding

The service layer should reject demoting supreme-admin accounts and self-demotion. In-app promotion must never set `is_supreme_admin`.

Rationale: the requested option is strictly customer <-> normal admin management. Supreme-admin management remains operator-controlled to avoid accidental lockout or privilege escalation.

Alternative considered:

- Allow supreme admins to manage other supreme admins: more complete role administration, but broader and riskier than option 1.

### Extend bootstrap tooling for supreme-admin grants

Add an operator command such as `promote-supreme <email>` or an explicit flag on the existing promote command. The command should normalize email, require an existing user, set both `is_admin` and `is_supreme_admin`, preserve auth data, and be idempotent.

Rationale: a protected bootstrap path is needed for the first supreme admin and for recovery without exposing supreme-admin changes in the UI.

Alternative considered:

- Seed a hardcoded supreme-admin account: unsafe because it couples credentials or identities to seed data.

### Frontend gates follow backend role fields

Update `UserPublic` types and auth state to include `is_supreme_admin`. Keep normal admin links driven by `is_admin`, and add user-management navigation/page access only when `is_supreme_admin` is true.

Rationale: UI should be clear, but backend checks remain authoritative. Unauthorized direct navigation should show access/error states rather than relying on hidden links.

Alternative considered:

- Infer supreme-admin UI from `is_admin`: impossible to distinguish normal and supreme admins.

## Risks / Trade-offs

- Existing users with `is_admin = true` will not become supreme admins automatically. -> Mitigation: document and use the bootstrap command to grant supreme-admin status to selected existing admins.
- Two booleans can theoretically drift into `is_admin = false` and `is_supreme_admin = true`. -> Mitigation: service and bootstrap writes must set both fields consistently; tests should assert supreme admins are also normal admins.
- The database may not enforce the boolean implication. -> Mitigation: application-level tests cover the invariant; a database check constraint can be considered if migration compatibility remains simple.
- Frontend hiding is not sufficient for security. -> Mitigation: all user-management endpoints use the supreme-admin dependency and service-level target validation.
- Order-review permission is specified before orders exist. -> Mitigation: keep implementation limited to role naming/authorization plumbing and add real order-management behavior in a later change.

## Migration Plan

1. Add an Alembic migration after the current head to add `users.is_supreme_admin BOOLEAN NOT NULL DEFAULT FALSE`.
2. Update the SQLAlchemy user model and public user schemas to include `is_supreme_admin`.
3. Add the supreme-admin dependency and user-management service/API.
4. Extend bootstrap tooling for supreme-admin grants.
5. Update frontend types, API helpers, navigation, and the user-management admin page.
6. Add unit/API/frontend build coverage, then run backend tests and frontend lint/build checks.

Rollback should drop the new column and remove the new routes/UI in code. Demotions/promotions to normal admin remain represented by the existing `is_admin` field; supreme-admin status would be lost on downgrade.
