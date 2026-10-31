## Context

See `proposal.md` for motivation. The current status-sync preflight calls `findPendingStatusRecord` and therefore rejects every change without a previously recorded pending transition. The apply validator already provides most completion primitives: normalized approved-plan hashing ignores task checkbox state, implementation scope rejects protected authority paths, task completeness is checked, strict OpenSpec validation runs, and changed paths select trusted verification commands. Those primitives currently operate only in an isolated apply worktree.

The required operator sequence is deliberately split across two trusted hosts: `ai:local` creates and records the GitHub-backed plan, the project-local `$openspec-apply-change` workflow implements and verifies it, and a later `ai:local --sync-status` invocation re-verifies the resulting checkout before updating the recorded Project item. A successful `ai:local --apply` run is an alternative path, not a prerequisite for this sequence.

The runner must continue treating GitHub credentials and mutation as host-only capabilities. A completed task list by itself is insufficient evidence: issue content and OpenSpec artifacts are untrusted, and an operator can have unrelated or unsafe checkout changes.

## Goals / Non-Goals

**Goals:**

- Keep the existing `--sync-status <change-name>` syntax and pending-retry semantics.
- Add a no-model verified-completion fallback for GitHub-backed OpenSpec changes implemented through `$openspec-apply-change`.
- Reuse approved-plan identity, scope protection, and trusted verification policy instead of creating a weaker parallel validator.
- Persist the transition intent before remote mutation so failures become ordinary retryable syncs.
- Keep failure paths non-mutating except for sanitized local run metadata.

**Non-Goals:**

- Inferring completion from GitHub issue checkboxes or OpenSpec task markers alone.
- Supporting automatic `Blocked` classification without a structured apply result.
- Accepting committed, staged, pushed, or remotely merged implementations as local completion evidence.
- Closing issues, commenting, editing issue bodies, or changing any Project field other than the recorded status field.
- Allowing status sync to modify runner authority, skills, prompts, schemas, or configuration.

## Decisions

### 1. Resolve status-sync evidence in priority order

Preflight will resolve one of three states:

1. A unique pending transition: retain the existing retry path exactly.
2. An already synchronized terminal record: return or confirm the idempotent terminal result without revalidating implementation.
3. No terminal transition: locate the unique successful plan record and enter verified-completion preflight.

Failed `ai:local --apply` records do not satisfy any of these evidence states: they cannot authorize a Project mutation. They also do not block the third state, because the unique successful plan plus the current completed implementation are independently revalidated. This permits an operator to recover from a technical runner failure by completing the same approved change with `$openspec-apply-change` and then synchronizing it.

Ambiguous pending or successful plan records remain hard failures. An alternative of always revalidating was rejected because a remote-only retry must not become dependent on the later checkout state or test environment. An alternative of treating any failed apply record as permanently disqualifying was rejected because technical failures are not plan invalidation and carry no terminal status authority.

### 2. Verify the current unstaged checkout against the approved plan

The completion fallback will inspect an attached worktree without staging or writing it. It will require no staged entries, collect modified/deleted/untracked paths, require the selected change's `tasks.md`, require at least one non-plan path, and pass the paths through the existing implementation authority and verification-policy checks. The current approved plan hash must equal the successful plan record's digest; normalized hashing already permits only checkbox changes in `tasks.md`.

The validator then runs task completeness, `openspec validate <change> --strict`, `git diff --check`, and the existing path-selected checks. Apply-specific test environment forwarding, including `TEST_POSTGRES_DATABASE_URL`, is reused without persisting secrets.

An alternative of trusting the 15/15 OpenSpec count was rejected because it provides no evidence that implementation paths are safe or tests pass. An alternative of diffing from the plan record's original commit was rejected because reviewed plans can be committed before implementation and unrelated commit history is not the local patch contract.

### 3. Separate verification from Project preparation and mutation

For the fallback path, all local completion checks run before the GitHub adapter is asked to prepare a status update. The `--sync-status` invocation is the operator's explicit approval to perform this verification and, if it succeeds, synchronize `Done`. After checks pass, the runner writes a linked `sync-status` record containing changed paths, verification names, and a `verified-completion` basis. It then prepares the exact recorded Project item, writes `statusSync.state = pending` with target `done`, and only then calls the existing update adapter.

This ordering prevents invalid local work from causing even a preparatory remote dependency and preserves a durable retry intent if mutation fails. The pending retry path continues to perform no local verification.

### 4. Reuse run-record version 3 with additive provenance

The existing record shape already supports linked plan identity, changed paths, verification, errors, and status state. Add a sanitized completion-basis value such as `verified-completion` or `pending-retry` rather than advancing the version and invalidating existing plan records. Lookup remains backward compatible with existing version-3 records.

An alternative new record version was rejected because no existing field changes meaning and old successful plan/pending records must remain usable.

### 5. Make repeated synchronization idempotent

Once a synchronized `Done` record exists, repeating the command must not create competing pending records or rerun expensive tests. The runner may verify the recorded Project identity/status through the existing adapter, but it cannot select a new target. Remote `Done` discovered after an uncertain prior update is accepted as success for the same recorded item and option.

## Risks / Trade-offs

- [A manually produced patch can be semantically unrelated while still passing its planned checks] → Require explicit operator invocation, unchanged approved contract, scoped paths, non-empty implementation, and the full trusted policy; retain the same limitation already inherent in human review of local patches.
- [Verification commands can be expensive] → Run them only when no pending or synchronized transition exists; retries remain remote-only.
- [Untracked-path inspection could accidentally stage intent-to-add entries] → Implement a read-only status/path collector rather than reusing diff capture that calls `git add -N`.
- [Tests can modify an explicitly configured test database] → Reuse apply-only environment forwarding and existing guarded test conventions; never persist or print the URL.
- [Concurrent sync invocations could create two verified records] → Re-read pending/synchronized evidence immediately before mutation and fail on ambiguity; atomic run-record writes and idempotent Project updates bound the effect.
- [A change modifies protected runner authority] → Reuse the existing protected-path rejection, so such changes cannot self-authorize a Project transition through this fallback.

## Migration Plan

1. Add read-only completion checkout inspection and status evidence resolution while keeping existing pending lookup compatibility.
2. Add verified-completion orchestration and additive run-record provenance.
3. Extend offline tests for retry priority, all refusal paths, successful verification, failed remote update recovery, idempotency, secret redaction, and absence of Codex/patch/publication actions.
4. Update operator documentation and CLI help text to describe retry-or-verify semantics.
5. Rollback removes the fallback path and documentation; existing pending and synchronized records remain compatible with the original retry-only behavior.
