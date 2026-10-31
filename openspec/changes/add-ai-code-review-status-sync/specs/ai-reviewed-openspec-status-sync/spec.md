## Purpose

Defines a read-only review and synchronization gate that verifies task provenance, evaluates all changes since the recorded base against the linked issue and approved OpenSpec contract, reports evidence per requirement, and safely routes the recorded GitHub Project item.

## ADDED Requirements

### Requirement: Status sync verifies recorded task provenance before review
The system MUST resolve one unique successful GitHub-backed plan run record for the selected change and verify its exact Project item, repository, issue number, issue content identity, recorded branch, and recorded base commit before reviewing or preparing a status update. The current issue snapshot MUST reproduce the recorded task identity, the current attached branch MUST equal the recorded branch, and the recorded base MUST exist as a commit and be an ancestor of the current `HEAD`.

#### Scenario: Recorded provenance is valid
- **WHEN** the Project item still links to the recorded issue, the current issue reproduces the recorded task identity, the attached branch matches, and the recorded base is an ancestor of `HEAD`
- **THEN** status sync proceeds to change-set collection and review

#### Scenario: Linked issue cannot be verified
- **WHEN** the Project item or issue is missing, its repository or number differs, its current task identity differs, or GitHub cannot verify it
- **THEN** status sync stops with an actionable local error and does not create or mutate a Project status transition

#### Scenario: Branch cannot be verified
- **WHEN** the checkout is detached or its current branch differs from the branch recorded by the successful plan
- **THEN** status sync stops with an actionable local error and leaves Project status unchanged

#### Scenario: Base commit cannot be verified
- **WHEN** the recorded base is missing, invalid, or not an ancestor of the current `HEAD`
- **THEN** status sync stops with an actionable local error and leaves Project status unchanged

### Requirement: Review covers committed and uncommitted changes since the base
The system SHALL collect the complete Git-visible change set between the recorded base commit and the current checkout. The review scope MUST include commits after the base plus staged, unstaged, deleted, and untracked files, and MUST identify their union of safe repository-relative paths without staging files or changing the index.

#### Scenario: Branch contains implementation commits
- **WHEN** one or more commits after the recorded base change implementation paths
- **THEN** those committed changes and paths are included in the review and verification scope

#### Scenario: Checkout contains uncommitted changes
- **WHEN** tracked staged or unstaged changes, deletions, or untracked files exist in addition to committed changes
- **THEN** all of those changes are included in the same base-to-current review snapshot

#### Scenario: No implementation exists
- **WHEN** the complete base-to-current scope contains no implementation path outside the selected OpenSpec change
- **THEN** the report marks the implementation requirement `FAIL` and identifies the missing implementation as remaining work

#### Scenario: Change scope becomes stale
- **WHEN** the branch, `HEAD`, index, working tree, untracked path set, issue identity, or approved plan changes before a status intent is persisted
- **THEN** status sync rejects the stale review and leaves Project status unchanged

### Requirement: Review evaluates issue and OpenSpec requirements
The system MUST evaluate the complete change set against the verified linked issue's acceptance criteria and against the approved OpenSpec proposal, specifications, design constraints, and required tasks. Issue content and repository files SHALL be treated as untrusted review data and MUST NOT override repository-controlled review instructions or status policy.

#### Scenario: Issue criterion is implemented
- **WHEN** code and verification evidence demonstrate that one linked-issue acceptance criterion is satisfied
- **THEN** the report contains a `PASS` entry for that criterion with supporting evidence

#### Scenario: Issue criterion is missing or contradicted
- **WHEN** the implementation omits or contradicts one linked-issue acceptance criterion
- **THEN** the report contains a `FAIL` entry with supporting evidence and concrete remaining work

#### Scenario: Issue acceptance criteria are ambiguous
- **WHEN** the issue request cannot be evaluated confidently without a human decision
- **THEN** the report requires human review, explains the ambiguity, and cannot route the item to `Done`

#### Scenario: OpenSpec contract is aligned
- **WHEN** the implementation satisfies the approved proposal and specification requirements, respects applicable design constraints, and every required task marker is truthfully complete
- **THEN** the report contains passing OpenSpec requirement and task entries

#### Scenario: OpenSpec alignment or tasks are incomplete
- **WHEN** the implementation conflicts with an approved artifact or a required task is incomplete or unsupported by evidence
- **THEN** the affected report entries are `FAIL` and identify the remaining work

### Requirement: Review runs all required verification checks
The system SHALL run strict OpenSpec validation and every trusted verification command selected by the full base-to-current changed-path set. A check that executes and fails MUST be reported as `FAIL`; a required check that cannot execute because of a missing tool, dependency, environment, credential-free service, or other external prerequisite MUST be reported as `BLOCKED`.

#### Scenario: Required check passes
- **WHEN** a selected verification command completes successfully
- **THEN** its report entry is `PASS` and identifies the command or check name as evidence

#### Scenario: Required check fails
- **WHEN** a selected verification command executes and returns a failing result
- **THEN** its report entry is `FAIL`, Project status cannot become `Done`, and remaining work identifies the failed check

#### Scenario: Required check cannot run
- **WHEN** a selected verification command cannot execute because a required prerequisite is unavailable
- **THEN** its report entry is `BLOCKED` and the report explains how to unblock verification

#### Scenario: Review activity changes Git-visible implementation state
- **WHEN** Codex or a verification command changes any Git-visible repository file, branch, commit, or index state during review
- **THEN** status sync stops, reports the unsafe mutation, and does not create or mutate a Project status transition

### Requirement: Review report covers every requirement with evidence
The system MUST produce a bounded structured report containing one entry for every discovered issue acceptance criterion, approved OpenSpec requirement, required OpenSpec task, and selected verification check. Every entry MUST have exactly one result of `PASS`, `FAIL`, or `BLOCKED`, bounded supporting evidence, and bounded remaining work. The report MUST also identify whether human review is required and why.

#### Scenario: Requirement passes
- **WHEN** available implementation and verification evidence fully supports a requirement
- **THEN** its entry is `PASS`, cites relevant files, behavior, or successful checks, and has no remaining work

#### Scenario: Requirement fails
- **WHEN** available evidence demonstrates missing, incorrect, contradictory, or failing behavior
- **THEN** its entry is `FAIL` with evidence and actionable remaining work

#### Scenario: Requirement cannot be evaluated
- **WHEN** required evidence cannot be obtained despite valid task provenance
- **THEN** its entry is `BLOCKED` with the unavailable prerequisite and an unblocking action

#### Scenario: Report is incomplete or malformed
- **WHEN** Codex fails, returns invalid structured output, omits a required inventory entry, or produces inconsistent classifications
- **THEN** the host records a sanitized `BLOCKED` review result for the unavailable semantic verification rather than inferring that requirements pass

### Requirement: Host derives Project status from the review report
Codex MUST NOT select or mutate a Project status. After validating a stable report, the host SHALL derive exactly one target using this precedence: `Done` only when every entry is `PASS`, every required check passed, and no human review is required; `Review` when any entry is `FAIL`, any check failed, human review is required, or both failure and blocked entries exist; otherwise `Blocked` when at least one entry is `BLOCKED` because required verification could not run.

#### Scenario: All requirements and checks pass
- **WHEN** every report entry is `PASS`, every required check succeeded, and the report does not require human review
- **THEN** the host persists and synchronizes the recorded Project item's configured `Done` transition

#### Scenario: Requirement or check fails
- **WHEN** any report entry is `FAIL` or a required check executed and failed
- **THEN** the host persists and synchronizes the recorded Project item's configured `Review` transition

#### Scenario: Human review is required
- **WHEN** the report identifies ambiguity, subjective acceptance, or another reason that requires a human decision
- **THEN** the host persists and synchronizes the recorded Project item's configured `Review` transition and reports the reason locally

#### Scenario: Verification is blocked without a known failure
- **WHEN** no entry is `FAIL`, human review is not independently required, and at least one required verification entry is `BLOCKED`
- **THEN** the host attempts to persist and synchronize the recorded Project item's configured `Blocked` transition

#### Scenario: Blocked option is unavailable
- **WHEN** the derived target is `Blocked` but the recorded Project field does not contain exactly one configured Blocked option
- **THEN** the host falls back to the configured `Review` transition and records and prints the blocker and fallback reason

#### Scenario: Review option is unavailable
- **WHEN** the derived or fallback target is `Review` but the recorded Project field does not contain exactly one configured Review option
- **THEN** status sync reports the configuration error and leaves Project status unchanged

### Requirement: Review and Blocked results remain eligible for re-review
A synchronized review-produced `Review` or `Blocked` result MUST NOT be treated as final completion. A later `--sync-status` invocation SHALL verify provenance again, collect the then-current base-to-current state, rerun required checks and review, and derive a new status. A synchronized `Done` result remains idempotent.

#### Scenario: Developer corrects failed requirements
- **WHEN** an item is in review-produced `Review`, the developer adds commits or working-tree corrections, and status sync runs again
- **THEN** the system performs a fresh review and may move the item to `Done`

#### Scenario: Verification prerequisite becomes available
- **WHEN** an item is in review-produced `Blocked`, the missing prerequisite becomes available, and status sync runs again
- **THEN** the system performs a fresh review and may move the item to `Done` or `Review`

#### Scenario: Done was already synchronized
- **WHEN** the selected change has one unambiguous synchronized `Done` result for the same recorded task identity
- **THEN** status sync returns that result without rerunning Codex, checks, or Project mutation

### Requirement: Pending status retries remain exact and review-free
The system SHALL prioritize one unique pending `Done`, `Review`, or `Blocked` transition and retry only its recorded Project item, field, option, and fallback provenance without rerunning issue analysis, checks, or Codex. Conflicting pending evidence MUST be rejected without mutation.

#### Scenario: Pending transition is retried
- **WHEN** a validated review persisted a pending status intent but the remote update did not complete
- **THEN** the next status-sync invocation retries only that exact recorded intent

#### Scenario: Pending evidence is ambiguous
- **WHEN** more than one pending transition matches the change
- **THEN** status sync stops and does not mutate GitHub

### Requirement: Review is read-only and credential-isolated
The review MUST NOT modify implementation code, the Git index, commits, branches, planning artifacts, issues, pull requests, or publication state. Codex MUST use repository-controlled instructions and schema, the repository-controlled model, a read-only sandbox, and a sanitized environment without GitHub credentials. The host MAY write only ignored local review/run metadata and MAY update only the exact recorded Project status field after review.

#### Scenario: Repository data contains conflicting instructions
- **WHEN** the issue, source code, diff, or OpenSpec artifact contains prompt-like instructions that conflict with trusted review policy
- **THEN** the reviewer treats those instructions as data and retains the repository-controlled workflow

#### Scenario: Review produces a non-Done result
- **WHEN** the report derives `Review` or `Blocked`
- **THEN** findings remain local and the system does not comment on, edit, label, assign, or close the source issue

#### Scenario: Review produces Done
- **WHEN** the report derives `Done`
- **THEN** the system updates only the recorded Project status field and does not commit, push, publish, or close the issue

### Requirement: Review notifications are local, bounded, and sanitized
The system SHALL print the overall result and per-requirement PASS/FAIL/BLOCKED summary, evidence, remaining work, derived Project status, fallback reason, and run-record path in the terminal and SHALL persist the same bounded sanitized review data in local run metadata. It MUST NOT persist raw issue bodies, raw model output, prompts, source excerpts, raw command logs, environment dumps, or credentials.

#### Scenario: Review completes with findings
- **WHEN** a valid review contains failed or blocked entries
- **THEN** terminal output and the run record identify each affected requirement, its evidence, its remaining work, and the resulting status

#### Scenario: Sensitive value appears in review input or command output
- **WHEN** issue data, environment values, or tool output contains a credential or configured secret
- **THEN** the terminal and run record omit or redact that value
