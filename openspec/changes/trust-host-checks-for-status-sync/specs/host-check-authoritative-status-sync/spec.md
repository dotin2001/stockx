## Purpose

Defines deterministic GitHub Project status synchronization in which repository-owned trusted host checks are the authoritative completion evidence for a local OpenSpec delivery.

## ADDED Requirements

### Requirement: Trusted host checks determine status-sync completion
For a fresh `--sync-status` review, the system MUST derive the Project target exclusively from every trusted host check selected for the stable base-to-current path set. The required set MUST include strict OpenSpec validation and diff validation, plus each path-selected test command. Semantic review output MUST NOT downgrade an all-pass host result.

#### Scenario: All required host checks pass
- **WHEN** every required selected host check completes with `PASS`
- **THEN** the system derives `Done` and prepares the recorded Project item's configured Done transition

#### Scenario: Current backend and runner delivery passes four checks
- **WHEN** the changed paths select strict OpenSpec validation, `git diff --check`, `python -m pytest`, and `npm test`, and all four checks pass
- **THEN** `--sync-status` derives `Done` without requiring a semantic-review PASS report

#### Scenario: A required host check fails
- **WHEN** one or more required host checks execute and return `FAIL`
- **THEN** the system derives `Review`, reports each failing check, and does not derive `Done`

#### Scenario: Host verification is unavailable without a failure
- **WHEN** no required check fails and one or more required checks are `BLOCKED` by an unavailable prerequisite
- **THEN** the system derives `Blocked`, reports the unblocking action, and uses the existing Review fallback when the configured Blocked option is unavailable

#### Scenario: Failed and blocked checks coexist
- **WHEN** the host check set contains both `FAIL` and `BLOCKED` results
- **THEN** the system derives `Review` because an executed failure takes precedence over unavailable verification

### Requirement: All-pass synchronization bypasses semantic gating
The system SHALL NOT invoke or validate Codex semantic review as a prerequisite after every required host check passes. Issue criteria, OpenSpec requirement narratives, design statements, and task evidence SHALL influence `Done` only through repository-owned checks selected by the trusted verification policy.

#### Scenario: Semantic review would report incomplete task evidence
- **WHEN** every required host check passes but a semantic reviewer would classify a task, requirement, or coverage claim as `FAIL`, `BLOCKED`, ambiguous, or incomplete
- **THEN** the system synchronizes `Done` from the host evidence and does not persist that hypothetical semantic classification as a status gate

#### Scenario: Semantic review is unavailable
- **WHEN** every required host check passes and Codex is unavailable, returns malformed output, or would fail report coverage validation
- **THEN** status synchronization remains eligible for `Done` because semantic review is not invoked for the authoritative result

### Requirement: Host-authoritative results remain auditable
The system MUST persist and print the authoritative check names/results, the host-derived target, the completion basis, and the exact pending or synchronized Project transition. An all-pass result MUST clearly state that completion was based on trusted host checks rather than semantic acceptance review.

#### Scenario: Done is synchronized from host evidence
- **WHEN** all required checks pass and GitHub accepts the Done transition
- **THEN** the run record and terminal output identify every passing check, record `Done`, and identify the completion basis as trusted host verification

#### Scenario: Status update must be retried
- **WHEN** authoritative host verification completes but the exact Project mutation fails
- **THEN** the system persists one pending allowlisted transition and the next invocation retries it without rerunning checks

### Requirement: Existing provenance and mutation boundaries remain enforced
Host-authoritative completion MUST retain linked-issue identity verification, recorded branch/base ancestry checks, safe base-to-current path collection, stable snapshot revalidation, exact Project item/field/option allowlisting, credential isolation, and the prohibition on commits, pushes, publication, or issue mutation.

#### Scenario: Provenance or snapshot is unsafe
- **WHEN** recorded provenance cannot be verified or the Git-visible snapshot changes during verification
- **THEN** status sync stops without preparing or mutating Project status even if checks previously passed

#### Scenario: Done transition is allowed
- **WHEN** provenance is valid, the snapshot is stable, every required host check passes, and the Done option resolves uniquely
- **THEN** the host updates only the recorded Project item's recorded Status field

### Requirement: Nonterminal results can advance after a fresh run
A synchronized host-derived `Review` or `Blocked` result MUST remain eligible for a fresh provenance check and host verification. A synchronized `Done` result MUST remain terminal and idempotent for the same recorded task identity.

#### Scenario: Previously failing checks are corrected
- **WHEN** an item is in `Review`, the implementation is corrected, and every required host check passes on the next synchronization
- **THEN** the system may advance the item to `Done`

#### Scenario: A blocked prerequisite is restored
- **WHEN** an item is in `Blocked`, the missing prerequisite becomes available, and every required host check passes on the next synchronization
- **THEN** the system may advance the item to `Done`

