## Why

`--sync-status` currently verifies only the current unstaged delta against an approved OpenSpec plan and can mark a Project item `Done` without reviewing committed work since the recorded base or checking the linked issue's acceptance criteria. Step 3 needs to become a read-only, evidence-backed review that proves provenance, evaluates every requirement, and routes incomplete or unverifiable work to an actionable non-Done status.

## What Changes

- Make `npm run ai:local -- --sync-status <change-name>` read the successful plan run record and verify the exact linked GitHub Project item, issue content identity, recorded branch, and recorded base commit before reviewing code.
- Stop with a local error and no Project mutation when the issue, branch, or base commit cannot be verified.
- Review the complete base-to-current change set, including commits after the recorded base plus staged, unstaged, deleted, and untracked files, without staging or modifying implementation files.
- Validate the implementation against both the linked issue's acceptance criteria and the approved OpenSpec proposal, specifications, design, and required tasks.
- Run strict OpenSpec validation and every trusted verification command selected by the complete changed-path set.
- Generate a bounded, sanitized report that marks each issue criterion, OpenSpec requirement/task, and required check `PASS`, `FAIL`, or `BLOCKED`, with supporting evidence and remaining work.
- Derive the Project status from the report rather than allowing Codex to select a target: all requirements and checks passing routes to `Done`; any failure or required human review routes to `Review`; an otherwise failure-free review whose required verification cannot run routes to `Blocked`.
- Fall back from `Blocked` to `Review` when the configured Project field does not provide the Blocked option, and explain that fallback in terminal output and the run record.
- Keep `Review` and review-produced `Blocked` recoverable so a later invocation can review new commits or working-tree corrections and move the same item to `Done`.
- Print the review report in the terminal and persist it in sanitized local run metadata only; do not comment on, edit, label, assign, or close the GitHub issue.
- Preserve exact pending-transition retries without rerunning Codex or checks, and revalidate the complete review snapshot before persisting a new status intent.
- Run Codex with repository-controlled instructions and schema, a read-only sandbox, a sanitized environment, and no GitHub credentials; the host runner alone may update the recorded Project status field.
- **BREAKING**: Fresh `--sync-status` runs now invoke Codex, read the linked issue through the host, include committed and uncommitted changes since the recorded base, and can route to `Review` or `Blocked` instead of only establishing `Done`.

## Capabilities

### New Capabilities

- `ai-reviewed-openspec-status-sync`: Defines provenance verification, full base-to-current review, issue and OpenSpec requirement evaluation, PASS/FAIL/BLOCKED reporting, safe Project status routing, local notification, retry, and re-review behavior.

### Modified Capabilities

None.

## Impact

- Affects local runner CLI status configuration, GitHub issue reads, task/source identity, Git diff collection, validation policy, Codex review contracts, status-sync orchestration, run records, Project status allowlisting, output, tests, `AGENTS.md`, and `docs/ai-local-openspec.md`.
- Adds a configurable `Review` status and makes the existing configured `Blocked` status optional at mutation time through a documented Review fallback.
- Reuses the recorded task hash to prove the current linked issue still represents the reviewed request; changed issue content requires a new or updated plan rather than silently changing the review contract.
- Reuses the pinned Codex model and host GitHub authentication while keeping credentials, raw command logs, and raw issue bodies out of Codex output and run records.
- Leaves implementation, index, commits, branches, issues, and publication state unchanged; only ignored local review metadata and the exact recorded Project status field may change.
