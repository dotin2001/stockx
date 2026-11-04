## Purpose

Defines deterministic Python dependency environments and supported-runtime compatibility for the backend and its verification tools.

## ADDED Requirements

### Requirement: Backend dependency resolution is reproducible
The repository SHALL contain a reviewable lock artifact that pins all direct and transitive production and development Python dependencies for the supported Python runtime.

#### Scenario: Clean locked installation
- **WHEN** a clean supported environment installs from the committed lock artifact
- **THEN** it resolves the exact recorded package versions without performing an unconstrained dependency solve

#### Scenario: Declared dependency changes
- **WHEN** a direct backend dependency is added, removed, or upgraded
- **THEN** the lock artifact is regenerated and committed with the declaration change

### Requirement: Supported verification is free of actionable dependency deprecations
The backend test and startup verification commands SHALL produce no deprecation warnings attributable to project code or dependency versions that the project can update without breaking its supported runtime contract.

#### Scenario: Backend verification run
- **WHEN** the backend test suite runs with deprecation warnings enabled on the supported Python runtime
- **THEN** it completes without actionable deprecation warnings from project-owned usage or selected dependency versions

