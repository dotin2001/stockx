## Why

The backend now supports auth, admin catalog management, listings, watchlists, and cart operations, but several marketplace edge cases are still too permissive or fragile for a frontend-backed workflow. This change hardens the foundation before checkout and richer account pages are added.

## What Changes

- Prevent new listings for archived products while preserving existing listings and historical references.
- Add authenticated listing lifecycle operations so sellers can view their listings and cancel active listings they own.
- Add admin listing management so admins can inspect and cancel listings when moderation or data cleanup is needed.
- Make duplicate-sensitive writes return stable API errors under database constraint races, including product slug conflicts and duplicate cart item merges.
- Add a project-supported admin bootstrap command for promoting an existing user to admin in local and deployed environments.
- Update tests, smoke coverage, and backend documentation for these hardened flows.

## Capabilities

### New Capabilities

- `listing-management`: Seller and admin listing lifecycle behavior, including archived-product listing rejection.
- `marketplace-write-integrity`: Stable behavior for duplicate-sensitive marketplace writes under database uniqueness races.
- `admin-bootstrap`: Backend-supported command behavior for safely granting initial admin access.

### Modified Capabilities

- None. The related admin product management and shopping cart behavior currently exists in completed change deltas that have not been archived into main specs.

## Impact

- Affected FastAPI routes: `/api/v1/listings`, `/api/v1/admin`, and existing cart/admin product write paths.
- Affected backend services: listings, cart, admin product management, and a new admin bootstrap command module.
- Affected persistence: likely no required schema change, but implementation may add database-level or service-level conflict handling around existing unique constraints.
- Affected verification: backend tests, smoke test, README route documentation, and OpenSpec validation.
