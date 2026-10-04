## Context

See `proposal.md` for motivation. The current backend already has products, variants, listings, cart items, watchlist items, product archive state, admin product APIs, and supreme-admin stock quantity/status controls. The current admin product UI can edit basic product fields, variants, and some inventory behavior, but public and admin surfaces still expose marketplace-oriented concepts such as lowest ask/listings. Public product detail currently returns variants and one lowest active listing, so customers cannot choose a specific size or stock record when multiple variants or prices exist.

## Goals / Non-Goals

**Goals:**

- Make the admin product editor the source of truth for customer-facing product content.
- Add structured storefront content that can support richer public product pages without hardcoding page copy.
- Preserve the existing cart/listing foundation while presenting stock as store inventory in UI and public API language.
- Let authorized admins update existing stock price and variant assignment in addition to quantity/status.
- Let product detail pages expose cartable variant purchase options, stock state, product stats, and related products.
- Keep admin authorization enforced in the backend.

**Non-Goals:**

- Replacing the `listings` table with a new inventory table in this change.
- Building checkout, payments, orders, shipments, reservations, or tax behavior.
- Adding seller marketplace behavior, public seller identity, bids, asks, or last-sale history.
- Building production asset uploads/storage; URL-based media remains acceptable for this foundation.
- Introducing a CMS, rich text editor, or external search/recommendation service.

## Decisions

### 1. Keep listings as the internal stock record for now

Use the existing `listings` table as the internal sellable stock record. Public and admin UI should call these records stock or inventory, and API response schemas can introduce store-oriented names while still serializing data from `Listing`.

Rationale: Cart items, guest carts, product detail, discovery, and admin inventory already depend on listing IDs as the cartable unit. Replacing that table now would cascade into carts and later checkout work.

Alternatives considered:

- Add a new `inventory_items` table now. This is cleaner domain language, but it expands the change into a migration-heavy cart refactor.
- Keep public "listing" terminology. This is less work, but it conflicts with the store-owned brand direction.

### 2. Add structured product content fields to products

Add persisted product content fields for customer-facing page sections, such as:

- `feature_bullets`: ordered list of short strings.
- `details`: structured key/value or label/value rows for materials, fit, care, dimensions, or product notes.
- `gallery_images`: ordered image URL records with optional alt text.

Use JSON-compatible PostgreSQL fields or a compact normalized child table only if validation or ordering needs become awkward. For this foundation, JSON fields on `products` are acceptable if backed by Pydantic validation and deterministic migration defaults.

Rationale: Admins need to edit product page features without code changes. Keeping the first model close to products avoids introducing a CMS before the product model stabilizes.

Alternatives considered:

- Store everything in one rich-text description. This is quick, but hard to validate, render consistently, or reuse in compact UI.
- Normalize each content section into separate tables. This is more flexible, but premature for the current scale and increases CRUD complexity.

### 3. Keep product price display derived from active stock

Public product cards and detail pages should prefer active positive-quantity stock prices for store price display. The existing product-level `lowest_ask_cents` should become legacy/fallback data or be renamed in API/frontend types over time; customer UI should not display "lowest ask."

Rationale: Active stock is the same truth cart behavior uses. A stale product-level price can confuse customers if variant-specific prices differ.

Alternatives considered:

- Keep product-level price as authoritative. Simpler, but wrong when variants have different prices or stock records change.
- Require one global price per product. Better for some stores, but too restrictive for size/color inventory differences already supported by variants.

### 4. Add stock update semantics instead of recreate-only workflows

Add an admin stock update route/payload that can update price, currency, quantity, status, and variant assignment for an existing stock record. Preserve existing quantity-adjustment routes if useful, but the complete editor should not require recreating stock to change price.

Rationale: "Admin can edit all product features" includes pricing and stock records. Recreate-only flows risk breaking cart references and create clutter.

Alternatives considered:

- Continue create + cancel + recreate. Avoids a new endpoint, but is awkward and can invalidate carted stock unnecessarily.
- Let normal admins mutate all stock fields. This is simpler, but current project behavior reserves sensitive inventory mutations for supreme admins.

### 5. Product detail returns purchase options and related products

Extend public product detail to include:

- `purchase_options`: active positive-quantity stock grouped or listed by variant.
- `selected` or frontend-derived default option: lowest priced in-stock option.
- `stats`: sold count, available size count, stock state, category, and brand when available.
- `related_products`: bounded product summaries from the same category and, when possible, matching brand affinity, excluding the current product.

Rationale: The product page can become richer while staying data-driven and consistent with discovery/cart behavior.

Alternatives considered:

- Fetch related products separately from the frontend. This keeps product detail smaller, but adds extra client coordination and makes smoke testing the complete product experience harder.
- Add a recommendation system. Not needed for the current catalog size.

### 6. Admin UI becomes a complete editor, not many disconnected panels

The existing admin products surface can evolve into a selected-product editor with sections for basics, media/content, variants, inventory, visibility, and preview links. Keep controls dense and operational rather than marketing-style.

Rationale: Admins need repeated product-management workflows, so the editor should prioritize scanning, quick saves, clear validation, and role-specific controls.

Alternatives considered:

- Build separate pages for each section. This may scale later, but would slow down current editing and require more routing.

## Risks / Trade-offs

- [JSON content shape drifts between backend and frontend] -> Use Pydantic schemas and TypeScript types for the exact shape, with backend tests and frontend build verification.
- [Listing/inventory naming mismatch causes confusion in code] -> Keep service names compatible where needed, but introduce API/UI aliases and comments around the temporary internal mapping.
- [Variant deletion can affect stock option display] -> Preserve current `ON DELETE SET NULL` listing behavior; public product detail should label stock without a missing variant as base product.
- [Related product queries become slow later] -> Reuse bounded discovery/category queries now; add indexes or recommendation tables only when catalog size requires it.
- [Changing public price semantics can expose stale product-level data] -> Prefer active stock prices in public UI and treat product-level price as fallback only when no active stock exists.
- [Inventory edits can affect carted items] -> Existing cart availability responses should continue to mark unavailable or quantity-limited items rather than silently deleting them.

## Migration Plan

1. Add product content fields with safe defaults and downgrade behavior.
2. Update backend schemas for product content, purchase options, stock update payloads, and managed product reads.
3. Add stock update service/API behavior with existing authorization rules.
4. Extend product detail serialization to include purchase options, stats, and related product summaries.
5. Update admin product editor UI sections and store-language labels.
6. Update public product cards/detail UI to use store price/stock language and selected purchase options.
7. Add focused backend tests, frontend build/lint checks, and smoke checks for admin edit, public product detail, and carting selected inventory.

Rollback: hide the new UI sections, ignore the added response fields, and downgrade the product content migration. Existing product, variant, listing, cart, and watchlist records remain intact because the change is additive around current relationships.

## Open Questions

- The first implementation can use URL-based gallery images. A later production image-upload/storage change can replace those URLs without changing this capability's customer-visible behavior.
