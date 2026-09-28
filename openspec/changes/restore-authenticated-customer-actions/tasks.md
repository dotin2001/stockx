## 1. Frontend Customer Actions

- [x] 1.1 Restore customer watchlist and customer message DTO types plus API client methods in `apps/web/lib`, and verify TypeScript references compile for authenticated customer and admin message callers.
- [x] 1.2 Restore authenticated-only Add to Watchlist behavior in `ProductDetailView`, and verify guests still see no `Log in to Watch` or equivalent guest watchlist prompt.
- [x] 1.3 Restore account dashboard watchlist loading, listing, removal, empty state, and cart coexistence, and verify authenticated account data loads cart plus watchlist without guest access.
- [x] 1.4 Restore account dashboard message-admin form and recent message history for authenticated customers, and verify it calls protected customer message APIs without exposing guest message submission.
- [x] 1.5 Update customer-facing copy in `/sell`, protected account gate, footer, and frontend README as needed, and verify docs/copy describe guests as browse/cart users and authenticated customers as cart/watchlist/message users.

## 2. Backend Smoke And Documentation

- [x] 2.1 Restore API smoke coverage for authenticated watchlist add/list/remove and duplicate rejection, and verify `apps/api/app/smoke.py` no longer treats watchlist as removed from authenticated customer behavior.
- [x] 2.2 Restore API smoke coverage for authenticated customer message create/list behavior, and verify message smoke uses protected `/api/v1/messages` routes.
- [x] 2.3 Update backend README protected customer action documentation, and verify it lists cart, watchlist, and messages as authenticated customer routes while keeping guests out of those actions.

## 3. Verification

- [x] 3.1 Run frontend typecheck, lint, and build checks, and verify all pass or document the environment blocker.
- [x] 3.2 Run backend tests from `apps/api`, and verify all pass or document the environment blocker.
- [x] 3.3 Run `openspec validate restore-authenticated-customer-actions --strict`, and verify the change artifacts are valid.
