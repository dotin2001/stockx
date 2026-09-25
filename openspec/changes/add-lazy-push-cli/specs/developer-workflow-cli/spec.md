## Purpose

Provides repository-local developer workflow commands that automate common Git operations while preserving clear safety checks before publishing changes.

## ADDED Requirements

### Requirement: Lazy push command accepts a commit message
The system SHALL provide a developer command invokable as `lazy push "<commit message>"` for the repository Git workflow.

#### Scenario: Missing commit message is rejected
- **WHEN** a developer runs `lazy push` without a non-empty commit message
- **THEN** the command fails before staging files and explains that a commit message is required

#### Scenario: Unsupported command is rejected
- **WHEN** a developer runs `lazy` with an unsupported subcommand
- **THEN** the command fails before staging files and shows the supported `push` usage

### Requirement: Lazy push blocks unsafe or impossible pushes
Before staging files, the system SHALL inspect repository state and stop when changes cannot be safely pushed by the automated workflow.

#### Scenario: Repository has unresolved merge conflicts
- **WHEN** the Git working tree contains unresolved conflict or unmerged paths
- **THEN** the command fails before staging files and lists the blocking paths

#### Scenario: Repository is not on a pushable branch
- **WHEN** the repository is in a detached HEAD state or the current branch has no upstream remote
- **THEN** the command fails before staging files and explains the branch or upstream issue

#### Scenario: Git-visible local-only files are present
- **WHEN** Git-visible changes include local-only files such as environment files, dependency directories, build output, cache directories, logs, coverage reports, or virtual environments
- **THEN** the command fails before staging files and lists the files that must be ignored, removed, or reviewed before pushing

### Requirement: Lazy push commits and pushes when checks pass
When preflight checks pass, the system SHALL stage all Git-visible changes, create a commit using the supplied message, and push the current branch to its upstream remote.

#### Scenario: Valid changes are pushed
- **WHEN** a developer runs `lazy push "my commit text"` with pushable changes and no blockers
- **THEN** the command runs the equivalent of `git add .`, `git commit -m "my commit text"`, and `git push`

#### Scenario: No committable changes remain after staging
- **WHEN** preflight checks pass but staging results in no committable changes
- **THEN** the command fails before attempting to commit or push and reports that there is nothing to commit

### Requirement: Lazy push reports command outcomes
The system SHALL print clear success or failure output for each automated Git workflow attempt.

#### Scenario: Push succeeds
- **WHEN** staging, commit, and push all succeed
- **THEN** the command reports the created commit and successful push target

#### Scenario: Commit or push fails
- **WHEN** `git commit` or `git push` returns a non-zero exit status
- **THEN** the command reports the failed step and preserves Git's error output for diagnosis
