## 1. Preflight

- [x] 1.1 Confirm the effective `DATABASE_URL` for `apps/api` targets the intended local StockX database, and verify this by printing or otherwise reporting the non-secret connection target before mutation.
- [x] 1.2 Verify an existing `users` row for `demo@stockx.local`; if it is missing, stop without creating a user and report that the account must be registered first.

## 2. Promotion

- [x] 2.1 Run the existing backend bootstrap command `python -m app.admin promote-supreme demo@stockx.local` from `apps/api`, and verify the command exits successfully with the expected promoted email.
- [x] 2.2 Verify the database row for `demo@stockx.local` has `is_admin = true` and `is_supreme_admin = true`, and verify no other user email was targeted.

## 3. Follow-up

- [x] 3.1 If a browser session for `demo@stockx.local` is already active, refresh auth state by logging out/in or refreshing the session, and verify the frontend sees supreme-admin controls.
