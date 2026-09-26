import { readFile } from "node:fs/promises";
import test from "node:test";
import assert from "node:assert/strict";

const formSource = await readFile("apps/web/components/admin/admin-product-form.tsx", "utf8");
const headerSource = await readFile("apps/web/components/layout/site-header.tsx", "utf8");
const adminUsersSource = await readFile("apps/web/components/admin/admin-users-panel.tsx", "utf8");
const sellPageSource = await readFile("apps/web/app/sell/page.tsx", "utf8");

test("admin product route source includes guest, non-admin, and admin form states", () => {
  assert.match(formSource, /Login required/);
  assert.match(formSource, /Admin required/);
  assert.match(formSource, /Product creation is admin-only/);
  assert.match(formSource, /Category/);
  assert.match(formSource, /Product name/);
  assert.match(formSource, /Price in USD/);
  assert.match(formSource, /Initial size/);
  assert.match(formSource, /Image URL/);
});

test("admin navigation is gated by is_admin", () => {
  assert.match(headerSource, /user\?\.is_admin/);
  assert.match(headerSource, /\/admin\/products\/new/);
});

test("supreme admin navigation and user management are gated by is_supreme_admin", () => {
  assert.match(headerSource, /is_supreme_admin/);
  assert.match(headerSource, /\/admin\/users/);
  assert.match(adminUsersSource, /Supreme admin required/);
  assert.match(adminUsersSource, /Promote by email/);
  assert.match(adminUsersSource, /Demote/);
});

test("sell page is store-managed and has no customer listing form", () => {
  assert.match(sellPageSource, /Selling is managed by the store/);
  assert.doesNotMatch(sellPageSource, /Create a listing/);
  assert.doesNotMatch(sellPageSource, /Seller registration/);
  assert.doesNotMatch(sellPageSource, /Image URL/);
});
