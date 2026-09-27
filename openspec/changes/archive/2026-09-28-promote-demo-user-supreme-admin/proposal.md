## Why

The local environment needs `demo@stockx.local` to have supreme-admin access so admin-only and supreme-admin-only product inventory controls can be exercised through the UI. The project already supports operator-controlled supreme-admin grants, so this change should use that existing bootstrap path instead of adding new auth behavior.

## What Changes

- Promote the existing user account `demo@stockx.local` to supreme admin in the configured local database.
- Use the existing backend operator command or equivalent service path that normalizes email and sets both `users.is_admin` and `users.is_supreme_admin`.
- Verify the account exists before promotion; if it does not exist, stop and report that the user must be created first.
- Verify the final database row has `is_admin = true` and `is_supreme_admin = true`.
- Do not change code, migrations, seed data, passwords, refresh tokens, or public API behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a one-off operational data change using the existing `admin-role-hierarchy` bootstrap behavior, so this change sets `skip_specs: true`.

## Impact

- Database: one existing `users` row for `demo@stockx.local` will be updated.
- Backend tooling: use `python -m app.admin promote-supreme demo@stockx.local` or the installed `stockx-api-admin promote-supreme demo@stockx.local` command against the intended `DATABASE_URL`.
- Auth: existing sessions and refresh-token records should be preserved; the user may need to refresh or log in again for the frontend to receive updated role flags.
- Risk: applying against the wrong `DATABASE_URL` would promote the wrong environment, so the apply step must confirm the target database URL before mutating data.
