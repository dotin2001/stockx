## Context

See `proposal.md` for motivation and `specs/local-github-project-inbox/spec.md` for behavior. The current `ai:local` entry point accepts one committed Markdown path, resolves it into a task object, verifies a clean attached checkout, and feeds an ephemeral copy of the task to separate Codex planning and implementation processes in an owned temporary worktree. GitHub credentials are already excluded from Codex's allowlisted child environment, and final output is a validated unstaged patch.

The new source is remote, mutable, and untrusted. Intake therefore has to finish and freeze a selected issue before any model process starts, without weakening the existing task-file path. GitHub CLI is not currently installed on the development machine, so Project mode must diagnose that prerequisite clearly; Markdown mode must not acquire the dependency.

## Goals / Non-Goals

**Goals:**

- Make `ai:local` support two explicit, mutually exclusive task sources: a committed Markdown file or one selected Project issue.
- Enumerate the complete configured Project inbox and make the operator's choice visible and deliberate.
- Reuse one task abstraction and the existing worktree, plan validation, implementation validation, and patch application pipeline after intake.
- Keep GitHub access read-only and keep GitHub authentication outside model processes and persistent records.
- Make intake deterministic and unit-testable without live GitHub access.

**Non-Goals:**

- Running the flow in GitHub Actions or as a scheduler/daemon.
- Updating Project status, assigning issues, adding comments, or otherwise acknowledging completion on GitHub.
- Creating commits, branches, pushes, pull requests, reviews, or merges.
- Batch-executing every `Todo` item; the complete inbox is fetched, but exactly one issue is executed per invocation.
- Replacing the existing Markdown task mode.

## Decisions

### Extend `ai:local` with a mutually exclusive Project source

Keep one delivery command and add this interface:

```text
npm run ai:local -- --task <repository-relative.md> [--dry-run]
npm run ai:local -- --project-owner <login> --project-number <number> [--status-field Status] [--status-value Todo] [--issue <owner/repo#number>] [--dry-run]
```

`--project-owner` and `--project-number` are required together. `--issue` is optional in a TTY and required when stdin is not interactive; it identifies one item from the already-filtered inbox rather than bypassing Project eligibility. Status field and value comparisons are exact and case-sensitive.

This keeps Project intake visibly local and preserves one plan/apply implementation. A separate `ai:project` command was considered, but it would duplicate lifecycle ownership and make the repository appear to have two AI delivery engines. A committed Project configuration file was also considered, but owner and number are operational inputs and do not need to become protected repository authority.

### Use the authenticated GitHub CLI as a narrow read transport

Project mode first runs GitHub CLI authentication/access checks, resolves the Project node with a read-only formatted Project view, then uses `gh api graphql` with the Project node ID. The GraphQL query requests up to 100 items per page, the configured single-select field value, and Issue content metadata; the intake module follows `pageInfo.endCursor` until `hasNextPage` is false. Querying by Project node ID avoids separate organization-versus-user GraphQL shapes.

The GitHub process inherits only the environment needed to locate the executable and the operator's local CLI/keychain session. GitHub token variables remain outside the general child environment and all Codex invocations. Access-query failure is treated as the authoritative authentication/scope check, with remediation directing the operator to authenticate `gh` and grant Project read access.

Direct REST/GraphQL calls from Node were considered, but would add token parsing and storage responsibility. `gh project item-list --limit <large-number>` was considered, but a guessed limit does not prove the complete inbox was read.

### Separate intake from execution with an immutable task-source object

Refactor task resolution into a common immutable task shape containing title, normalized Markdown body, hash, change name, and allowlisted source metadata. File intake continues to populate a repository path source. Project intake populates a GitHub issue source containing Project owner/number, repository name, issue number, canonical URL, and Project item ID.

After selection, intake re-queries the selected Project item by node ID, confirms the exact configured status, and snapshots current Issue metadata. It then builds normalized untrusted Markdown context with a generated heading and source reference around the issue body. The body is written only to the owned worktree's mode-0600 task context and is represented in run records only by its hash.

Passing a newly generated task file through the original checkout was considered, but it would intentionally dirty the checkout and conflict with the clean-tree safety gate. Running directly from mutable list results was considered, but it creates a selection-to-planning race.

### Derive execution identity from canonical issue identity

Project tasks use a bounded change name formed from the canonical repository owner/name, issue number, and a short hash of the canonical issue URL. The title is not part of identity. The existing collision check remains authoritative, so rerunning an already materialized issue cannot overwrite its OpenSpec artifacts.

Title-based names were considered, but a title edit could create a second identity for the same issue; issue-number-only names were considered, but collide across repositories in a multi-repository Project.

### Perform local safety checks before and after interactive selection

Before network intake, Project mode discovers the repository, requires an attached clean checkout, and checks temporary/worktree safety. After selection and fresh snapshot, it checks deterministic change collision and the existing Codex/OpenSpec prerequisites before creating a run record or worktree. The final patch application continues to recheck the original base and checkout state.

The prompt uses Node's terminal input/output primitives so no UI dependency is added. Items are sorted by repository name and numeric issue number before numbering. EOF, interrupt, invalid input, and explicit cancellation terminate without model use. `--dry-run` still performs Project enumeration, selection, fresh snapshot, and all preflight checks, but creates neither a worktree nor a Codex process.

### Keep Project behavior behind injected adapters and source-contract tests

Place GitHub querying, response validation, filtering, pagination, selection, and snapshot conversion in focused modules with command and prompt adapters supplied as dependencies. Tests use recorded in-memory JSON shapes and fake command results; the normal test suite does not require GitHub CLI, credentials, or network access.

Source-contract tests continue forbidding GitHub publication and mutation commands. They are narrowed from forbidding every GitHub read symbol to permitting only the documented read-only Project/issue transport. End-to-end orchestration tests prove that selection cancellation, empty inboxes, stale status, malformed responses, access failure, planning failure, and validation failure never apply a patch or mutate GitHub.

### Version run metadata to describe either source without persisting issue text

Run records move to a source-aware schema that stores a task hash, change name, and an allowlisted source descriptor. Markdown sources record the repository-relative path; GitHub sources record only Project identity, canonical repository/issue identity, and URL. Issue titles and bodies, raw GitHub responses, prompts, transcripts, environment dumps, and credentials are not stored.

The console identifies the selected issue and local change so the operator can correlate results. Errors are sanitized through the existing error boundary before display or recording.

## Risks / Trade-offs

- [Project schema or GitHub GraphQL output changes] → Validate every response shape, fail closed with an actionable message, and isolate queries/parsers behind tests.
- [Large Projects make interactive startup slow] → Fetch pages sequentially with a bounded page size, show an intake phase, and avoid retrieving bodies until one item is selected.
- [Issue changes between list and execution] → Re-query the chosen Project item and issue immediately before planning; stop if it is no longer eligible.
- [Read-only intent is weakened by future edits] → Keep GitHub operations in a narrow module and assert forbidden mutation/publication verbs and credential propagation in source-contract tests.
- [A successful issue remains in `Todo` and appears again] → Preserve the requested read-only boundary; deterministic change collision prevents silent duplicate execution, and the operator moves Project status manually.
- [Project mode cannot run until GitHub CLI is installed and authorized] → Keep Markdown mode independent and document installation, login, and Project-read remediation before the first Project run.
- [Interactive prompting is unavailable in CI or redirected shells] → Require the explicit `--issue owner/repo#number` selector when no TTY exists; this remains a local single-issue run rather than hosted automation.

## Migration Plan

1. Add Project intake modules and source-aware task/run-record contracts behind the new CLI option set.
2. Add fake-transport unit and orchestration coverage, then revise source-contract assertions to allow read-only intake while continuing to forbid mutation and publication.
3. Update local operator documentation and repository guidance with GitHub CLI prerequisites and examples.
4. Validate the existing Markdown flow and the new Project dry-run flow; live Project verification is performed only after the operator installs/authenticates GitHub CLI and supplies a Project owner/number.
5. Roll back by reverting this change's code and documentation. Markdown `--task` behavior remains the compatibility baseline, and no GitHub state requires rollback because Project mode performs no mutations.
