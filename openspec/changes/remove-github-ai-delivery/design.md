## Context

See `proposal.md` for motivation. The GitHub delivery feature is entirely repository-local and currently uncommitted: workflows and trusted helpers live under `.github/`, its tests live under `tests/ai-workflow/`, its operator guide is standalone, and its OpenSpec change remains active rather than archived. The local runner is independently implemented under `bin/ai-local.mjs` and `automation/ai-local/`.

The repository guidance and root package scripts currently present both delivery modes, so deleting only the workflow files would leave stale commands and instructions. Removal must therefore be reference-complete while preserving the local runner's source, tests, package entry points, and OpenSpec change.

## Goals / Non-Goals

**Goals:**

- Leave one supported AI delivery path: `npm run ai:local -- --task <path>`.
- Remove every executable, test, documentation, and active planning artifact whose purpose is the GitHub Project delivery feature.
- Keep root tests and local-runner tests free of references to the removed suite.
- Verify no live repository guidance or package command advertises GitHub AI delivery after removal.

**Non-Goals:**

- Changing local-runner orchestration, security policy, task intake, or validation behavior.
- Removing ordinary Git usage or generic language explaining that the local runner does not publish to GitHub.
- Mutating GitHub repository settings, Actions variables, secrets, Projects, branches, issues, or pull requests outside this checkout.
- Archiving the unfinished GitHub delivery change as if it had become supported behavior.

## Decisions

### Delete the GitHub delivery implementation instead of disabling workflows

Remove `.github/workflows/ai-openspec-delivery.yml`, `.github/workflows/ai-openspec-pull-request-observer.yml`, and `.github/codex/` as one feature boundary. Leaving disabled workflows or helper code would preserve unused credential and publication logic and make the repository appear to support two modes.

Alternative considered: keep the implementation with scheduling disabled. Rejected because the requested end state is local-only, not dormant dual-mode support.

### Remove the unfinished OpenSpec change rather than archive it

Delete `openspec/changes/automate-github-project-ai-openspec-flow/`. Its capability was never synchronized into `openspec/specs/`, and its rollout tasks remain incomplete. Archiving it would imply the removed feature is part of accepted project history and could reintroduce misleading requirements.

Alternative considered: retain the change as historical documentation. Rejected because the current work is uncommitted and the artifacts would remain discoverable as an active or completed feature that no longer exists.

### Keep local safety statements about non-publication

The local runner may continue to state that it does not commit, push, create pull requests, or mutate GitHub. These are local-runner safety guarantees rather than remnants of the removed GitHub Actions feature. References that compare two active delivery modes, name removed workflows, or document GitHub Project operation will be removed.

Alternative considered: remove every occurrence of the word GitHub. Rejected because that would weaken useful negative security assertions in the local runner and its tests.

### Make root scripts and documentation local-only

Remove `ai:workflow:test` and the `tests/ai-workflow/*.test.mjs` segment from the root `test` command. Update `AGENTS.md`, `project.md`, `docs/ai-local-openspec.md`, and local source-contract wording so `ai:local` is presented as the only AI OpenSpec delivery mechanism.

Alternative considered: leave compatibility aliases or documentation redirects. Rejected because no consumer contract has been released and the aliases would advertise a removed feature.

## Risks / Trade-offs

- External GitHub Actions variables or secrets may remain configured after repository files are deleted -> Document the out-of-repository cleanup in the handoff; do not attempt to mutate external settings from this change.
- Broad deletion could accidentally remove unrelated GitHub configuration -> Verify `.github/` contains only the AI delivery feature before deleting it, and preserve the directory if unrelated files appear.
- Root test coverage decreases when the GitHub suite is removed -> Retain all local-runner tests and run both the focused local suite and the remaining root suite.
- Historical references may survive in unrelated completed artifacts -> Treat the new removal change as the current source of truth; remove active guidance and executable references, then use targeted searches to identify any misleading live references.

## Migration Plan

1. Remove GitHub workflow/helper files, GitHub delivery tests and guide, and the unfinished GitHub delivery OpenSpec change.
2. Update package scripts and active repository guidance to local-only operation.
3. Update the local guide and source-contract test wording while retaining non-publication guarantees.
4. Search for stale workflow names, package commands, and GitHub delivery capability references.
5. Run local-runner tests, the remaining root tests, strict validation for the local runner and this removal change, and JavaScript syntax checks where applicable.
6. After review, an operator may remove now-unused Actions variables/secrets from GitHub settings; this external cleanup is not performed by repository code.

Rollback is a normal Git revert of this removal before any external credentials are deleted. Restoring external configuration, branches, or Project state is outside the repository rollback.
