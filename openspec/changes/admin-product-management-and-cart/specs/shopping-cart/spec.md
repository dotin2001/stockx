## Purpose

Defines authenticated customer cart behavior for adding active marketplace listings to a cart, viewing current cart contents, updating quantities, and removing cart items before checkout exists.

## ADDED Requirements

### Requirement: Authenticated users can view their cart
The system SHALL allow authenticated users to view only their own cart items with enough product and listing information for frontend display.

#### Scenario: Cart view returns current user's items
- **WHEN** an authenticated user requests their cart
- **THEN** the system returns only cart items owned by that user

#### Scenario: Empty cart returns an empty list
- **WHEN** an authenticated user with no cart items requests their cart
- **THEN** the system returns an empty cart response

#### Scenario: Anonymous cart view is rejected
- **WHEN** an unauthenticated client requests a cart
- **THEN** the system rejects the request with an authentication error

### Requirement: Authenticated users can add active listings to cart
The system SHALL allow authenticated users to add active sellable listings for non-archived products to their cart.

#### Scenario: Add active listing succeeds
- **WHEN** an authenticated user adds an active listing for a non-archived product to their cart
- **THEN** the system creates or updates a cart item and returns the updated cart item data

#### Scenario: Add same listing merges quantity
- **WHEN** an authenticated user adds a listing that is already in their cart
- **THEN** the system increases or replaces the cart item quantity according to the request without creating a duplicate cart item for the same user and listing

#### Scenario: Add missing listing is rejected
- **WHEN** an authenticated user adds a listing that does not exist
- **THEN** the system returns a not-found error

#### Scenario: Add inactive listing is rejected
- **WHEN** an authenticated user adds a listing that is sold, cancelled, or otherwise inactive
- **THEN** the system rejects the request without creating a cart item

#### Scenario: Add listing for archived product is rejected
- **WHEN** an authenticated user adds a listing whose product is archived
- **THEN** the system rejects the request without creating a cart item

#### Scenario: Anonymous add to cart is rejected
- **WHEN** an unauthenticated client attempts to add a listing to a cart
- **THEN** the system rejects the request with an authentication error

### Requirement: Authenticated users can update cart item quantity
The system SHALL allow authenticated users to update quantities for their own cart items before checkout exists.

#### Scenario: Quantity update succeeds
- **WHEN** an authenticated user updates one of their cart items with a valid positive integer quantity
- **THEN** the system updates the item and returns the updated cart item data

#### Scenario: Invalid quantity is rejected
- **WHEN** an authenticated user updates a cart item with a non-positive or non-integer quantity
- **THEN** the system rejects the request with a validation error

#### Scenario: Cross-user quantity update is rejected
- **WHEN** an authenticated user attempts to update another user's cart item
- **THEN** the system returns a not-found or forbidden-style response without changing the other user's cart item

### Requirement: Authenticated users can remove cart items
The system SHALL allow authenticated users to remove their own cart items.

#### Scenario: Remove cart item succeeds
- **WHEN** an authenticated user removes one of their cart items
- **THEN** the system deletes that cart item from the user's cart

#### Scenario: Cross-user cart item removal is rejected
- **WHEN** an authenticated user attempts to remove another user's cart item
- **THEN** the system returns a not-found or forbidden-style response without deleting the other user's cart item

#### Scenario: Removing missing cart item is rejected
- **WHEN** an authenticated user removes a cart item that does not exist
- **THEN** the system returns a not-found error

### Requirement: Cart items remain user-scoped and listing-scoped
The system SHALL persist cart items as user-owned references to listings and prevent duplicate cart rows for the same user and listing.

#### Scenario: Duplicate user listing cart row is prevented
- **WHEN** the same user attempts to store the same listing in their cart more than once
- **THEN** the system keeps a single cart item for that user and listing

#### Scenario: Different users can cart the same listing
- **WHEN** different authenticated users add the same active listing to their carts
- **THEN** the system stores separate cart items scoped to each user

### Requirement: Cart view reflects listing availability
The system SHALL identify cart items whose listing or product is no longer available for purchase.

#### Scenario: Cart item becomes unavailable when listing is inactive
- **WHEN** a listing already in a cart becomes sold, cancelled, or otherwise inactive
- **THEN** the cart response indicates that the item is unavailable for purchase

#### Scenario: Cart item becomes unavailable when product is archived
- **WHEN** a product for a listing already in a cart becomes archived
- **THEN** the cart response indicates that the item is unavailable for purchase
