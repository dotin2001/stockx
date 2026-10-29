## Purpose

Provide a durable two-stage local delivery workflow in which a validated OpenSpec plan is reviewed by a human before implementation and selected GitHub Project issues receive narrowly controlled terminal status updates.

## ADDED Requirements

### Requirement: Intake runs stop after producing a reviewable plan
The system SHALL treat normal Markdown and GitHub Project intake invocations as plan-only runs. It SHALL create the complete OpenSpec proposal, design, specification, and task artifacts in an isolated worktree, validate them strictly, apply only the validated planning artifacts to the operator checkout as unstaged changes, and stop without starting implementation.

#### Scenario: GitHub issue planning succeeds
- **WHEN** an operator selects one eligible `Todo` issue and planning passes all scope and strict OpenSpec checks
- **THEN** the selected change's planning artifacts are left unstaged in the operator checkout and no implementation process or GitHub mutation occurs

#### Scenario: Markdown task planning succeeds
- **WHEN** an operator supplies one valid committed Markdown task and planning passes all checks
- **THEN** the planning artifacts are left unstaged for review and no implementation process starts

#### Scenario: Planning fails or requires clarification
- **WHEN** the planning process fails, requires a material decision, produces invalid artifacts, or changes a path outside the selected change directory
- **THEN** the operator checkout remains unchanged, implementation does not start, and a GitHub-backed issue remains `Todo`

### Requirement: Apply is an explicit human approval action
The system SHALL provide an apply invocation that accepts exactly one previously planned change name. Invoking apply SHALL constitute approval of the current planning artifacts, SHALL revalidate the complete plan before model execution, and SHALL run implementation without rerunning proposal generation.

#### Scenario: Operator approves an unstaged plan
- **WHEN** the checkout changes are limited to one planned OpenSpec change associated with a successful plan record and the operator invokes apply for that change
- **THEN** the system snapshots and validates the current artifacts as the approved plan and starts implementation in an isolated worktree

#### Scenario: Operator approves a committed plan
- **WHEN** the selected plan exists in the current clean revision, remains associated with a successful local plan record, and the operator invokes apply
- **THEN** the system uses the current validated artifacts as the approved plan and starts implementation from the current revision

#### Scenario: Operator edited the generated plan before approval
- **WHEN** the operator changes only files inside the selected OpenSpec change directory and the edited plan passes strict validation
- **THEN** apply treats the current validated artifact contents as the approved plan

#### Scenario: Apply input is stale, ambiguous, or dirty outside the plan
- **WHEN** the plan has no matching successful plan record, its source identity is inconsistent, required artifacts are absent, or the checkout contains unrelated staged or unstaged changes
- **THEN** apply fails before Codex starts and does not mutate GitHub

### Requirement: Implementation cannot rewrite the approved contract
The system SHALL bind implementation to a digest of the approved plan. The implementation process MAY mark task checkboxes complete but SHALL NOT alter the approved proposal, design, specifications, schema metadata, or task text, and SHALL produce at least one non-planning implementation change.

#### Scenario: Implementation follows the approved plan
- **WHEN** implementation changes project files, changes only task checkbox states within the plan, completes every task, and passes all trusted verification
- **THEN** the system applies only the validated implementation delta to the operator checkout as unstaged and uncommitted changes

#### Scenario: Implementation changes approved planning content
- **WHEN** implementation modifies approved requirements, design decisions, task wording, or other plan content beyond task checkbox states
- **THEN** validation fails, the operator checkout remains at its approved-plan state, and the GitHub issue remains `Todo`

#### Scenario: Operator checkout changes during apply
- **WHEN** the checkout revision, approved plan, staging state, or allowed dirty-path set changes after apply begins
- **THEN** the system refuses to apply the implementation delta and leaves GitHub state unchanged

### Requirement: GitHub terminal status mutation is narrow and outcome-based
For a GitHub-backed change, the host runner SHALL update only the original selected Project item and only its configured status field. It SHALL set the configured done value after the validated implementation delta reaches the operator checkout, set the configured blocked value only after a structured task-blocked outcome, and leave the item in `Todo` for all other failures. GitHub credentials SHALL remain unavailable to Codex processes.

#### Scenario: GitHub-backed apply succeeds
- **WHEN** implementation and verification succeed and the validated delta is applied locally
- **THEN** the host runner updates the original Project item from `Todo` to `Done` and records the status synchronization result

#### Scenario: Implementation reports a task blocker
- **WHEN** the implementation result explicitly reports that a missing requirement, unavailable external dependency, or required human decision prevents safe completion
- **THEN** no implementation delta reaches the checkout and the host runner updates the original Project item from `Todo` to `Blocked`

#### Scenario: Apply fails for a transient or technical reason
- **WHEN** Codex exhausts capacity, a command or network operation fails, verification fails, the process is interrupted, or runner validation rejects output without a structured task blocker
- **THEN** the Project item remains `Todo`

#### Scenario: Selected Project item is no longer eligible
- **WHEN** apply refreshes the original item and its identity or configured source status no longer matches the plan record
- **THEN** apply stops before Codex or mutation and asks the operator to reconcile the item

### Requirement: Status synchronization failure is recoverable
The system SHALL keep a successfully applied local implementation when the subsequent Project status update fails, SHALL report a distinct non-success status-sync outcome, and SHALL provide a no-model retry that can perform only the previously intended allowlisted status update.

#### Scenario: Done update fails after local apply
- **WHEN** the validated implementation delta has reached the checkout but GitHub rejects or cannot complete the `Done` update
- **THEN** the local changes remain present, the run record identifies the pending `Done` synchronization, and the command reports how to retry without rerunning implementation

#### Scenario: Operator retries pending synchronization
- **WHEN** the operator invokes status synchronization for a change whose run record proves a pending terminal update and the Project item still has the expected identity
- **THEN** the runner performs no Codex or patch operation and attempts only that recorded status update

#### Scenario: Retry has no proven pending update
- **WHEN** no matching run record proves a pending terminal update for the selected change
- **THEN** the runner rejects the retry without changing Project or issue state

### Requirement: Two-stage runs remain reviewable and secret-safe
The system SHALL record source identity, mode, approved-plan identity, phase, outcomes, changed paths, verification, and pending or completed status synchronization in ignored local metadata without storing issue bodies, prompts, raw transcripts, or credentials.

#### Scenario: Plan completes
- **WHEN** a plan-only run succeeds
- **THEN** output identifies the change, source, review paths, exact apply command, and confirms that implementation and Project mutation did not run

#### Scenario: Apply completes
- **WHEN** apply reaches a terminal success or blocked outcome
- **THEN** output identifies the implementation result, local changed paths when present, verification, Project status result when applicable, and the run record

#### Scenario: Codex process starts in either stage
- **WHEN** planning or implementation invokes Codex
- **THEN** its environment contains no GitHub authentication credential or Project mutation authority
