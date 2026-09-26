import { readFile } from "node:fs/promises";
import test from "node:test";
import assert from "node:assert/strict";

const productDetailSource = await readFile("apps/web/components/catalog/product-detail-view.tsx", "utf8");
const accountSource = await readFile("apps/web/components/auth/account-dashboard.tsx", "utf8");
const cartSource = await readFile("apps/web/components/cart/cart-page-client.tsx", "utf8");
const sellPageSource = await readFile("apps/web/app/sell/page.tsx", "utf8");
const adminMessagesSource = await readFile("apps/web/components/admin/admin-messages-panel.tsx", "utf8");
const adminUsersSource = await readFile("apps/web/components/admin/admin-users-panel.tsx", "utf8");
const headerSource = await readFile("apps/web/components/layout/site-header.tsx", "utf8");

test("product detail keeps buyer actions and removes seller actions", () => {
  assert.match(productDetailSource, /Add to Cart/);
  assert.match(productDetailSource, /Buy Now/);
  assert.match(productDetailSource, /Add to Watchlist/);
  assert.doesNotMatch(productDetailSource, /Sell This Product/);
  assert.doesNotMatch(productDetailSource, /Log in to Watch or Sell/);
});

test("account dashboard is customer focused with message admin", () => {
  assert.match(accountSource, /Customer account/);
  assert.match(accountSource, /Message Admin/);
  assert.match(accountSource, /Send Message/);
  assert.match(accountSource, /Checkout/);
  assert.doesNotMatch(accountSource, /Seller account active/);
  assert.doesNotMatch(accountSource, /Create a listing/);
});

test("sell route is informational and not a customer seller form", () => {
  assert.match(sellPageSource, /Selling is managed by the store/);
  assert.doesNotMatch(sellPageSource, /Register Seller/);
  assert.doesNotMatch(sellPageSource, /Create Listing/);
});

test("guest cart preserves checkout login gate", () => {
  assert.match(cartSource, /Guest cart/);
  assert.match(cartSource, /Login or sign up to continue checkout/);
  assert.match(cartSource, /\/login\?redirect=/);
});

test("admin messages are admin gated", () => {
  assert.match(adminMessagesSource, /Admin required/);
  assert.match(adminMessagesSource, /Customer messages/);
  assert.match(adminMessagesSource, /Mark Read/);
  assert.match(headerSource, /\/admin\/messages/);
  assert.doesNotMatch(headerSource, />\\s*Sell\\s*</);
});

test("admin user management is supreme admin gated", () => {
  assert.match(adminUsersSource, /Supreme admin required/);
  assert.match(adminUsersSource, /api\.listAdminUsers/);
  assert.match(adminUsersSource, /api\.promoteAdminUser/);
  assert.match(adminUsersSource, /api\.demoteAdminUser/);
  assert.match(headerSource, /user\.is_supreme_admin/);
});
