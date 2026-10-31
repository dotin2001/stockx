## Purpose

Defines how the local runner safely synchronizes a completed and independently verified GitHub-backed OpenSpec change to its configured Project `Done` status.

## ADDED Requirements

### Requirement: Status sync preserves recorded retry behavior
The system SHALL prioritize a unique recorded pending terminal transition when `--sync-status <change-name>` is invoked and SHALL retry only that exact allowlisted Project update without invoking Codex, validating a new implementation, or changing the checkout.

#### Scenario: Pending transition exists
- **WHEN** the selected change has exactly one pending `Done` or `Blocked` Project transition
- **THEN** status sync retries that recorded transition using its recorded source identity and target

#### Scenario: Multiple pending transitions exist
- **WHEN** more than one pending transition matches the selected change
- **THEN** status sync refuses the ambiguous update without mutating GitHub

### Requirement: Completed OpenSpec changes can establish a Done transition
When no pending transition exists, the system SHALL allow `--sync-status <change-name>` to establish a `Done` transition only from a unique successful GitHub-backed plan record and a locally completed implementation that passes every trusted completion check. A successful `ai:local --apply <change-name>` record MUST NOT be required when the implementation was completed through `$openspec-apply-change <change-name>`.

#### Scenario: Verified project-local OpenSpec apply is complete
- **WHEN** an operator invokes status sync after the approved GitHub-backed OpenSpec change was implemented with `$openspec-apply-change` and every completion check succeeds
- **THEN** the system records a pending `Done` transition, updates only the selected Project item's configured status field, and records successful synchronization

#### Scenario: Exact three-stage operator flow succeeds
- **WHEN** an operator creates a successful GitHub-backed plan using `--project-owner`, `--project-number`, and `--issue`, implements that change using `$openspec-apply-change <change-name>`, and then invokes `--sync-status <change-name>` without any successful `ai:local --apply` record
- **THEN** status sync verifies the completed implementation and updates the recorded Project item to `Done`

#### Scenario: Plan approval without implementation is insufficient
- **WHEN** a GitHub-backed plan exists but `$openspec-apply-change` has not completed every task and produced a verifiable implementation delta
- **THEN** status sync refuses to set `Done` and leaves the Project status unchanged

#### Scenario: Source is not GitHub-backed
- **WHEN** the selected completed change originated from a local Markdown task
- **THEN** status sync refuses to create a terminal Project transition

#### Scenario: No unique successful plan exists
- **WHEN** no successful plan record exists or multiple successful plan records match the change
- **THEN** status sync refuses without validating or mutating a Project item

### Requirement: Verified completion uses the approved plan and trusted checks
The system MUST prove that the current change has the same approved plan identity apart from task checkbox completion, every OpenSpec task is complete, strict OpenSpec validation succeeds, the checkout has a non-empty unstaged implementation delta including the tasks file, no staged or unsupported changes are present, no protected authority path changed, and all path-selected trusted verification commands pass.

#### Scenario: All completion evidence passes
- **WHEN** the approved plan identity matches and all task, checkout, scope, strict-validation, and trusted-verification checks pass
- **THEN** the system may create a pending `Done` transition for the recorded GitHub Project item

#### Scenario: Task markers are incomplete
- **WHEN** any task marker in the approved change remains incomplete
- **THEN** status sync fails before preparing or mutating the remote Project status

#### Scenario: Approved plan contract changed
- **WHEN** the proposal, design, specification, task text, or other approved artifact changed beyond task checkbox markers
- **THEN** status sync reports plan drift and does not mutate GitHub

#### Scenario: Checkout evidence is unsafe
- **WHEN** changes are staged, the implementation delta is empty, only planning artifacts changed, an unsupported path changed, or a protected authority path changed
- **THEN** status sync refuses the transition without altering the checkout or GitHub

#### Scenario: Trusted verification fails
- **WHEN** strict OpenSpec validation or any verification command selected by the trusted path policy fails
- **THEN** status sync leaves the Project item in its existing status and records a technical failure without a pending `Done` transition

### Requirement: Verified status synchronization is auditable and recoverable
The system SHALL write a sanitized linked run record containing the plan identity, changed paths, verification names, completion basis, and status-sync state, and SHALL persist the pending `Done` intent before attempting GitHub mutation.

#### Scenario: GitHub update fails after local verification
- **WHEN** completion verification succeeds and the subsequent Project update fails
- **THEN** the run record retains one pending `Done` transition and the command instructs the operator to retry the same `--sync-status` invocation

#### Scenario: Retrying after remote uncertainty
- **WHEN** the remote update may have succeeded but the local process did not record completion
- **THEN** retry remains idempotent and cannot mutate another Project item, field, or terminal value

#### Scenario: Verification record is inspected
- **WHEN** an operator reads the status-sync run record
- **THEN** it identifies verified completion separately from a pending-transition retry without storing issue bodies, prompts, raw command output, environment dumps, or credentials

### Requirement: Status synchronization remains a no-model no-publication operation
The system MUST NOT invoke Codex, edit issues, create commits, stage files, push, open or merge pull requests, or publish artifacts during either retry or verified-completion status synchronization.

#### Scenario: Verified completion synchronizes successfully
- **WHEN** status sync verifies and updates a completed change
- **THEN** only local run metadata and the selected GitHub Project status field may change
