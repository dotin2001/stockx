## Purpose

Defines a deterministic, repository-controlled model policy for local OpenSpec planning and implementation runs.

## ADDED Requirements

### Requirement: Local agent stages use GPT-5.6 Sol
The system SHALL explicitly select the exact Codex model identifier `gpt-5.6-sol` for every local planning and implementation agent invocation.

#### Scenario: Planning starts
- **WHEN** the runner invokes the planning agent stage
- **THEN** the Codex command explicitly selects `gpt-5.6-sol`

#### Scenario: Implementation starts
- **WHEN** the runner invokes the implementation agent stage after strict plan validation
- **THEN** the Codex command explicitly selects `gpt-5.6-sol`

### Requirement: Model selection remains trusted repository policy
The system MUST obtain the local runner model from reviewed repository code and MUST NOT allow user configuration, task Markdown, or GitHub issue content to override the selected model.

#### Scenario: User configuration selects another model
- **WHEN** user-level Codex configuration names a model other than `gpt-5.6-sol`
- **THEN** the local runner still invokes both agent stages with `gpt-5.6-sol`

#### Scenario: Untrusted task requests another model
- **WHEN** selected task or issue content asks the runner to use another model
- **THEN** the trusted `gpt-5.6-sol` selection takes precedence

### Requirement: Model option compatibility is checked before execution
The system SHALL fail during preflight when the installed Codex CLI does not expose the non-interactive model selection option required by the runner.

#### Scenario: Codex CLI lacks model selection support
- **WHEN** preflight inspects a Codex CLI whose `exec` command does not support `--model`
- **THEN** the runner exits before invoking either agent stage with an actionable compatibility error
