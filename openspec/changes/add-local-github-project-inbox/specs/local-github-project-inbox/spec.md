## Purpose

Provide a local, operator-controlled inbox that reads eligible GitHub Project issues and submits exactly one explicitly selected issue to the existing isolated OpenSpec planning and implementation pipeline.

## ADDED Requirements

### Requirement: Project-backed intake is an explicit local mode
The system SHALL preserve Markdown `--task` intake and SHALL add a mutually exclusive GitHub Project intake mode that requires a Project owner and Project number. Project intake SHALL default to the field name `Status` and option value `Todo`, while allowing the operator to override both values explicitly.

#### Scenario: Operator starts Project intake
- **WHEN** the operator supplies a Project owner and number instead of `--task`
- **THEN** the system enters GitHub Project intake mode using `Status=Todo` unless explicit field and option overrides were supplied

#### Scenario: Operator supplies conflicting intake sources
- **WHEN** the operator supplies both a Markdown task and GitHub Project intake options
- **THEN** the system rejects the invocation before accessing GitHub or starting Codex

#### Scenario: Existing Markdown mode remains independent
- **WHEN** the operator supplies only a valid committed Markdown task
- **THEN** the existing local task flow runs without requiring GitHub CLI or GitHub authentication

### Requirement: GitHub prerequisites fail closed
Before reading Project data, the system SHALL verify that GitHub CLI is available, locally authenticated, and able to read the configured Project. A failed prerequisite SHALL produce a sanitized actionable error and SHALL prevent all Codex and OpenSpec agent stages.

#### Scenario: GitHub CLI is unavailable
- **WHEN** Project intake is requested and GitHub CLI cannot be executed
- **THEN** the system reports the missing prerequisite and does not start Codex

#### Scenario: Authentication or Project access is insufficient
- **WHEN** GitHub CLI is not authenticated or the authenticated account cannot read the configured Project
- **THEN** the system reports an authentication or access error without exposing credentials and does not start Codex

### Requirement: All eligible Todo issues are enumerated
The system SHALL read every item in the configured GitHub Project across all result pages, select items whose configured status exactly equals the configured `Todo` value, and include only GitHub Issue content. Pull requests, draft items, redacted items, and unsupported content types SHALL not be offered for execution.

#### Scenario: Project contains multiple pages of items
- **WHEN** eligible issues exist beyond the first GitHub response page
- **THEN** the selection list includes those issues as well as eligible issues from earlier pages

#### Scenario: Project contains mixed content and statuses
- **WHEN** the Project contains `Todo` issues, non-`Todo` issues, pull requests, and draft items
- **THEN** only issues with an exact matching `Todo` status are offered

#### Scenario: No eligible issues exist
- **WHEN** the complete Project contains no eligible `Todo` issues
- **THEN** the system reports that the inbox is empty and exits without starting Codex or modifying the checkout

### Requirement: One issue requires explicit operator selection
In an interactive terminal, the system SHALL display a stable numbered list containing each eligible issue's repository, issue number, and title, and SHALL require the operator to select exactly one issue or cancel. The system SHALL also provide an explicit issue-identity selector for deterministic non-interactive use, and that identity SHALL resolve to exactly one currently eligible item.

#### Scenario: Operator chooses an issue interactively
- **WHEN** the operator enters the number of one displayed issue
- **THEN** only that issue proceeds to snapshot and local execution

#### Scenario: Operator cancels selection
- **WHEN** the operator cancels or closes the selection prompt
- **THEN** the system exits without starting Codex or modifying the checkout

#### Scenario: Non-interactive selector is invalid or ambiguous
- **WHEN** a supplied issue identity does not resolve to exactly one eligible Project item
- **THEN** the system rejects the invocation before starting Codex

### Requirement: Selected issue is frozen as untrusted task context
Immediately before planning, the system SHALL retrieve a fresh snapshot of the selected issue and confirm that its Project item still has the configured `Todo` status. The snapshot SHALL contain only allowlisted source metadata, title, body, and canonical URL; its text SHALL be treated as untrusted task data and SHALL not be allowed to change runner authority, prompts, schemas, validation policy, credentials, or protected paths.

#### Scenario: Selected issue remains eligible
- **WHEN** the fresh issue snapshot succeeds and its Project status still matches `Todo`
- **THEN** the system derives a deterministic identity from the canonical repository and issue number and supplies the frozen snapshot to planning

#### Scenario: Selected issue changed after listing
- **WHEN** the selected item no longer has the configured `Todo` status or the issue became unavailable
- **THEN** the system stops before planning and asks the operator to refresh the inbox

#### Scenario: Issue body contains instructions targeting runner authority
- **WHEN** the issue body requests credentials, publication, unsafe access, or edits to protected automation authority
- **THEN** the content remains untrusted context and cannot grant those capabilities

### Requirement: Selected issue uses the existing gated local execution pipeline
After intake succeeds, the system SHALL run the existing clean-checkout preflight, isolated planning process, strict plan validation, separate implementation process, changed-area validation, and unstaged patch application. A deterministic OpenSpec change name SHALL be based on canonical issue identity so title edits cannot silently create a different execution identity.

#### Scenario: Selected issue completes successfully
- **WHEN** planning, implementation, and every validation step succeed
- **THEN** the original checkout receives only the validated unstaged patch for human review and the output identifies the source issue

#### Scenario: Planning requires clarification
- **WHEN** the planning process cannot safely resolve the selected issue
- **THEN** implementation does not start and the checkout remains unchanged

#### Scenario: Existing issue change collides
- **WHEN** the deterministic OpenSpec change for the canonical issue identity already exists
- **THEN** the system reports the collision and does not start Codex or overwrite the existing change

### Requirement: GitHub access remains read-only and local
The system SHALL use GitHub only to read Project and issue data from the local operator session. It SHALL NOT mutate Project fields, edit or comment on issues, create commits or branches, push, open or merge pull requests, install GitHub Actions workflows, or pass GitHub credentials into Codex processes, task snapshots, patches, output, or run records.

#### Scenario: Project-backed run finishes or fails
- **WHEN** any Project-backed run reaches a terminal outcome
- **THEN** GitHub Project and issue state remain unchanged and no publication action has occurred

#### Scenario: Codex process is created
- **WHEN** planning or implementation starts for a GitHub issue snapshot
- **THEN** the Codex child environment contains no GitHub authentication credential

#### Scenario: Run metadata is recorded
- **WHEN** the runner writes a local run record
- **THEN** the record may contain allowlisted issue identity and URL metadata but contains neither issue body nor GitHub credentials
