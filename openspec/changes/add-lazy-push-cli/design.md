## Context

See `proposal.md` for motivation. The repository currently has a root `package.json` for npm workspace scripts, but no project-local `bin`, `scripts`, or `tools` directory for developer CLI commands. Git is configured on `feature/project-flow` with an upstream at `origin/feature/project-flow`, and the existing `.gitignore` already excludes common local artifacts such as env files, dependency installs, caches, build output, logs, and coverage.

## Goals / Non-Goals

**Goals:**

- Provide a predictable repo-local CLI entry point for `lazy push "<message>"`.
- Keep the command lightweight and portable for this Node-backed repository.
- Make the preflight check conservative enough to stop before publishing likely-local files or unpushable Git states.
- Preserve Git's own output when a Git step fails, so the user can diagnose authentication, remote, or branch problems.

**Non-Goals:**

- Do not add a global installer or machine-wide shell profile changes.
- Do not replace general Git usage or add a full task-runner framework.
- Do not auto-resolve merge conflicts, change remotes, create upstream branches, or delete files.
- Do not run frontend/backend tests automatically before every lazy push unless a later change explicitly adds that behavior.

## Decisions

- Implement the command as a small Node executable exposed through the root package metadata.
  - Rationale: the repository already uses Node/npm at the root, so a dependency-free Node script can run on the supported Node version and can be exposed as a package `bin` named `lazy`.
  - Alternative considered: a Python command. Rejected because the root workflow is npm-based and the Python package is scoped to `apps/api`.
  - Alternative considered: a shell alias or global shell script. Rejected because it would require machine-local setup outside the repo and would be harder to review with the project.
- Keep the CLI dependency-free and call Git through child processes.
  - Rationale: Git is the source of truth for branch, status, staging, commit, and push behavior. Avoiding new dependencies keeps the command simple and avoids changing install surface area.
  - Alternative considered: use a Git wrapper library. Rejected because the workflow is small and direct Git command output is valuable.
- Run preflight checks before `git add .`.
  - Rationale: the user's requested behavior starts by checking file changes and warning when files cannot be pushed. Stopping before staging keeps the working tree easier to reason about when blockers exist.
  - Alternative considered: stage first and inspect the index. Rejected because local-only files should be caught before the command mutates staging state.
- Treat Git-visible local-only artifacts as blockers, and ignored local-only artifacts as informational.
  - Rationale: ignored artifacts will not be included by `git add .`, but visible `.env`, build, cache, dependency, log, coverage, or virtual-environment files are dangerous enough to stop.
  - Alternative considered: block on ignored files too. Rejected because normal local development often has ignored artifacts and blocking them would make the command noisy.
- Report failure at the first blocking condition or failed Git step.
  - Rationale: the command should be fast to understand and should not continue after an unsafe state, failed commit, or failed push.
  - Alternative considered: collect every possible warning before exiting. Rejected for Git failures because later steps depend on earlier state; acceptable for preflight blockers where the implementation can list all detected blockers together.

## Risks / Trade-offs

- Direct `lazy push` availability depends on how the user invokes project-local package bins. -> Add a package `bin` named `lazy`, plus documentation or a script fallback so the command can be run predictably from the repo.
- A conservative local-only pattern could block a legitimate tracked file. -> Print exact paths and reasons without deleting anything, so the user can update `.gitignore`, rename the file, or adjust the blocker rules in a reviewed follow-up.
- `git push` can fail after a commit is created due to authentication, network, protected branches, or remote rejection. -> Report the failed push and leave the commit intact, matching normal Git behavior.
- The command may include unrelated visible work because it intentionally runs `git add .`. -> The preflight output should summarize candidate changes before mutating state, and future enhancements can add an interactive confirmation or path filtering if needed.

## Migration Plan

1. Add a repo-local executable for the `lazy` CLI and expose it through root package metadata.
2. Implement argument parsing for `lazy push "<message>"` and unsupported command handling.
3. Implement preflight Git checks for repository availability, branch/upstream state, unresolved conflicts, visible local-only artifacts, and changed files.
4. Implement the Git action sequence: `git add .`, verify there is a staged diff, `git commit -m`, and `git push`.
5. Add focused verification for success and failure paths using a temporary Git repository where possible.
6. Document how to invoke the command from this repository.

## Open Questions

None.
