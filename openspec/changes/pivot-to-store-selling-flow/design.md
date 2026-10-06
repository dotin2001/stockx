## Context

See `proposal.md` for motivation. The current app already has public catalog browsing, guest cart storage/merge behavior, authenticated watchlist/cart APIs, admin product management, and a recently added admin product creation UI. It also has marketplace seller concepts: `seller_profiles`, `users.is_seller`, `/api/v1/seller/profile`, `/api/v1/listings`, `/sell`, product-detail "Sell This Product", and account dashboard listing/seller sections.

This change pivots the active product direction to a store-owned selling site. Normal users should act as customers only. Admins own store catalog and selling management. Supreme-admin hierarchy is intentionally deferred.

## Goals / Non-Goals

**Goals:**
- Remove customer-facing seller onboarding and user-created listing actions from the frontend.
- Enforce backend rejection for non-admin customer listing creation so hidden UI is not the only control.
- Keep existing guest cart, authenticated cart, watchlist, login/logout, and account behavior.
- Add a simple authenticated customer-to-admin message path with admin-protected read/update support.
- Keep legacy seller data from breaking existing local/dev databases while excluding it from active customer UX.

**Non-Goals:**
- Real payments, order creation, fulfillment, shipment tracking, or checkout completion.
- Supreme-admin role hierarchy, admin management, or permission management.
- Public seller marketplace behavior.
- Destructive cleanup of existing seller profile/listing data unless separately reviewed.

## Decisions

### Treat seller features as inactive rather than immediately deleting data

Deactivate customer-facing seller profile and listing flows first. Remove `/sell` links and replace the `/sell` page with a store-owned message explaining that selling is managed by the store, or redirect customers to catalog/account messaging. Keep database tables and models initially so existing migrations remain linear and local databases do not need destructive rollback.

Alternative considered: drop `seller_profiles` and `listings` immediately. That would simplify the domain but risks migration churn because carts currently point at listings and public products use lowest active listing as the sellable unit.

### Keep listings as the current inventory/price unit during this pivot

The existing cart and product detail behavior depends on active listings as sellable items. For this change, listings should be treated as store-owned inventory records, not user-created seller records. Customer listing creation must be rejected. Admin-created or seeded active listings remain usable for carts and product purchase actions.

Alternative considered: replace listings with a new `inventory_items` table now. That better matches a store but would expand the change into a deeper checkout/catalog refactor. A later inventory change can rename or replace listing internals after the UX is corrected.

### Backend enforcement must change before or with frontend removal

The frontend should stop showing seller controls, but the API must also reject non-admin listing creation. Existing `/api/v1/listings` behavior can either be removed from the router for customers or changed so write operations require admin/store ownership. Customer cart and watchlist APIs remain protected customer APIs.

Alternative considered: only hide the sell UI. That leaves a direct API path for customer-created inventory and contradicts the store-owned model.

### Customer-admin messaging is a small durable support channel

Add a customer message model with sender, subject/context, body, read state, and timestamps. Customers can create messages and optionally list their own messages. Admins can list, inspect, and mark messages read. This is enough for a first store-contact flow without building live chat or admin replies.

Alternative considered: use a mailto/contact link only. That avoids database work but gives admins no in-app queue and no testable customer message state.

### Do not add supreme-admin yet

Keep `users.is_admin` as the only admin check during this change. Name "normal admin" in UI/copy only where helpful, but do not add `is_supreme_admin`, role strings, or permission tables yet.

Alternative considered: introduce role hierarchy now. The user explicitly wants to request supreme admin later, so adding it now would create unnecessary migration and authorization design.

## Risks / Trade-offs

- Existing code and tests assume users can become sellers -> Update affected smoke/tests and copy so failures point at the new store-owned behavior.
- Cart currently depends on listings -> Preserve active listing reads as inventory while blocking customer-created listings.
- Legacy seller profiles may still exist in local databases -> Ignore them in customer UI and avoid exposing `is_seller` as a meaningful customer state.
- Admin messaging can grow into support chat later -> Keep the first model intentionally simple and append-only except read state.
- In-progress `enable-guest-cart-and-seller-onboarding` contains seller requirements -> Treat this change as superseding the seller portion while preserving guest cart behavior.

## Migration Plan

1. Frontend: remove seller navigation/action affordances from product detail, account dashboard, header/footer, and `/sell`; replace with buyer/account/message-admin paths.
2. Backend: reject customer listing creation and seller profile mutation for active store-owned flow, while keeping catalog/cart/listing availability behavior intact.
3. Database: add customer messages with a deterministic migration; do not drop seller tables in this change.
4. API: add authenticated customer message create/read-own endpoints and admin-protected message list/detail/read-state endpoints.
5. Tests: update seller expectations to store-owned behavior and add customer/admin messaging coverage.
6. Rollback: hide message UI and routes, downgrade message migration, and restore previous seller route behavior if the store pivot is reversed before production data depends on messages.
