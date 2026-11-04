## Context

See `proposal.md` for motivation and `specs/host-check-authoritative-status-sync/spec.md` for the behavior contract. Fresh status sync currently collects trusted host checks, constructs a large semantic inventory, invokes read-only Codex, validates complete semantic coverage, and derives the Project target from the resulting report. This allows semantic classifications to override a fully passing executable check set.

The runner already has deterministic check entries with `PASS`, `FAIL`, or `BLOCKED`, stable snapshot revalidation, exact pending-transition persistence, and safe Project mutation preparation. The change can therefore replace the target authority without weakening provenance or mutation safety.

## Goals / Non-Goals

**Goals:**

- Make the complete required host-check set the sole status-routing authority.
- Produce `Done` deterministically when every selected check passes.
- Preserve actionable `Review` and `Blocked` routing for host failures and unavailable prerequisites.
- Keep records and terminal output explicit about the new completion basis.
- Retain all provenance, snapshot, retry, credential, and mutation boundaries.

**Non-Goals:**

- Expand or shrink the path-based verification command selection in this change.
- Claim that host checks prove requirements not encoded in executable verification.
- Modify apply-time validation or planning behavior.
- Remove semantic-review modules that may remain useful to a future advisory command.
- Edit issues, commit, push, merge, or publish.

## Decisions

### Derive status directly from check results

After collecting the stable path-selected check set, aggregate it with strict precedence:

1. Any `FAIL` produces `Review`.
2. Otherwise any `BLOCKED` produces `Blocked`.
3. Otherwise a non-empty all-`PASS` set produces `Done`.

This mirrors the useful portion of current report routing while removing semantic entries from the decision. A dedicated host-check derivation helper is preferred over fabricating semantic PASS entries because the latter would misleadingly claim requirements were reviewed.

Alternative considered: allow semantic review to run but ignore its result when checks pass. This wastes model time and can still introduce malformed-output failure paths, so the all-pass path will not invoke Codex.

### Keep path-selected verification rather than hard-code four global commands

The authoritative set remains the output of the trusted verification policy. For the current backend/runner patch that set is strict OpenSpec validation, `git diff --check`, `python -m pytest`, and `npm test`; other path sets continue to select their applicable frontend or backend commands.

Alternative considered: always run exactly four commands. This would run irrelevant suites for unrelated changes and would weaken the existing path-policy abstraction.

### Revalidate the snapshot and linked issue before Project preparation

After checks complete, recompute the exact review snapshot and refresh the linked issue identity exactly as the current workflow does. An all-pass result is not sufficient if the reviewed object changed or provenance drifted.

### Persist deterministic check evidence without semantic claims

Run records will retain the check entries, verification summary, derived/effective target, completion basis, and pending/synchronized mutation. Terminal output will list failed or blocked checks when present and state that all-pass Done came from trusted host verification. `reviewReport` may be omitted or replaced with a bounded host-check report, but it MUST NOT contain invented requirement PASS results.

Backward-compatible record readers must continue to understand earlier semantic-review records and pending transitions. Existing synchronized Review/Blocked records remain re-reviewable.

### Preserve exact pending transition recovery

The runner will persist the selected status intent before calling GitHub. A retry continues to use only the recorded item, field, option, and target; it does not rerun checks. This behavior is independent of the evidence source.

## Risks / Trade-offs

- [Passing tests do not cover every acceptance criterion] → Document the breaking policy clearly and require important acceptance behavior to be encoded in trusted checks.
- [Operators misread Done as semantic acceptance] → Record and print `trusted-host-verification` as the completion basis.
- [A check set is unexpectedly narrow] → Preserve the trusted path policy and test selection for backend, frontend, infrastructure, runner, and documentation paths.
- [Snapshot changes after checks] → Retain exact post-check snapshot and issue revalidation before any Project mutation.
- [Older records become unreadable] → Keep additive record fields and compatibility tests for existing semantic records and pending retries.

## Migration Plan

1. Add a deterministic host-check target derivation helper and unit tests for all-pass, fail, blocked, and mixed outcomes.
2. Refactor fresh status sync to use check results directly and skip semantic context/Codex/report validation on the all-pass path.
3. Preserve stable snapshot and issue revalidation before status preparation.
4. Update completion-basis metadata, terminal output, and run-record assertions.
5. Update status-sync integration tests, repository guidance, and operator documentation.
6. Run the full runner suite and strict OpenSpec validation.

Rollback restores semantic review as the status gate while retaining backward-compatible reads of host-authoritative run records and any already synchronized Project status.
