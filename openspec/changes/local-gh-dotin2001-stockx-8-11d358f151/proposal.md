## Why

Expired and long-revoked refresh-token rows currently accumulate without a safe, repeatable operator workflow. The backend needs an explicit retention boundary and PostgreSQL-backed cleanup command that reduces obsolete authentication data without endangering active tokens, replacement chains, or permanent business and payment records.

## What Changes

- Add an idempotent backend cleanup CLI that selects refresh tokens only when `expires_at` or `revoked_at` is at least 30 days before the run cutoff.
- Support dry runs, positive bounded batch sizes, deterministic reporting, and repeated execution without deleting protected records.
- Preserve active refresh tokens and maintain safe replacement relationships when eligible predecessor rows are removed.
- Treat `stripe_webhook_events` as a permanent deduplication ledger and exclude orders, payment attempts, listings, users, products, variants, audit data, and every record type lacking an explicit disposable designation and expiration timestamp.
- Add PostgreSQL coverage for retention boundaries, replacement links, dry runs, actual deletion, batching, idempotency, and protected-record retention.
- Document the recommended daily operator invocation and separate normal-suite and PostgreSQL-specific test commands, without adding a scheduler or hosted CI workflow.

## Capabilities

### New Capabilities

- `backend-retention-cleanup`: Defines safe, bounded, observable cleanup of explicitly eligible refresh-token records and operator execution requirements.

### Modified Capabilities

None.

## Impact

- Backend command entry points and a retention cleanup service under `apps/api`.
- PostgreSQL-specific backend tests and existing test-support conventions.
- Backend/database operator documentation.
- No API contract, database schema, deployment scheduler, GitHub Actions workflow, webhook retry behavior, or cleanup of business/payment ledgers is introduced.
