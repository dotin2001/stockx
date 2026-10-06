## Context

The seed currently upserts three categories and six products. Listings require a user owner, while a fresh database has no users. The static storefront already contains representative product names, prices, and images.

## Goals / Non-Goals

**Goals:** deterministic five-product category seeds, optional admin-owned stock, repeatable reconciliation, and no new credentials.

**Non-Goals:** schema migrations, multiple sizes per product, production catalog management, or dynamic pricing.

## Decisions

- Keep `python -m app.db.seed` as product-only seeding. Add an optional inventory-owner email argument for inventory after an existing user is promoted.
- Reuse nine additional products from the repository's static storefront rather than making seed-time network requests.
- Give each product a namespaced deterministic seed SKU, with representative sizes `10`, `M`, and `One Size` by category.
- Reconcile the selected owner's managed seed listing to active USD inventory with quantity 10 and the configured price. Leave other owners and variants unchanged.
- Validate the normalized owner email and admin flag before inventory mutation, then commit the reconciliation atomically.

## Risks / Trade-offs

- [Remote images may disappear] -> Reuse existing repository URLs and keep production storage out of scope.
- [Reseeding resets managed demo stock] -> Use visible seed SKUs and document reset semantics.
- [No listing uniqueness constraint] -> Match owner, product, and deterministic seed variant and test double execution.

## Migration Plan

Add the product definitions and optional inventory workflow, run catalog seed, then run inventory seed with an existing promoted admin. No schema rollback is required.
