## Purpose

Defines backend runtime configuration behavior so local development commands, database migrations, seed scripts, and API server startup can reliably load environment settings.

## ADDED Requirements

### Requirement: API settings tolerate infrastructure environment variables
The system SHALL load API runtime settings successfully when the environment file also contains infrastructure variables used by local orchestration.

#### Scenario: Settings load with Docker Compose database variables
- **WHEN** the API settings loader reads an environment containing `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT` in addition to known API settings
- **THEN** the settings loader ignores those infrastructure-only variables and successfully exposes the known API settings

#### Scenario: Migration command can load settings from copied example environment
- **WHEN** a developer copies the example environment file to the API environment file and runs database migrations
- **THEN** the migration command loads configuration without failing on infrastructure-only variables

#### Scenario: Seed command can load settings from copied example environment
- **WHEN** a developer copies the example environment file to the API environment file and runs the seed command
- **THEN** the seed command loads configuration without failing on infrastructure-only variables

#### Scenario: API server can boot from copied example environment
- **WHEN** a developer copies the example environment file to the API environment file and starts the FastAPI server
- **THEN** the server imports application settings without failing on infrastructure-only variables

### Requirement: Known API settings remain validated
The system SHALL continue to parse and validate known API runtime settings such as database URL, token settings, refresh-cookie settings, and CORS origins.

#### Scenario: API settings parse expected environment values
- **WHEN** known API runtime settings are supplied through environment variables
- **THEN** the settings loader exposes typed values for database, auth token, refresh cookie, and CORS configuration

#### Scenario: Unknown infrastructure values do not override API settings
- **WHEN** infrastructure-only variables are present alongside known API settings
- **THEN** the infrastructure-only variables do not change the values of known API settings
