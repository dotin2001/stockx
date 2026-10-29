## Context

See `proposal.md` for motivation and `specs/human-approved-local-ai-delivery/spec.md` for required behavior. Today `runLocalWorkflow` performs preflight, planning, implementation, validation, and patch application in one temporary worktree. Planning output reaches the operator checkout only as part of the final combined patch, so any later failure discards it. Preflight also requires a completely clean checkout, run records describe only one invocation, and the GitHub adapter is intentionally read-only.

The existing isolation, trusted prompts, strict OpenSpec validation, changed-area checks, `gpt-5.6-sol` pin, and credential separation remain useful. The redesign must preserve them while allowing a reviewed plan to exist in the checkout between commands and granting the host runner narrowly scoped Project status mutation authority.

## Goals / Non-Goals

**Goals:**

- Make an intake invocation produce, validate, and persist only a reviewable OpenSpec plan.
- Make a second explicit command the approval boundary and implementation entry point.
- Support operator edits to the generated plan before approval without accepting unrelated dirty files.
- Preserve temporary-worktree isolation and apply only a validated implementation delta.
- Update exactly one selected Project item to `Done` or `Blocked` under defined terminal outcomes.
- Make a post-apply status-sync failure safely retryable without rerunning Codex.

**Non-Goals:**

- Committing, staging, pushing, opening pull requests, merging, or publishing implementation changes.
- Passing GitHub credentials or mutation tools into Codex.
- Treating every model, network, verification, or runner failure as a task blocker.
- Polling Projects, processing multiple issues, or moving arbitrary Project items.
- Providing cross-machine apply from planning artifacts alone; the first version relies on ignored local plan records for trusted source linkage.

## Decisions

### Keep intake syntax compatible and add explicit apply and sync modes

Existing `--task` and `--project-owner` intake forms become plan-only without requiring a new `plan` positional command. Add mutually exclusive `--apply <change-name>` and `--sync-status <change-name>` modes. `--apply` is the human approval event; `--sync-status` is a recovery-only operation that never invokes Codex or touches the checkout.

Project intake continues to accept `--status-field` and `--status-value` for the source inbox and adds `--done-status` and `--blocked-status`, defaulting to `Done` and `Blocked`. These names and the selected item identity are frozen into the successful plan record so apply cannot redirect mutation through task or plan text.

Alternative considered: introduce `plan` and `apply` positional subcommands. Rejected because changing normal intake to plan-only already provides an unambiguous compatibility path and Node's current strict option parser can add the two explicit modes with less CLI churn.

### Apply the validated plan patch at the end of stage one

Planning continues in a detached temporary worktree. After plan-only scope and strict OpenSpec validation succeed, apply that binary plan patch to the original clean checkout with the existing unstaged/no-commit guarantees. The successful run record stores the source descriptor, base revision, plan paths, and plan digest, then output prints the exact `--apply` command.

Failures before patch application leave the checkout unchanged. GitHub status remains `Todo` throughout planning, including clarification outcomes.

Alternative considered: keep the temporary worktree alive while awaiting approval. Rejected because approval may happen much later, persistent worktrees are fragile, and a reviewable checkout diff is the desired artifact.

### Treat explicit apply as approval of the current artifacts

Apply locates the latest successful plan record for the exact change and reconstructs the trusted source descriptor from that record. It accepts either:

- a clean checkout where the plan has been committed since generation; or
- a checkout whose unstaged changes are entirely inside the exact selected change directory and whose index has no staged changes.

It rejects other dirty paths, source mismatch, missing records, missing artifacts, and unsafe change names. Apply runs strict OpenSpec validation against the current artifacts and computes a fresh approved-plan digest. This deliberately permits the operator to correct or refine the generated plan before invoking approval.

Alternative considered: require a plan commit as approval. Rejected because the user requested review followed by explicit OpenSpec apply, and the runner can safely bind the current uncommitted plan while retaining a narrow dirty-worktree policy. A commit remains supported but optional.

### Use the isolated index as the implementation baseline

Create the apply worktree from the current `HEAD`. If the approved plan is uncommitted, copy only its directory into the worktree, validate it again, and stage that directory in the temporary worktree index to establish an internal baseline. No commit is created. If the plan is already committed, the existing index is the baseline.

Run the implementation Codex process against that approved state. Capture the implementation delta between the temporary index and working tree rather than between `HEAD` and the working tree. This excludes the already-present plan additions while retaining task-checkbox edits and project implementation files, so the patch applies cleanly to the operator checkout that already contains the plan.

Before applying, compare the original revision, staging state, allowed dirty paths, and approved-plan digest to their apply-start values. Validation requires non-plan implementation changes, every task complete, and all trusted checks.

Alternative considered: create a temporary baseline commit. Rejected because the index provides the needed comparison without creating Git objects presented as commits or weakening the no-commit contract.

### Freeze the approved contract and permit checkbox-only task updates

At apply start, hash `.openspec.yaml`, proposal, design when present, every capability spec, and task content normalized so checkbox states do not affect the digest. After implementation, recompute that digest. The approved contract must match exactly; only task marker state may differ, and every marker must be complete.

This prevents the implementation agent from silently changing requirements to make its work appear complete while still allowing normal OpenSpec task tracking.

Alternative considered: rely only on strict OpenSpec validation. Rejected because a rewritten but syntactically valid spec is not the plan the operator approved.

### Classify `Blocked` as a structured task outcome

Extend the trusted implementation result contract with `blocked`. The implementation prompt may use it only for a missing requirement, unavailable external dependency, or required human decision that prevents safe completion. A blocked result is terminal for the apply attempt, produces no local implementation patch, and is eligible for the Project `Blocked` transition.

All unstructured failures, token/capacity exhaustion, process errors, interruptions, validation failures, verification failures, checkout drift, and GitHub read failures remain technical failures and leave the item `Todo`.

Alternative considered: move every failed apply to `Blocked`. Rejected because it would misrepresent infrastructure failures as product-task blockers and remove retryable work from the inbox.

### Restrict GitHub mutation to resolved status option IDs

Only the host process uses the local `gh` session. At apply start it refreshes the recorded Project and exact item, verifies identity and current source status, and resolves the configured status field plus `Done` and `Blocked` option IDs from Project metadata. It fails closed on missing or ambiguous fields/options.

After local patch application, it updates only the recorded item, Project, field, and allowlisted `Done` option. After a structured blocker, it updates only the same tuple to the allowlisted `Blocked` option. The adapter accepts no status value sourced from issue text, plan text, or model output.

Alternative considered: let Codex call `gh`. Rejected because it would expose credentials and allow task content to influence external mutation.

### Record pending status synchronization after the local terminal action

Local patch application and a remote Project update cannot be atomic. Before attempting mutation, record the exact intended status transition as pending. On success mark it synchronized. On failure retain the local implementation, return a distinct `STATUS_SYNC_FAILED` error, and print `--sync-status <change-name>`.

Sync mode loads only a proven pending transition, refreshes the exact item identity, resolves the frozen field/option, and retries it. It refuses records without a pending transition and never runs planning, implementation, or patch application.

Alternative considered: roll back the local patch when status update fails. Rejected because rollback could destroy operator changes and would discard a fully validated implementation for an unrelated network failure.

### Version run records around plan and apply lifecycles

Advance the run-record schema with a mode (`plan`, `apply`, or `sync-status`), plan identity, source status configuration, parent plan run ID for apply, and status-sync state. Keep issue bodies, titles, prompts, transcripts, raw API responses, environment dumps, and credentials excluded.

The apply lookup considers only complete successful plan records whose exact change name and source identity validate. A later apply record refers back to that plan record rather than copying untrusted plan content.

## Risks / Trade-offs

- [Uncommitted plans relax the global clean-worktree rule] -> Apply accepts only one exact change directory, rejects staged and unrelated paths, hashes the approved artifacts, and rechecks them before patch application.
- [Operator edits could create a plan unrelated to the issue] -> Explicit apply is the approval action, strict OpenSpec validation still applies, and external mutation remains restricted to the originally selected item.
- [A successful local implementation can precede a failed remote update] -> Persist a pending transition and provide a no-model, no-patch retry instead of attempting rollback.
- [The model could overuse the structured blocked outcome] -> Constrain the schema/prompt, require a non-empty blocker summary, discard all partial output, and limit mutation to the selected item; human review of run records remains available.
- [Committed plans may move `HEAD` beyond the original planning base] -> Treat apply as a new transaction at current `HEAD`, revalidate the plan, and bind a new approved-plan digest rather than replaying against the old base.
- [Local records are not portable across machines] -> Document this first-version constraint; do not infer Project mutation authority from editable plan content alone.

## Migration Plan

1. Add CLI parsing and run-record contracts for plan, apply, and status-sync modes while retaining existing intake arguments.
2. Split planning orchestration from apply orchestration, add approved-plan discovery/digest helpers, and implement temporary-index baseline capture.
3. Add structured blocked output and narrow Project status resolution/mutation with fake-adapter tests.
4. Add status-sync recovery, terminal output, and failure-path tests proving technical failures remain `Todo`.
5. Update source-contract tests, operator documentation, and `AGENTS.md` to replace the current one-shot/read-only guarantees.
6. Run syntax checks, the focused local-runner suite, the root test suite, and strict OpenSpec validation.

Rollback restores one-shot orchestration, the read-only GitHub adapter, and the previous docs. Existing ignored run records remain inert; no automatic reverse Project transition is attempted.
