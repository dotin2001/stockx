## 1. Backend API

- [x] 1.1 Extend product detail API data with the lowest active sellable listing summary, and verify tests cover product with active listing, product with no listing, inactive listing exclusion, and archived product exclusion

## 2. Frontend API And Types

- [x] 2.1 Update frontend TypeScript DTOs for product lowest active listing, and verify `npm run web:typecheck` reaches the next unrelated issue or succeeds
- [x] 2.2 Add frontend API helpers for cart item update/remove where missing, and verify typecheck covers their request and response shapes
- [x] 2.3 Adjust API error handling call sites for cart/watchlist mutations so failed controls preserve previous UI state, and verify targeted component behavior through manual local interaction or component-level checks where available

## 3. Product Detail Actions

- [x] 3.1 Replace the product detail authenticated action panel with Add to Cart, Buy Now, Add to Watchlist, and Sell This Product controls using the lowest active listing, and verify product detail renders correctly for authenticated and guest states
- [x] 3.2 Disable or hide Add to Cart and Buy Now when no active listing is available while preserving watch and sell actions, and verify a seeded product with no active listing shows the unavailable purchase state
- [x] 3.3 Implement Buy Now as add-to-cart plus navigation to the account cart or checkout placeholder context, and verify it does not create orders, payments, or sold listings

## 4. Account Cart And Watchlist Controls

- [x] 4.1 Add cart quantity increase/decrease controls using existing cart update behavior, and verify increasing and decreasing refresh item quantity and total quantity in the account dashboard
- [x] 4.2 Add cart item removal controls, and verify removing one item updates the account dashboard without removing other cart items
- [x] 4.3 Add a checkout button and UI-first placeholder state in the account cart section, and verify the copy clearly indicates checkout is not available yet
- [x] 4.4 Add watchlist removal controls, and verify removing one watched product updates the account dashboard without removing other watched products

## 5. Verification

- [x] 5.1 Run backend tests with `cd apps/api && pytest` and verify cart, watchlist, product detail, and auth-protected behavior pass
- [x] 5.2 Run frontend checks with `npm run web:typecheck`, `npm run web:lint`, and `npm run web:build`, and verify no new TypeScript, lint, or build failures are introduced
- [x] 5.3 Smoke test signup/login, product detail Add to Cart, Buy Now placeholder, cart quantity controls, cart removal, watchlist removal, and logout against a local API/web session
