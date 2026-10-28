# Local AI OpenSpec Runner

The local runner turns one committed Markdown task into an OpenSpec-planned,
validated implementation in the current repository. It runs on this computer,
does not require GitHub CLI or GitHub credentials, and never creates commits,
branches, pushes, issues, comments, or pull requests.

## Prerequisites

- Git and an attached local branch.
- Node.js 18.18 or newer.
- OpenSpec 1.12.x available as `openspec`.
- A Codex CLI that supports `exec`, `--ephemeral`, `--ignore-user-config`,
  `--sandbox`, `--output-schema`, and `--output-last-message`.
- A clean working tree, including no untracked task file. Commit the task and
  runner changes before using the runner.
- Writable operating-system temporary storage.

Check Codex authentication without displaying credentials:

```bash
codex login status
```

The runner normally reuses the authenticated Codex session. Codex also supports
an invocation-scoped `CODEX_API_KEY` or `CODEX_ACCESS_TOKEN`; the runner passes
those variables only to Codex and never reads, prints, or records their values.
Do not store a key in the task file, repository, shell history, or run record.

## Task file

The task must be a non-symlink `.md` file inside this repository with a
first-level heading:

```markdown
# Add catalog empty state

Describe the user-visible behavior and acceptance criteria here.
```

The first heading produces a deterministic bounded change name such as
`local-add-catalog-empty-state`. The command refuses to overwrite an existing
change with that name. Rename the heading deliberately for a distinct run.

Task content is untrusted context. It cannot select commands, credentials,
sandbox modes, protected paths, validation policy, or publication behavior.

## Dry run

From the repository root:

```bash
npm run ai:local -- --task tasks/catalog-empty-state.md --dry-run
```

Dry run checks the task, clean checkout, Git state, tool versions, required
Codex flags, authentication, change-name collision, stale owned worktrees, and
temporary storage. It writes only an ignored `.ai-local/runs/*.json` record. It
does not create a worktree or invoke Codex.

## Run locally

```bash
npm run ai:local -- --task tasks/catalog-empty-state.md
```

The phases are:

1. `preflight`: resolve the committed task and verify the local environment.
2. `worktree`: create an owned detached temporary worktree at the current commit.
3. `planning`: invoke Codex with the trusted propose prompt.
4. Plan validation: allow only the deterministic OpenSpec directory and run
   strict OpenSpec validation.
5. `implementation`: invoke a separate Codex process with the trusted apply
   prompt and accepted plan.
6. `validation`: reject protected paths and incomplete tasks, rerun strict
   OpenSpec validation, and execute trusted changed-area checks.
7. `apply`: recheck the original checkout and apply the binary patch unstaged.
8. `complete`: remove the temporary worktree and report changed paths and checks.

Codex runs with an ephemeral session, ignored user configuration, and the
`workspace-write` sandbox. The local runner never enables automatic approval or
danger-full-access.

## Review the result

Successful output is intentionally uncommitted and unstaged:

```bash
git status --short
git diff --check
git diff
```

Rerun the verification commands printed by the runner. Commit only after human
review. To discard work, restore only the explicit tracked paths you reviewed
and remove only the explicit new files; do not use a repository-wide destructive
reset or clean command.

## Failure and recovery

- A clarification exits before implementation and leaves the checkout unchanged.
- Invalid planning, incomplete tasks, protected-path edits, failed checks, stale
  base state, and patch conflicts leave the checkout unchanged.
- If the checkout changes while agents run, the final patch is refused.
- An interrupted process attempts to stop Codex and remove the owned worktree.
- A failure record identifies the stopped phase with a sanitized reason.

Run records live under `.ai-local/runs/` and are ignored by Git. They contain
task path/hash, base commit, tool versions, phases, outcome, changed paths, and
verification names. They do not contain task bodies, prompts, model transcripts,
environment dumps, or credentials.

If preflight reports a stale owned worktree, inspect it first:

```bash
git worktree list
```

Only paths under the operating system temporary directory named
`stockx-ai-local-*` with a matching `owner.json` marker belong to this runner.
After confirming no process uses the exact path, remove that exact worktree with
`git worktree remove --force <verified-worktree-path>`, remove its marked parent
directory through your normal file manager, and run `git worktree prune`.

## Delivery model

`ai:local` is the repository's only AI OpenSpec delivery path. It reads one
committed local task and leaves a validated local diff for human review. It does
not poll external queues, schedule work, publish branches, or create pull
requests.

## Tests

```bash
npm run ai:local:test
openspec validate add-local-ai-openspec-runner --strict
```
