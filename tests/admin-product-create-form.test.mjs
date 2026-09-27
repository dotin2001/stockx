import { readFile } from "node:fs/promises";
import test from "node:test";
import assert from "node:assert/strict";

const formSource = await readFile("apps/web/components/admin/admin-product-form.tsx", "utf8");
const productManagementSource = await readFile("apps/web/components/admin/admin-products-panel.tsx", "utf8");
const productManagementPageSource = await readFile("apps/web/app/admin/products/page.tsx", "utf8");
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
  assert.match(headerSource, /\/admin\/products/);
  assert.doesNotMatch(headerSource, /\/admin\/products\/new/);
  assert.match(productManagementSource, /\/admin\/products\/new/);
});

test("admin product management route includes access and data states", () => {
  assert.match(productManagementPageSource, /AdminProductsPanel/);
  assert.match(productManagementSource, /Loading admin products/);
  assert.match(productManagementSource, /Login required/);
  assert.match(productManagementSource, /Admin required/);
  assert.match(productManagementSource, /Could not load products/);
  assert.match(productManagementSource, /No managed products found/);
});

test("admin product management includes filters and product scanning", () => {
  assert.match(productManagementSource, /Scan products/);
  assert.match(productManagementSource, /Catalog/);
  assert.match(productManagementSource, /Inventory/);
  assert.match(productManagementSource, /Active/);
  assert.match(productManagementSource, /Archived/);
  assert.match(productManagementSource, /In stock/);
  assert.match(productManagementSource, /Out of stock/);
});

test("admin product management includes catalog and variant actions", () => {
  assert.match(productManagementSource, /api\.updateAdminProduct/);
  assert.match(productManagementSource, /api\.archiveAdminProduct/);
  assert.match(productManagementSource, /api\.restoreAdminProduct/);
  assert.match(productManagementSource, /api\.createAdminProductVariant/);
  assert.match(productManagementSource, /api\.updateAdminProductVariant/);
  assert.match(productManagementSource, /api\.deleteAdminProductVariant/);
  assert.match(productManagementSource, /Save Product/);
  assert.match(productManagementSource, /Create Variant/);
  assert.match(productManagementSource, /Remove/);
});

test("admin product management gates inventory controls to supreme admins", () => {
  assert.match(productManagementSource, /user\.is_supreme_admin/);
  assert.match(productManagementSource, /Supreme admin required/);
  assert.match(productManagementSource, /api\.adjustAdminListingQuantity/);
  assert.match(productManagementSource, /api\.updateAdminListingStatus/);
  assert.match(productManagementSource, /Set Status/);
  assert.match(productManagementSource, /currently available/);
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
