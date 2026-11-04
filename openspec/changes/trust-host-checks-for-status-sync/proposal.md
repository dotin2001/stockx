## Why

`--sync-status` can keep a delivery in `Review` or `Blocked` after every trusted host check passes because the semantic reviewer reports incomplete evidence or rejects task-level verification coverage. Operators want deterministic completion based on repository-owned executable checks: when every required host-selected check passes, the recorded Project item should become `Done` without semantic review overriding that result.

## What Changes

- Make trusted host verification authoritative for fresh `--sync-status` completion.
- Derive `Done` when every required path-selected host check passes; for the current backend/runner delivery those checks are strict OpenSpec validation, `git diff --check`, `python -m pytest`, and `npm test`.
- Skip the Codex semantic-review gate after all required host checks pass, preventing semantic coverage gaps or subjective task-evidence findings from downgrading a verified delivery.
- Preserve `Review` for any executed host check that fails and `Blocked` for failure-free host verification that cannot run because a prerequisite is unavailable.
- Preserve provenance, stable-snapshot validation, pending-transition recovery, exact Project mutation allowlisting, credential isolation, and the prohibition on issue/code publication side effects.
- Update local records, terminal reporting, documentation, and offline tests to make the host-authoritative completion basis explicit.
- **BREAKING**: Passing trusted host checks can now produce `Done` even when a semantic reviewer would have reported failed, blocked, ambiguous, or incomplete requirement coverage.

## Capabilities

### New Capabilities

- `host-check-authoritative-status-sync`: Defines deterministic Project status routing from the required trusted host-check results, with all-pass completion independent of semantic-review output.

### Modified Capabilities

None.

## Impact

- Affects `automation/ai-local/lib/runner.mjs`, review/status derivation helpers, run-record and terminal reporting, status-sync tests, `AGENTS.md`, and `docs/ai-local-openspec.md`.
- Does not change which verification commands are selected for a path set; it changes which evidence is authoritative for status routing.
- Reduces semantic assurance: passing executable checks become sufficient for `Done`, so acceptance-criteria completeness must be encoded in those checks.
- Maintains the existing GitHub mutation boundary: only the recorded Project item's recorded Status field may change.
