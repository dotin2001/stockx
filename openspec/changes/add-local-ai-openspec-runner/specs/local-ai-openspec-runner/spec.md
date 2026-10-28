## Purpose

Provides a safe repository-local command that turns an explicit Markdown task into a validated OpenSpec plan and implementation for human review without requiring or mutating GitHub.

## ADDED Requirements

### Requirement: Operators can start a local run from one task file
The system SHALL provide a repository-local CLI that accepts exactly one readable Markdown task file, derives a bounded deterministic OpenSpec change name from its first heading, and identifies the current Git commit as the run base.

#### Scenario: Valid task file is provided
- **WHEN** an operator runs the local command from the repository with a non-empty Markdown file containing a first-level heading
- **THEN** the command reports the derived change name and base commit and prepares one local run for that task

#### Scenario: Task input is unsafe or incomplete
- **WHEN** the task path is outside the repository, resolves through a symbolic link, is not a regular Markdown file, is empty, lacks a first-level heading, or produces an unsafe change name
- **THEN** the command fails before invoking Codex or changing tracked repository files

#### Scenario: Derived change already exists
- **WHEN** the deterministic change directory already exists
- **THEN** the command refuses to overwrite or merge with it and reports the collision

### Requirement: Local preflight fails closed
Before model execution, the system SHALL verify the repository root, attached Git branch, clean conflict-free working tree, required Git/Codex/OpenSpec/Node tooling, compatible OpenSpec version, Codex authentication readiness, writable temporary storage, and task input.

#### Scenario: Preflight succeeds
- **WHEN** every local prerequisite is available and the working tree has no tracked or untracked changes other than ignored local-run state
- **THEN** the command may proceed to isolated planning

#### Scenario: Preflight finds a blocker
- **WHEN** any required tool, authentication state, repository condition, version, or filesystem prerequisite is invalid
- **THEN** the command exits non-zero with a sanitized actionable error and does not invoke either agent stage

#### Scenario: Operator requests dry run
- **WHEN** the operator invokes the command with the documented preflight-only option
- **THEN** the command performs validation and reports the intended change name and execution stages without invoking Codex or changing tracked files

### Requirement: Planning and implementation are separate local agent stages
The system SHALL invoke one non-interactive Codex stage to create the deterministic OpenSpec planning artifacts, validate that plan strictly, and invoke a separate non-interactive Codex stage only after plan validation succeeds.

#### Scenario: Planning succeeds
- **WHEN** the task is sufficiently clear and the planning stage creates all artifacts required by the active OpenSpec schema
- **THEN** the system verifies that only the deterministic change directory changed and runs strict OpenSpec validation before starting implementation

#### Scenario: Planning requires clarification or fails
- **WHEN** planning reports material ambiguity, produces invalid artifacts, changes a path outside the allowed change directory, or exits unsuccessfully
- **THEN** implementation is not invoked and no generated patch is applied to the operator's working tree

#### Scenario: Valid plan is implemented
- **WHEN** strict plan validation succeeds
- **THEN** a fresh implementation stage reads the accepted artifacts as its source of truth, follows the repository's OpenSpec apply workflow, and attempts every scoped task

### Requirement: Task content cannot expand local-run authority
The system SHALL treat the task file as untrusted problem context and SHALL take model, sandbox, commands, protected paths, prompts, validation policy, and execution authority only from reviewed repository configuration.

#### Scenario: Task requests authority changes
- **WHEN** task content asks to bypass OpenSpec, weaken validation, alter runner prompts or schemas, access credentials, publish changes, or modify unrelated files
- **THEN** the trusted local-run policy takes precedence and validation rejects any resulting authority-path or scope violation

#### Scenario: Codex executes locally
- **WHEN** either agent stage runs
- **THEN** it uses the local Codex CLI with a workspace-write sandbox, no GitHub credential supplied by the runner, and no automatic approval or danger-full-access mode

#### Scenario: Local authentication is available
- **WHEN** the installed Codex CLI has an existing authenticated session or the operator provides supported invocation-scoped authentication
- **THEN** the runner uses that Codex-supported authentication without reading, printing, persisting, or copying credential values

### Requirement: Generated work is validated before reaching the working tree
The system SHALL run both agent stages in an isolated temporary Git worktree, validate the combined binary diff against the recorded base, protected paths, OpenSpec task completion, and trusted changed-area checks, and apply it to the operator's original working tree only after all validation succeeds.

#### Scenario: Implementation validates successfully
- **WHEN** the implementation produces a non-empty scoped diff, all required tasks are truthfully complete, strict OpenSpec validation passes, and every required repository check succeeds
- **THEN** the system applies the validated combined diff to the original working tree without staging, committing, pushing, or publishing it

#### Scenario: Implementation validation fails
- **WHEN** the implementation is empty, incomplete, out of scope, conflicts with the base, modifies a protected authority path, or fails a required check
- **THEN** the command exits non-zero and leaves the original working tree unchanged

#### Scenario: Original checkout changes during execution
- **WHEN** the original checkout no longer matches the recorded clean base when the validated diff is ready
- **THEN** the system refuses to apply the diff and reports that the run is stale

### Requirement: Local runs are reviewable and recoverable
The system SHALL present phase-oriented progress, always clean up its temporary worktree, and write an ignored structured run record containing identifiers, timestamps, outcome, and verification summaries without task bodies, credentials, or raw model transcripts.

#### Scenario: Run completes successfully
- **WHEN** the validated patch is applied locally
- **THEN** the command reports the change name, changed paths, completed verification, and explicit instructions to inspect and commit or discard the uncommitted changes

#### Scenario: Run fails or is interrupted
- **WHEN** a command, agent stage, validation step, patch application, or operator interruption prevents completion
- **THEN** the temporary worktree is removed, the original checkout remains unchanged unless final patch application had completed atomically, and the run record reports the failed phase and sanitized reason

#### Scenario: GitHub is unavailable
- **WHEN** no GitHub CLI, Project token, repository secret, or network access to GitHub is available
- **THEN** all local preflight, planning, implementation, validation, and review behavior remains available
