# Local AI OpenSpec Runner

The local runner turns one explicitly selected task into an OpenSpec-planned,
validated implementation in the current repository. A task can come from a
committed Markdown file or from an issue selected from a GitHub Project inbox.
Both modes run on this computer and leave an unstaged diff for human review.

The GitHub Project mode is read-only. It never changes Project status, edits or
comments on an issue, creates a commit or branch, pushes, opens a pull request,
merges, or invokes GitHub Actions.

## Common prerequisites

- Git and an attached local branch.
- Node.js 18.18 or newer.
- OpenSpec 1.12.x available as `openspec`.
- A Codex CLI that supports `exec`, `--ephemeral`, `--ignore-user-config`,
  `--sandbox`, `--output-schema`, and `--output-last-message`.
- A completely clean working tree, including no untracked files.
- Writable operating-system temporary storage.

Check Codex authentication without displaying credentials:

```bash
codex login status
```

The runner normally reuses the authenticated Codex session. Invocation-scoped
`CODEX_API_KEY` or `CODEX_ACCESS_TOKEN` values are passed only to Codex and are
never read, printed, or recorded. Do not put credentials in tasks or issues.

## Markdown task mode

The task must be a committed, non-symlink `.md` file inside this repository with
a first-level heading:

```markdown
# Add catalog empty state

Describe the user-visible behavior and acceptance criteria here.
```

Run preflight only:

```bash
npm run ai:local -- --task tasks/catalog-empty-state.md --dry-run
```

Run planning and implementation:

```bash
npm run ai:local -- --task tasks/catalog-empty-state.md
```

The heading creates a bounded identity such as `local-add-catalog-empty-state`.
The runner refuses to overwrite an existing OpenSpec change with that name.
Markdown mode does not require GitHub CLI or GitHub authentication.

## GitHub Project inbox mode

Project mode additionally requires GitHub CLI. On macOS it can be installed with
Homebrew; use the equivalent package for other platforms:

```bash
brew install gh
gh auth login
gh auth refresh -s read:project
gh auth status
```

The authenticated account must be able to read the Project and every issue you
intend to select. GitHub credentials remain in the local `gh` session and are
not passed to Codex.

### Interactive selection

From a clean checkout, supply the Project owner and Project number:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7
```

The command reads every Project item across all pages, keeps only GitHub Issues
whose single-select field exactly matches `Status = Todo`, sorts them by
repository and issue number, and prints a numbered list. Pull requests, draft
items, other statuses, redacted items, and malformed entries are excluded. Pick
one number or enter `q` to cancel.

Only the selected issue executes. Immediately before planning, the runner reads
it again and stops if it moved out of `Todo`, disappeared, or changed identity.

### Explicit selection

When stdin is not interactive, or when selecting deterministically, add the
canonical issue identity:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7 \
  --issue 'OWNER/REPOSITORY#123'
```

The issue must still be present in the configured Project inbox. `--issue` does
not bypass Project status filtering.

Projects with different field names or option values can override the exact,
case-sensitive defaults:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7 \
  --status-field Workflow \
  --status-value Ready
```

### Project dry run

Dry run performs the clean-checkout checks, reads the entire inbox, selects and
refreshes one issue, validates the deterministic change identity and local tool
setup, and writes an ignored run record. It does not create a worktree or start
Codex:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7 \
  --issue 'OWNER/REPOSITORY#123' \
  --dry-run
```

## Security boundary

Markdown and GitHub issue text are untrusted context. They cannot select
commands, credentials, sandbox modes, protected paths, validation policy, or
publication behavior. Project mode snapshots allowlisted issue metadata, title,
body, and canonical URL; the body exists only in the owned temporary worktree.

GitHub issue identity, not its editable title, determines the OpenSpec change
name. Rerunning an issue whose deterministic change already exists fails rather
than overwriting it. A successful run does not move the issue out of `Todo`; the
operator updates Project status manually after review.

## Execution phases

1. `preflight`: verify the clean attached checkout and local safety state.
2. `inbox` for Project mode: read all eligible issues, select one, and refresh
   its immutable snapshot.
3. Complete tool/authentication and deterministic collision checks.
4. `worktree`: create an owned detached temporary worktree at the current commit.
5. `planning`: invoke Codex with the trusted propose prompt.
6. Strictly validate the OpenSpec plan before implementation starts.
7. `implementation`: invoke a separate Codex process with the accepted plan.
8. `validation`: reject protected paths and incomplete tasks, validate OpenSpec,
   and run trusted changed-area checks.
9. `apply`: recheck the original checkout and apply the binary patch unstaged.
10. `complete`: remove the temporary worktree and report paths and checks.

Codex uses an ephemeral session, ignored user configuration, and the
`workspace-write` sandbox. Automatic approval and danger-full-access are never
enabled.

## Review the result

Successful output remains uncommitted and unstaged:

```bash
git status --short
git diff --check
git diff
```

Rerun the reported checks and commit only after human review. To discard work,
restore only explicit reviewed paths; do not use a repository-wide destructive
reset or clean command.

## Failure and recovery

- `GITHUB_CLI`: install `gh`, then confirm `gh --version`.
- `GITHUB_AUTH`: run `gh auth login` and grant Project read access.
- `GITHUB_PROJECT_ACCESS`: confirm the owner/number and run
  `gh auth refresh -s read:project`.
- `GITHUB_INBOX_EMPTY`: no issue exactly matches the configured status.
- `GITHUB_ISSUE_SELECTOR`: use the displayed canonical `owner/repo#number`.
- `GITHUB_ISSUE_STALE`: refresh the inbox because the selection changed.
- Planning clarification, invalid plans, failed implementation checks, checkout
  drift, and patch conflicts leave the original checkout unchanged.
- Interruptions attempt to stop Codex and remove the owned worktree.

Run records live under `.ai-local/runs/`. Version 2 records contain the task
hash, allowlisted Markdown path or GitHub issue identity/URL, base commit, tool
versions, phases, outcome, changed paths, and verification names. They exclude
task/issue bodies, titles, raw GitHub responses, prompts, transcripts,
environment dumps, and credentials.

If preflight reports a stale owned worktree, inspect it first:

```bash
git worktree list
```

Only operating-system temporary paths named `stockx-ai-local-*` with a matching
`owner.json` marker belong to this runner. After verifying the exact path is not
in use, remove that worktree explicitly and run `git worktree prune`.

## Delivery model

`ai:local` is the repository's only AI OpenSpec delivery path. It reads one
committed Markdown task or one explicitly selected `Todo` Project issue and
leaves a validated local diff. It does not poll, schedule, batch-execute,
publish, or mutate GitHub.

## Tests

```bash
npm run ai:local:test
openspec validate add-local-github-project-inbox --strict
```
