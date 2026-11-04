## Context

The FastAPI backend already stores hashed refresh tokens, issues short-lived access tokens, and uses an HTTP-only refresh cookie. Correct hardening spans API routes, services, settings, PostgreSQL models/migrations, delivery integration, and concurrency tests. PostgreSQL is the production datastore and therefore the authority for cross-worker serialization. See `proposal.md` and `specs/authentication-hardening/spec.md` for scope and observable requirements.

## Goals / Non-Goals

**Goals:**

- Preserve existing auth response envelopes while making rotation, replay response, and registration conflicts deterministic under concurrency.
- Keep verification/reset responses and limiter keys privacy-preserving.
- Support multi-worker deployments with database-backed session coordination and a replaceable shared rate-limit store.
- Provide migration and test coverage for existing refresh-token chains.

**Non-Goals:**

- Replacing access-token signing or introducing third-party/social login.
- Requiring verified email for every existing protected operation; enforcement policy can be added separately.
- Building end-user frontend pages or selecting a production email vendor.
- Persisting raw refresh, verification, or reset tokens.

## Decisions

### Serialize refresh rotation with PostgreSQL row locks and token families

Add a non-null family identifier to refresh-token records while retaining replacement links. A refresh transaction looks up the token digest with `SELECT ... FOR UPDATE`, then distinguishes active, expired/revoked, and already-replaced states. An active token is revoked and linked to one replacement in the same transaction. A replaced token triggers revocation of all still-active family members before returning the stable auth error. New login creates a new family; logout-all revokes all active families for the user.

Process-local locks were rejected because they cannot coordinate multiple API workers. A uniqueness-only replacement scheme was rejected because family identity is still needed for replay containment.

### Backfill families by existing replacement-chain component

The migration derives one deterministic family for every connected, same-user replacement chain and an independent family for each unlinked token. It detaches malformed self-links and cross-user links before backfill, verifies that no row remains unclassified, then makes family identity non-null and adds family/revocation indexes.

Assigning every legacy token an unrelated family was rejected because replay of a rotated legacy token would not revoke its descendants. A single family per user was rejected because replay of one session would unnecessarily revoke unrelated sessions.

### Use digest-only, purpose-bound account challenges

Store verification and reset challenges in a dedicated table with user, purpose, digest, expiry, consumption time, and creation time. Generate high-entropy raw tokens only for delivery. Confirmation locks and consumes the matching challenge transactionally. Password reset also updates the password hash and revokes every user refresh token in that transaction. Public request endpoints return the same accepted response for known and unknown valid emails.

Embedding these tokens in user rows was rejected because multiple issuance, single-use history, and purpose separation become ambiguous. Reversible token storage was rejected because database disclosure would expose live credentials.

### Apply endpoint policies through a replaceable shared rate-limit interface

Define independent settings for registration, login, refresh, verification, and reset limits. Keys combine the endpoint policy with keyed digests of trusted client address and, when available, normalized account identity. Production uses an atomic shared store; an in-process implementation is limited to development/testing. Exceeded limits return `429 rate_limit_exceeded` with `Retry-After`. Store-unavailable behavior is explicit in configuration, with production defaulting to fail closed.

A single global counter was rejected because endpoint risk and expected traffic differ. Raw IP/email keys were rejected to avoid exposing personal data in the limiter store.

### Treat the database constraint as registration's final conflict authority

Validate email syntax before normalization and retain a friendly preflight lookup, but catch only recognized user-email uniqueness violations after insert/flush and translate them to HTTP 409 `email_exists`. Unknown integrity failures continue to propagate.

Relying only on preflight lookup was rejected because concurrent requests can both pass it. Translating every integrity error was rejected because it would mask unrelated defects.

## Risks / Trade-offs

- [Replay races can revoke the successor issued to the winning request] → This is intentional containment; clients must reauthenticate after replay is detected.
- [Row locks increase refresh latency during contention] → Keep the transaction small and index token digests and family revocation lookup paths.
- [Shared limiter outage can block authentication when fail-closed] → Expose clear operational errors and allow an explicit, documented fail-open policy only where risk permits.
- [Delivery failure can strand a newly issued challenge] → Report delivery failure without exposing the token; permit rate-limited reissue and expire stale challenges.
- [Legacy replacement links may be malformed] → Sanitize invalid links, derive deterministic components, and fail the migration if any family remains null.
- [Downgrading removes verification/challenge state and family grouping] → Require a maintenance window and compatible application rollback; document that new state is not preserved by downgrade.

## Migration Plan

1. Add nullable refresh-family and user-verification columns plus the account-challenge table and supporting constraints/indexes.
2. Sanitize malformed legacy replacement links, backfill deterministic family identifiers, verify every refresh row is classified, and make the family column non-null.
3. Deploy backend behavior and configuration for locking, replay revocation, challenges, rate limits, deterministic registration conflicts, and logout-all.
4. Run migration upgrade, backend tests, PostgreSQL concurrency tests, and the complete auth smoke flow before enabling production traffic.
5. For rollback, first restore a compatible application version, disable new verification/reset issuance, then downgrade. Treat issued action tokens and verification state as invalidated after downgrade and require reauthentication where session-family guarantees cannot be preserved.
