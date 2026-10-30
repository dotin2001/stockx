## Purpose

Provide an explicit, phase-scoped, and secret-safe way for approved local AI implementation runs to execute required PostgreSQL tests against an operator-selected disposable database.

## ADDED Requirements

### Requirement: Apply accepts an explicit PostgreSQL test database
The system SHALL recognize `TEST_POSTGRES_DATABASE_URL` when the operator invokes apply, SHALL validate that a non-empty configured value uses a PostgreSQL SQLAlchemy URL before Codex starts, and SHALL make the validated value available to both the implementation process and trusted apply verification. The operator MAY select the same database used for local application development when that database is disposable.

#### Scenario: Operator applies with a valid PostgreSQL test URL
- **WHEN** the operator invokes apply with `TEST_POSTGRES_DATABASE_URL` set to a supported PostgreSQL URL
- **THEN** implementation and host-side changed-area verification receive that exact variable and PostgreSQL-only tests can execute instead of skipping for missing configuration

#### Scenario: Operator applies with an invalid test URL
- **WHEN** `TEST_POSTGRES_DATABASE_URL` is empty, malformed, or uses a non-PostgreSQL dialect
- **THEN** apply fails during preflight before Codex, patch application, or GitHub mutation with an actionable error that does not reveal the configured value

#### Scenario: Operator applies without a test URL
- **WHEN** `TEST_POSTGRES_DATABASE_URL` is absent
- **THEN** existing apply behavior remains available and the runner does not invent or infer a database credential

### Requirement: Test database access is limited to approved apply work
The system SHALL expose `TEST_POSTGRES_DATABASE_URL` only to the approved implementation stage and its trusted verification commands. It SHALL NOT expose the value to plan-stage Codex, plan validation, dry runs, status synchronization, GitHub commands, or unrelated child processes.

#### Scenario: Planning runs while the variable is configured
- **WHEN** the operator starts Markdown or GitHub Project planning with `TEST_POSTGRES_DATABASE_URL` present in the host environment
- **THEN** the plan Codex process and plan validation environment omit the variable

#### Scenario: Approved implementation runs while the variable is configured
- **WHEN** apply passes preflight and starts the implementation stage
- **THEN** only the implementation Codex process and subsequent trusted implementation verification inherit the variable

#### Scenario: Apply dry run validates configuration without exposing it
- **WHEN** the operator invokes apply with `--dry-run` and a configured test URL
- **THEN** preflight validates the URL but no Codex or test process receives it

### Requirement: Test database credentials remain confidential
The system SHALL treat the configured test database URL as sensitive runtime data. It SHALL NOT write the value to run records, prompts, task context, result schemas, normal terminal output, or error messages, and SHALL redact an exact value that appears in captured child-process output.

#### Scenario: Implementation command fails
- **WHEN** a child process fails after receiving `TEST_POSTGRES_DATABASE_URL`
- **THEN** terminal errors and persisted run errors contain no raw database URL or embedded password

#### Scenario: Run record is inspected
- **WHEN** an operator inspects a plan, apply, blocked, failed, or completed run record
- **THEN** the record contains no test database URL, password, or environment dump

### Requirement: Operators are warned about database lifecycle effects
The system SHALL document that PostgreSQL migration tests may downgrade and re-upgrade the selected database schema, that interrupted tests may leave it at an intermediate revision, and that the configured database must not contain irreplaceable or shared data.

#### Scenario: Operator configures the application development database for testing
- **WHEN** the operator chooses to set `TEST_POSTGRES_DATABASE_URL` equal to the local application `DATABASE_URL`
- **THEN** documentation explains that this is supported only when the database is disposable and not concurrently serving work that must remain stable
