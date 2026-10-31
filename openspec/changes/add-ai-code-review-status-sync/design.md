## Context

See `proposal.md` for motivation and `specs/ai-reviewed-openspec-status-sync/spec.md` for required behavior. Fresh `--sync-status` currently trusts a unique successful GitHub-backed plan record, inspects only modified/deleted/untracked working-tree paths, rejects staged changes, validates the approved OpenSpec digest and completed task markers, runs path-selected checks, and prepares `Done`. It neither re-reads the linked issue nor reviews commits between the plan's base and the current `HEAD`.

Version-3 run records already contain the canonical Project/issue identity, task hash, recorded branch, base commit, approved-plan hash, and status-sync evidence. The raw issue body is deliberately excluded. The GitHub adapter can re-read the exact recorded Project item and issue through the host's authenticated `gh` process, while Codex runs with a sanitized environment and empty GitHub configuration.

## Goals / Non-Goals

**Goals:**

- Prove that the current review still belongs to the recorded issue, request snapshot, branch, and base history.
- Review one stable base-to-current snapshot containing committed and uncommitted changes.
- Produce auditable PASS/FAIL/BLOCKED evidence for issue criteria, OpenSpec requirements/tasks, and required checks.
- Derive `Done`, `Review`, or `Blocked` deterministically and support correction or unblocking through re-review.
- Keep the review unable to modify Git-visible implementation state or use GitHub credentials.

**Non-Goals:**

- Review another branch, a rebased history that no longer contains the recorded base, or issue content changed after planning.
- Update the approved OpenSpec contract automatically when an issue changes.
- Let Codex choose a Project target or call GitHub.
- Post the report to the issue, create a formal GitHub review, commit, push, merge, or publish.
- Guarantee semantic correctness beyond the available code, checks, and one bounded Codex review.

## Decisions

### Reconstruct and verify the recorded issue snapshot on the host

Status-sync preflight will resolve one unique successful plan record, require a GitHub issue source, and query the exact recorded Project item. The query must return the same Project item id, repository, issue number, URL identity, and configured status field. The host then rebuilds the same canonical GitHub task representation used during intake from the current title/body metadata and compares its SHA-256 task hash with the record.

A hash mismatch means the request changed after planning, so the command stops without a status transition. This is safer than silently reviewing new acceptance criteria against an older approved plan. The operator must update or create a plan for the changed request. Raw issue content is written only to a private ignored review-context file for the current invocation, is treated as untrusted data, and is removed after review; it is never stored in the run record or model result.

The host also requires the current symbolic branch name to equal the recorded branch, verifies that `baseSha` resolves to a commit, and uses an ancestor check to prove that base is in the current `HEAD` history. Exact `HEAD === baseSha` is intentionally not required because committed implementation work must be reviewable. A detached checkout, branch mismatch, missing base, or non-ancestor base is a provenance error, not a review finding, and cannot mutate Project status.

### Collect one read-only base-to-current snapshot

For tracked content, compare the recorded base tree directly with the working tree. A base-to-working-tree binary diff and name-only query include changes committed after base, staged changes, unstaged changes, and deletions. Collect untracked paths separately with Git's read-only untracked-file query and include safe regular files in the review inventory. Do not reuse the current intent-to-add diff capture because `git add -N` changes the index.

The snapshot contains:

- recorded branch and base;
- current `HEAD`;
- exact porcelain-v1 status including untracked files;
- staged-name output and untracked path inventory;
- union of safe changed paths;
- digest of the tracked binary diff plus bounded untracked file identities/content digests;
- approved-plan digest; and
- verified issue task hash.

Symlinks, unsafe paths, unreadable files, or unsupported status records fail closed. Binary and oversized untracked files remain identifiable as changed evidence without copying their raw contents into the report. The Codex reviewer reads the actual checkout under a read-only sandbox and can use the recorded base for its own read-only inspection.

After checks and Codex complete, the host recomputes every snapshot identity before Project preparation. Any concurrent commit, checkout, stage, edit, untracked-file change, plan edit, or issue drift invalidates the report. This also detects unexpected Git-visible output from tests.

### Build a normalized requirement and verification inventory

The reviewer receives four bounded input groups:

1. The verified issue snapshot, from which it enumerates explicit acceptance criteria and material request requirements.
2. The approved OpenSpec proposal, specification requirements/scenarios, and applicable design constraints.
3. Every required task marker with its current completion state.
4. Host-produced results for strict OpenSpec validation and each trusted path-selected check.

The report schema contains an array of entries with a stable source (`issue`, `openspec`, `task`, or `check`), bounded identifier/label, result (`PASS`, `FAIL`, or `BLOCKED`), bounded evidence items, and bounded remaining-work items. It also contains a bounded summary plus `humanReviewRequired` and reasons.

The host can deterministically validate coverage for OpenSpec requirement headings, task markers, and selected checks. Issue-criteria discovery remains semantic, so the trusted prompt requires enumeration before evaluation; an absent or ambiguous acceptance contract must set human review and explain why rather than silently pass. `PASS` requires evidence and no remaining work, while `FAIL` and `BLOCKED` require remaining work or an unblocking action.

This per-entry model replaces the earlier single `match`/`mismatch` verdict. A free-form report was rejected because it cannot prove coverage or support deterministic status routing.

### Capture check outcomes instead of aborting on ordinary failures

Provenance and snapshot-safety checks remain hard preconditions. Once they pass, review-oriented validation collects results instead of throwing for expected implementation outcomes:

- incomplete task markers, OpenSpec misalignment, or a command that executes and fails become `FAIL` entries;
- a command that cannot start or lacks an external prerequisite becomes `BLOCKED` with a sanitized reason;
- a passing command becomes `PASS`;
- unsafe paths, malformed Git evidence, or mutation during review remain hard errors because the reviewed object cannot be trusted.

Verification command selection uses the complete base-to-current path union. `git diff --check` is scoped from the recorded base so committed whitespace errors are included. Frontend, backend/PostgreSQL, and runner checks retain the existing allowlist and sanitized test environment. Raw stdout/stderr is not persisted; only check name, result, concise sanitized evidence, and remaining work reach the report.

If Codex itself is unavailable, times out, or returns invalid/incomplete structured output after provenance is proven, the host synthesizes a bounded `BLOCKED` semantic-review entry. That satisfies the user's rule that unavailable required verification becomes Blocked rather than pretending the implementation failed or passed.

### Run Codex as a read-only report generator

Add a dedicated `review` prompt and JSON schema. The prompt identifies the verified base, change name, private issue-context path, approved OpenSpec directory, and sanitized check-result path. It directs Codex to inspect the base-to-current code, enumerate and classify all requirements, cite evidence, identify remaining work, and request human review when evidence is ambiguous. All repository and issue content is data and cannot override the trusted prompt.

Review arguments reuse the pinned repository model, ephemeral execution, ignored user configuration, and structured final-message capture, but select a read-only sandbox. The child receives a sanitized environment, an empty private `GH_CONFIG_DIR`, no apply-only database value, and no GitHub credentials. The host creates private ignored input/result directories with restrictive permissions; Codex has no authority to write source or status data.

### Derive status on the host with explicit precedence

Codex returns classifications and human-review signals, never a Project target. After schema, coverage, consistency, and snapshot validation, the host derives:

1. `Done` only if every inventory entry is `PASS`, all required checks passed, and no human review is required.
2. `Review` if any entry is `FAIL`, any executed check failed, human review is required, or the report contains both failed and blocked entries.
3. `Blocked` if there is no failure or independent human-review reason and at least one required verification is `BLOCKED`.

GitHub-backed intake continues to record distinct source, Done, Review, and Blocked names, adding `--review-status` with default `Review`. During preparation the adapter must resolve Done and Review exactly. It resolves Blocked only when Blocked is the derived target. If that option is absent or ambiguous, the host selects Review instead and records `derivedTarget: blocked`, `effectiveTarget: review`, and a sanitized fallback reason.

For a fresh review, the recorded item's current status may be the original source value, Review, a review-produced Blocked value, or the desired value. Unrelated manual movement fails closed. Synchronized Done is terminal. Synchronized Review and review-produced Blocked are nonterminal and enter fresh provenance verification and review so fixes or restored prerequisites can advance the task.

### Persist report and intent before the one allowed mutation

The linked sync record stores changed paths, check names/results, bounded report entries, human-review reasons, derived/effective target, fallback reason, and review basis. It excludes raw issue text, prompts, source excerpts, model output, command logs, environment dumps, and secrets.

After the report is valid and the snapshot is stable, prepare the exact recorded Project item and effective option. Persist `statusSync.state = pending` before calling the mutation adapter. If the remote update fails, the pending record is the sole retry authority. The next invocation retries exactly the recorded item, field, option, and fallback provenance without re-reading the issue, running checks, or invoking Codex.

Pending `done`, `review`, and `blocked` transitions take priority over fresh review. Multiple pending records remain an ambiguity error. A successful retry marks both the parent pending evidence and the linked retry record synchronized.

### Enforce no implementation modification

Neither the host review path nor Codex stages, applies, resets, commits, checks out, or edits implementation files. The host uses read-only Git queries and writes only ignored private review/run metadata. Trusted verification commands are expected not to modify Git-visible inputs; exact post-review snapshot comparison detects violations and stops without Project mutation. Ignored build/test caches may be created by existing commands, but they are not treated as implementation and are never committed or published by the runner.

The only permitted external write is the selected Project item's recorded status field after all review rules pass. Issue comments, labels, assignments, closure, pull requests, pushes, and publication remain forbidden.

## Risks / Trade-offs

- [Issue content changes after planning] -> Compare the reconstructed canonical task hash and require a new or updated plan instead of mixing contracts.
- [A long-lived branch contains unrelated commits] -> Review the entire recorded-base delta and expose every path in the report; operators must keep the delivery branch scoped or accept Review findings.
- [The model misses an implicit issue requirement] -> Require explicit inventory construction, deterministic coverage for OpenSpec/check items, human-review signaling for ambiguity, and local auditability.
- [The model returns a false PASS or FAIL] -> Combine semantic review with trusted checks and route uncertainty to human Review; never let the model choose the Project status directly.
- [Tests or another process mutate the checkout] -> Recompute the full snapshot after review and stop without status mutation on any Git-visible difference.
- [A required test environment is unavailable] -> Report BLOCKED and use the configured Blocked option or the documented Review fallback.
- [The Project lacks both Blocked and Review options] -> Print and record the configuration failure and leave Project status unchanged.
- [Raw issue or test data leaks into metadata] -> Keep raw inputs in private ephemeral context, sanitize bounded report fields, and prohibit raw logs/bodies/output in records.
- [Committed binary or large untracked files are expensive to inspect] -> Keep bounded path/digest evidence and allow the reviewer to request human review when semantic inspection is insufficient.

## Migration Plan

1. Extend source/status configuration and compatible run-record parsing for Review, Blocked fallback provenance, and structured report metadata.
2. Add host-side exact issue refresh and canonical task-hash verification plus branch/base/ancestor preflight.
3. Replace working-tree-only completion inspection with read-only base-to-current tracked/untracked collection and stable snapshot revalidation.
4. Refactor trusted verification to return PASS/FAIL/BLOCKED results for review while retaining hard errors for unsafe provenance or mutable evidence.
5. Add the review inventory/result schema, contract validation, trusted prompt, private contexts, and read-only Codex invocation.
6. Add host status aggregation, conditional Blocked-option fallback, recoverable Review/Blocked evidence, and exact pending retries.
7. Add terminal/run-record reporting and offline tests for committed/uncommitted scope, provenance failures, classifications, fallback, re-review, mutation detection, redaction, and prohibited GitHub/code actions.
8. Update `AGENTS.md`, CLI help, and operator documentation, then run the full runner tests and strict OpenSpec validation.
9. Roll back by removing fresh review/report routing while retaining backward-compatible reads of additive report and Review metadata; manually handle any item already left in Review or Blocked.
