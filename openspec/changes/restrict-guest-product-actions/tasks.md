## 1. Frontend Customer Surfaces

- [x] 1.1 Remove product-detail watchlist state, API calls, buttons, login-to-watch prompt, and unavailable-listing watchlist copy from `ProductDetailView`, and verify product pages still show public product data plus Add to Cart/Buy Now for active listings.
- [x] 1.2 Preserve guest add-to-cart and buy-now behavior in `ProductDetailView`, and verify a guest can add an active listing to local guest cart without being redirected to login.
- [x] 1.3 Remove watchlist and customer message state, data loading, mutations, sections, forms, recent-message history, and customer copy from `AccountDashboard`, and verify the account page still loads authenticated account identity plus cart/checkout state.
- [x] 1.4 Audit frontend API client/types imports for customer-facing watchlist and customer-message usage, remove unused customer-facing calls where possible, and verify `rg "watchlist|Watchlist|CustomerMessage|message admin|Message Admin|addWatchlist|listCustomerMessages|createCustomerMessage" apps/web` shows no customer-facing product/account dependencies.

## 2. Backend Smoke And Documentation

- [x] 2.1 Update `apps/api/app/smoke.py` so customer shopping smoke coverage no longer creates watchlist items or customer messages, and verify the smoke workflow still covers guest cart resolution plus authenticated cart add/list/remove and duplicate merge behavior.
- [x] 2.2 Update backend and frontend documentation that advertises customer watchlist or message-admin flows, and verify docs describe public browsing, guest cart, authenticated cart, and admin-only management accurately.
- [x] 2.3 Audit watchlist and customer message backend routes/services for remaining required admin or compatibility use, and verify any retained endpoints are not required by customer-facing product/account flows.

## 3. Verification

- [x] 3.1 Run frontend lint/build checks from `apps/web` and verify they pass or document any tooling/environment blocker.
- [x] 3.2 Run backend tests from `apps/api` and verify they pass or document any tooling/environment blocker.
- [x] 3.3 Run `openspec validate restrict-guest-product-actions --strict` and verify the change artifacts are valid.
