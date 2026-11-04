## Context

The API currently loads a singleton settings object at import time, permits development defaults, exposes only a database-independent `/health`, and configures CORS directly from a comma-separated origin list. Stripe configuration already validates several cross-field invariants, but production is not a first-class environment profile.

Authentication stores hashed refresh tokens and replacement links, but rotation reads without a row lock and has no family identity or replay-family revocation. Registration already translates known PostgreSQL email uniqueness violations to `email_exists`; that behavior must remain stable as stronger validation and account lifecycle state are added. There is no verification/reset state, authentication limiter, global logout, request-correlation middleware, external error reporter, or general audit ledger. Payment events and attempts are durable but monitoring is command/log ad hoc. Python dependencies are mostly lower-bounded ranges rather than locked.

## Goals / Non-Goals

**Goals:**

- Make unsafe production deployments fail before accepting traffic while keeping explicit local development usable.
- Define transactional session replay handling and account lifecycle state that remain correct under PostgreSQL concurrency.
- Add operational diagnostics and audit evidence with strict data minimization.
- Make dependency installation deterministic for the supported Python runtime.

**Non-Goals:**

- Selecting or operating a particular email delivery, telemetry, log aggregation, or error-reporting vendor.
- Adding MFA, social login, changing JWT signing algorithms, or replacing HTTP-only refresh cookies.
- Building frontend verification/reset/admin-audit screens.
- Creating a general event-sourcing framework or changing Stripe's authority over payment confirmation.

## Decisions

### Use an explicit environment profile with fail-fast cross-field validation

Add a bounded application-environment setting, with production enabling stricter validators for signing-secret quality, secure cookie policy, HTTPS non-local CORS origins, and Stripe consistency. Keep development defaults only outside production. Normalize origins before duplicate checks and return setting names, never values, in errors. This extends the existing Pydantic settings boundary instead of scattering runtime checks through routes. An external preflight script was rejected because every entry point must enforce the same invariants.

### Model refresh rotation as a database-serialized token-family state machine

Add a non-null family identifier to refresh tokens and retain replacement linkage. Refresh looks up the digest, locks the token row, then distinguishes active, expired/revoked, and already-replaced states. A valid active token is revoked and replaced in one transaction; a replaced token triggers bulk revocation of every unrevoked token in the family. New login creates a new family, while logout-all revokes all families for the user. PostgreSQL row locking is the production concurrency authority; process-local locks were rejected because they do not work across workers.

Replay detection must not treat ordinary logout or expiration as proof of theft. Only a token with replacement evidence triggers family revocation. Responses remain generic so family topology is not disclosed.

### Store verification and reset challenges as dedicated hashed, expiring records

Use purpose-specific records with random opaque tokens, digests, expiry, consumption time, and user ownership. Verification updates a user verification timestamp. Password reset consumes its challenge, changes the password hash, and revokes all sessions in one transaction. Request endpoints always return an indistinguishable accepted response and delivery occurs through an interface with a local capture/test implementation and a production-configured adapter. JWT-encoded action links were rejected because server-side single use and emergency revocation are requirements.

### Apply endpoint-specific rate limits through a replaceable shared-store interface

Place limiting before expensive password hashing or outbound delivery. Keys combine endpoint policy with a privacy-preserving digest of canonical email where available and a trusted client address derived only from explicitly configured proxy handling. Policies are configured per endpoint and emit 429 plus `Retry-After`. The interface supports deterministic in-memory tests and a production shared backend; an in-process-only production limiter was rejected because multiple workers would enforce inconsistent limits.

### Preserve database authority for canonical email conflicts

Use a standards-aware email validator before canonical normalization, retain database uniqueness as the final arbiter, and map only recognized user-email constraints to `email_exists` after rollback. Broadly translating every integrity error was rejected because it would hide unrelated defects.

### Add one outer request-context middleware and structured event schema

The outer middleware validates or generates a bounded request ID, stores it in request context, returns it on every response, and records one completion event using the matched route template rather than raw path parameters. Error handlers and background/operator commands use the same structured event helper. Sanitization is allowlist-based; bodies, credentials, tokens, cookie values, and provider payloads are never log fields.

Unexpected errors are sent through a small reporter interface with bounded time/failure isolation. Payment code emits categorized state-transition and reconciliation summaries from existing durable payment records. This avoids making a telemetry vendor part of domain code.

### Separate liveness, readiness, and operational payment signals

Keep liveness process-only. Add a readiness endpoint with a short bounded `SELECT 1` probe and sanitized failure response. Payment monitoring derives counts and alerts from webhook status, payment-attempt status/age, reservation expiry, and reconciliation results rather than introducing a second payment state store.

### Use an append-only audit table written inside privileged transactions

Add an audit table with actor, action, typed target, request ID, timestamp, and JSON before/after facts. Services write allowlisted snapshots in the same transaction as admin-role and inventory changes. A read-only, paginated administrator endpoint supports bounded filters; application APIs provide no update/delete route. Generic request-body capture was rejected because it risks collecting secrets and unstable data.

### Commit a generated transitive lock for production and development groups

Retain `pyproject.toml` as the human-edited direct dependency declaration and use a standard Python lock workflow compatible with editable project installs and Python 3.12. CI/test setup installs from the lock and checks that regeneration is clean. Resolve warnings by upgrading locked dependencies or replacing deprecated project usage, then run tests with actionable deprecations treated as errors. Hand-pinning only direct dependencies was rejected because transitive resolution would remain variable.

## Risks / Trade-offs

- [Replay family revocation can sign out a legitimate client after a duplicated request] → Serialize rotation, document single-use refresh semantics, and return a recoverable authentication failure requiring login.
- [Adding non-null family identifiers to existing tokens can make migration unsafe] → Backfill each existing token chain deterministically before enforcing non-null/index constraints and test upgrade/rollback against PostgreSQL.
- [Rate-limit store failure can weaken protection or reduce availability] → Define explicit production startup requirements and a documented fail-closed policy for sensitive delivery endpoints while keeping health diagnostics available.
- [Email delivery outages can block verification/recovery] → Commit challenge state before queued delivery, use generic responses, expose delivery failures operationally, and allow rate-limited reissue.
- [Structured telemetry or audit metadata can still leak personal data] → Use field allowlists, length bounds, identifiers rather than payloads, and tests that assert forbidden values are absent.
- [Strict production validation may break existing deployments] → Introduce the environment profile and readiness checks before requiring production mode, and document every newly required setting.
- [Large dependency upgrades can introduce regressions] → Regenerate the lock in reviewable increments and run the full backend and PostgreSQL verification suite.

## Migration Plan

1. Add migrations for refresh families, user verification state, action challenges, and audit records. Backfill existing refresh-token families and verify constraints before making family identity required.
2. Deploy schema-compatible code that understands old sessions after backfill, but require fresh login if a legacy record cannot be safely classified.
3. Configure the shared rate-limit store, delivery adapter, reporter, allowed production origins, secure cookies, strong signing secret, and consistent Stripe production settings in staging.
4. Exercise concurrent refresh/replay, concurrent registration, verification/reset, global logout, readiness failure, telemetry sanitization, audit atomicity, and payment monitoring in staging.
5. Install from the lock, run the complete backend/PostgreSQL suite with deprecation checks, then enable the production environment profile.

Rollback the application to the previous compatible version before reversing migrations. Do not remove new columns/tables until old application versions are restored and new verification/reset flows are disabled; existing refresh sessions may be revoked to restore a known-safe baseline.
