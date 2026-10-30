# Local AI OpenSpec Runner

`ai:local` is a two-stage, human-approved delivery flow:

```text
Todo issue or Markdown task
  -> isolated OpenSpec proposal
  -> validated plan saved unstaged
  -> STOP for human review
  -> explicit --apply approval
  -> isolated implementation and verification
  -> local unstaged implementation
  -> selected Project item becomes Done or Blocked
```

Planning and implementation are different commands and different Codex
processes. The runner never commits, stages, pushes, opens a pull request,
merges, edits an issue, or invokes GitHub Actions.

## Prerequisites

- Git with an attached branch.
- Node.js 18.18 or newer.
- OpenSpec 1.12.x available as `openspec`.
- Codex CLI with `exec`, `--ephemeral`, `--ignore-user-config`, `--model`,
  `--sandbox`, `--output-schema`, and `--output-last-message`.
- Writable operating-system temporary storage.
- A completely clean checkout before starting a new plan.

Check Codex authentication without displaying credentials:

```bash
codex login status
```

The runner uses the repository-pinned `gpt-5.6-sol` model. Invocation-scoped
`CODEX_API_KEY` or `CODEX_ACCESS_TOKEN` values are passed only to Codex and are
never read, printed, or recorded.

### PostgreSQL verification during apply

Apply can use an explicitly selected PostgreSQL database for implementation and
trusted backend verification. Set `TEST_POSTGRES_DATABASE_URL` before the apply
preflight or apply command:

```bash
export TEST_POSTGRES_DATABASE_URL='postgresql+psycopg://stockx:stockx@localhost:5432/stockx'
(
  cd apps/api
  ALEMBIC_DATABASE_URL="$TEST_POSTGRES_DATABASE_URL" alembic upgrade head
)
npm run ai:local -- --apply <change-name> --dry-run
npm run ai:local -- --apply <change-name>
```

The normal application `DATABASE_URL` is never inferred. If both variables
should intentionally use the same disposable local database, set that choice
explicitly:

```bash
export DATABASE_URL='postgresql+psycopg://stockx:stockx@localhost:5432/stockx'
export TEST_POSTGRES_DATABASE_URL="$DATABASE_URL"
```

The runner validates the URL as PostgreSQL during apply preflight. It passes the
value only to the approved implementation Codex process and trusted
implementation verification; plan runs, status synchronization, GitHub
commands, and unrelated children do not receive it. The value is not printed or
stored in run records, and exact occurrences in child failures are redacted.

Use only a disposable database that is not concurrently serving work that must
remain stable. PostgreSQL identity, migration-lifecycle, and concurrency tests
create isolated records, but migration tests can downgrade and re-upgrade the
entire schema. An interrupted test can leave the database at an intermediate
revision. Starting from a stale revision can also make concurrency tests fail
before the migration-lifecycle tests run, so apply `alembic upgrade head` before
each apply attempt as shown above. Do not point this variable at shared,
production, or irreplaceable data. After an interruption, restore the configured
database to the current revision before retrying:

```bash
cd apps/api
ALEMBIC_DATABASE_URL="$TEST_POSTGRES_DATABASE_URL" alembic upgrade head
```

GitHub Project intake and terminal status updates require the local GitHub CLI
session to have Project access:

```bash
brew install gh
gh auth login
gh auth refresh -s project
gh auth status
```

GitHub credentials remain in the host-side `gh` process and are never passed to
Codex.

## Stage 1: create a plan

### Plan from one selected GitHub issue

To list the configured Project's eligible `Status = Todo` issues and choose one
interactively:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7
```

To select one issue deterministically:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7 \
  --issue 'OWNER/REPOSITORY#123'
```

For this repository's Project 1 and issue 5:

```bash
npm run ai:local -- \
  --project-owner dotin2001 \
  --project-number 1 \
  --issue 'dotin2001/stockx#5'
```

The issue must be in the configured Project and still have the exact source
status. Pull requests, draft items, redacted items, unsupported content, and
other statuses are excluded. Immediately before planning, the selected item is
refreshed and its identity and status are checked again.

Projects with different single-select names can freeze their values into the
plan record:

```bash
npm run ai:local -- \
  --project-owner OWNER \
  --project-number 7 \
  --status-field Workflow \
  --status-value Ready \
  --done-status Complete \
  --blocked-status Blocked \
  --issue 'OWNER/REPOSITORY#123'
```

The source, done, and blocked values must be distinct and are matched exactly.

### Plan from a Markdown task

The task must be a committed, non-symlink `.md` file inside the repository with
a first-level heading:

```bash
npm run ai:local -- --task tasks/catalog-empty-state.md
```

Markdown mode requires no GitHub CLI and never changes external state.

### Plan dry run

Add `--dry-run` to either intake form. Project dry run reads, selects, and
refreshes the issue and verifies local prerequisites. It does not create a
worktree or invoke Codex.

```bash
npm run ai:local -- \
  --project-owner dotin2001 \
  --project-number 1 \
  --issue 'dotin2001/stockx#5' \
  --dry-run
```

### Plan output and review

A successful plan run performs only:

1. Clean-checkout and source preflight.
2. Owned detached temporary worktree creation.
3. One Codex OpenSpec propose process.
4. Plan-only path checks and strict OpenSpec validation.
5. Application of only `openspec/changes/<change-name>/` as unstaged changes.
6. Temporary worktree cleanup and an exact `--apply` command.

It does not run implementation and does not change Project status. Review every
artifact, not only the specification:

```text
openspec/changes/<change-name>/.openspec.yaml
openspec/changes/<change-name>/proposal.md
openspec/changes/<change-name>/design.md
openspec/changes/<change-name>/specs/*/spec.md
openspec/changes/<change-name>/tasks.md
```

You may edit those plan files before approval. They must still pass strict
OpenSpec validation.

## Stage 2: approve and apply

The apply command is the explicit human approval action:

```bash
npm run ai:local -- --apply <change-name>
```

Example for issue 5:

```bash
npm run ai:local -- \
  --apply local-gh-dotin2001-stockx-5-0c4efdf802
```

The plan may remain unstaged and uncommitted, or it may be committed. For an
uncommitted plan, every checkout change must remain inside that exact OpenSpec
change directory and the index must be empty. Apply rejects unrelated or staged
changes.

Apply requires the successful ignored plan record from the same machine. The
record binds the change to its original task or selected Project item. Copying
only the OpenSpec directory to another machine does not grant Project mutation
authority.

Before Codex starts, apply strictly validates the current artifacts and hashes
the human-approved contract. Implementation may update task checkbox states but
cannot rewrite proposal, design, specification, schema metadata, or task text.
It must produce non-planning changes, complete every task, and pass trusted
changed-area checks.

Test apply preflight without invoking Codex or changing the Project:

```bash
npm run ai:local -- --apply <change-name> --dry-run
```

## GitHub Project status outcomes

Only GitHub-backed apply runs can mutate Project state. The host runner resolves
the recorded Project, selected item, status field, and allowlisted option IDs.
Issue or plan text cannot choose a different item, field, or status.

| Apply outcome | Project result |
|---|---|
| Validated implementation patch reaches the local checkout | `Done` |
| Structured missing requirement, external dependency, or required human decision | `Blocked` |
| Token/capacity failure, interruption, command failure, failed verification, invalid output, or checkout drift | remains source status, normally `Todo` |

Technical failures leave the Project item in its source status and remain safe
to retry after the underlying problem is corrected.

`Done` means the verified implementation reached the local checkout as unstaged
changes. It does not mean the code was committed, pushed, or merged.

Partial output from a blocked implementation is discarded. No implementation
patch reaches the checkout before `Blocked` is set.

## Status-sync recovery

Local patch application and a remote Project update cannot be atomic. If the
local implementation succeeds but the status update fails, the patch remains
in the checkout and the run record keeps one pending allowlisted transition.
Retry only that transition without rerunning Codex:

```bash
npm run ai:local -- --sync-status <change-name>
```

The retry is idempotent: if GitHub accepted the earlier update but the local
process failed before recording it, synchronization succeeds without changing
anything else. A missing or ambiguous pending record is rejected.

## Security boundary

Task and issue content are untrusted during planning. They cannot change the
model, prompts, schema, sandbox, credentials, commands, protected paths, or
publication policy. During apply, only the human-reviewed OpenSpec artifacts are
task context.

Both Codex stages use an ephemeral session, ignored user configuration,
`gpt-5.6-sol`, and the `workspace-write` sandbox. Codex receives no GitHub
credentials. The host runner's only GitHub mutation is the exact selected
Project item's recorded single-select status field.

## Run records

Ignored version 3 records live under `.ai-local/runs/`. They contain allowlisted
source identity, mode, task and plan hashes, base commit, phases, outcomes,
changed paths, verification names, parent plan identity, and pending or completed
status synchronization.

They exclude task and issue bodies, titles, prompts, raw model transcripts, raw
GitHub responses, environment dumps, and credentials.

## Review and recovery

Inspect successful plan or implementation output with:

```bash
git status --short
git diff --check
git diff
```

Do not use a repository-wide destructive reset or clean command to discard work.
Restore only explicit reviewed paths.

Common errors:

- `PLAN_RECORD_MISSING`: apply must run on the machine that created the plan.
- `WORKTREE_DIRTY`: remove, commit, or move unrelated checkout changes.
- `GITHUB_AUTH`: run `gh auth login` and grant Project access.
- `GITHUB_ISSUE_STALE`: reconcile the item because its identity or status changed.
- `GITHUB_STATUS_FIELD` or `GITHUB_STATUS_OPTION`: verify exact Project field and option names.
- `STATUS_SYNC_FAILED`: keep the local patch and use the printed `--sync-status` command.

If a stale owned worktree is reported, inspect `git worktree list`. Only temporary
paths named `stockx-ai-local-*` with a matching `owner.json` marker belong to the
runner.

## Tests

```bash
npm run ai:local:test
openspec validate split-ai-local-plan-apply --strict
```
