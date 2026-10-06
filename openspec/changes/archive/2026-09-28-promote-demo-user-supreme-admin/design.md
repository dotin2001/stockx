## Context

See `proposal.md` for motivation. The backend already provides operator tooling for admin bootstrap in `app.admin`: `promote-supreme <email>` calls the existing `grant_supreme_admin` service, normalizes email, requires an existing user, sets both `is_admin` and `is_supreme_admin`, and preserves auth data.

The default local database URL is `postgresql+psycopg://stockx:stockx@localhost:5432/stockx`, but the actual apply step must respect the `DATABASE_URL` configured for `apps/api`.

## Goals / Non-Goals

**Goals:**

- Promote the existing `demo@stockx.local` account in the intended local database.
- Use the existing backend operator path rather than a hand-written SQL update.
- Verify the account exists before mutation and verify both role flags after mutation.
- Preserve password hash, refresh-token records, and all unrelated user data.

**Non-Goals:**

- Creating `demo@stockx.local` if it does not already exist.
- Adding a seed account, migration, API route, frontend control, or new role model.
- Changing any other user's role flags.
- Granting or removing supreme-admin status through the in-app user-management UI.

## Decisions

### Use `python -m app.admin promote-supreme demo@stockx.local`

Run the existing CLI from `apps/api` with the intended `DATABASE_URL`. This keeps the operation aligned with tested service behavior and avoids duplicating role rules in ad hoc SQL.

Alternative considered: direct SQL update. It is shorter, but it bypasses the service/CLI path that already normalizes email, handles missing users consistently, and preserves the documented bootstrap contract.

### Stop if the user is missing

The existing command already fails for missing users. The apply step should treat that as a blocker and report that the account must be registered first.

Alternative considered: create the user during apply. That would require a password decision and would change auth/account state beyond the user's request.

### Verify role flags after promotion

After the command succeeds, query the user row or use an equivalent backend session check to confirm `is_admin = true` and `is_supreme_admin = true` for `demo@stockx.local`.

Alternative considered: trust command output only. The output is useful, but a database read confirms the actual target environment was changed.

## Risks / Trade-offs

- [Wrong database target] The command could use an unintended `DATABASE_URL`. -> Confirm or display the effective local database target before promotion and verify the row after.
- [Missing demo account] The command will fail if `demo@stockx.local` has not been registered. -> Stop and ask for the account to be created or for permission to plan/create it separately.
- [Stale frontend session] The currently logged-in browser session may still have old role flags. -> Refresh the session, log out/in, or call auth refresh after promotion.
- [Privilege operation sensitivity] Supreme-admin access is powerful. -> Limit the operation to the exact email and use the documented backend bootstrap command.

## Migration Plan

1. From `apps/api`, confirm the intended `DATABASE_URL` points to the local StockX database.
2. Run `python -m app.admin promote-supreme demo@stockx.local`.
3. Verify the resulting `users` row for `demo@stockx.local` has both role flags true.
4. If the frontend is already logged in as `demo@stockx.local`, refresh or re-login so the client receives updated role state.

Rollback, if needed, is a separate explicit operation because demoting supreme-admin access is security-sensitive. A safe rollback would set `is_supreme_admin = false` for only `demo@stockx.local`, and optionally keep or remove `is_admin` depending on the intended access level.
