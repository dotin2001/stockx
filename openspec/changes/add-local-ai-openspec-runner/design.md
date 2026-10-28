## Context

See `proposal.md` for motivation and `specs/local-ai-openspec-runner/spec.md` for required behavior. The repository already has a dependency-free Node CLI pattern, OpenSpec 1.12.0, Node 18.18+ support, and trusted planning/implementation conventions in the GitHub delivery automation. The local machine currently has Git, Node, OpenSpec, and Codex CLI installed.

Unlike GitHub Actions, a local process shares a developer checkout and account. The design must preserve pre-existing work, avoid handling credentials, contain partial model output, and make the final diff inspectable before a human commits it.

## Goals / Non-Goals

**Goals:**

- Provide one predictable command for a Markdown task file.
- Keep plan and implementation as separate Codex invocations with a strict validation gate.
- Prevent failed stages from modifying the operator's checkout.
- Use local Codex authentication without copying or persisting secrets.
- Make orchestration deterministic and testable without Codex, network, or GitHub access.

**Non-Goals:**

- Polling GitHub Projects, updating issues, creating branches or pull requests, or observing merges.
- Running unattended schedules, accepting multiple tasks, resuming an existing change, or auto-committing in the first version.
- Providing a general-purpose agent framework or replacing interactive Codex use.
- Supporting dirty starting worktrees or automatically stashing user changes.

## Decisions

### Add a dependency-free Node entry point

Add `bin/ai-local.mjs` with an `ai:local` package script and small importable modules under `automation/ai-local/lib/`. Keep trusted prompts and structured-output schemas under `automation/ai-local/prompts/` and `automation/ai-local/schemas/`. The CLI accepts `--task <repository-relative.md>` and an optional `--dry-run` flag.

Node's standard library is sufficient for argument parsing, child processes, hashing, temporary directories, signals, JSON records, and filesystem validation. This matches the existing `lazy` CLI and avoids adding install or supply-chain requirements.

Alternative considered: a shell script. Rejected because portable path validation, structured process handling, cleanup, and offline unit testing are substantially safer in Node.

### Require a clean attached checkout and safe task file

Resolve the repository root with Git, require an attached branch, reject conflicts and every Git-visible modification, and record `HEAD` as the immutable base. Do not offer an `--allow-dirty` or automatic stash option in the first version because either makes it difficult to prove which changes came from the agent.

Resolve the task with real paths and require it to be a non-symlink regular `.md` file inside the repository. Parse its first `#` heading, slugify it, and derive `local-<bounded-slug>` as the change name. Hash the task contents for the run record. If the derived OpenSpec directory exists, fail before model use; resume and merge semantics are deferred.

Alternative considered: accept task text on the command line. Rejected because quoting, shell history, and multiline input make auditability and safety worse.

### Use an isolated temporary Git worktree as the transaction boundary

Create a temporary detached worktree from the recorded base under the operating system's temporary directory. Copy the task into a run-only context path inside that worktree and label it untrusted. Both Codex stages and all validation run there. Always remove the worktree and temporary directory on success, error, or supported termination signals.

After final validation, create one binary diff against the base, re-check that the original checkout is still clean and at the recorded commit, run `git apply --check --binary`, and apply the patch without staging it. Patch application is the only point at which the original checkout changes.

Alternative considered: run directly in the current checkout and reset on failure. Rejected because reset/cleanup can destroy user data and partial writes are difficult to distinguish from pre-existing work.

### Invoke Codex non-interactively with trusted prompts and structured results

Spawn the installed CLI directly, without a shell, using `codex exec --ephemeral --sandbox workspace-write`, a repository-controlled prompt, an output JSON Schema, and a final-message file. Do not use danger-full-access, automatic approval, or GitHub credentials. The task body remains a file that prompts identify as untrusted context rather than command-line or shell interpolation.

The runner does not inspect or copy authentication material. Codex reuses its supported local authenticated session; invocation-scoped `CODEX_API_KEY` also remains owned by Codex and is never written into a prompt, result, record, or log. Child-process errors and model summaries pass through a secret-redacting sanitizer.

The planning prompt requires `AGENTS.md`, the local propose skill, the exact derived change name, schema-complete artifacts, strict validation, and no non-plan edits. The implementation prompt requires the local apply skill, accepted artifacts as source of truth, truthful task markers, relevant verification, and no Git/GitHub publication.

Alternative considered: one Codex invocation. Rejected because it removes the enforceable plan-only boundary and lets implementation begin before the plan is accepted.

### Validate diffs and checks from trusted policy

Planning validation parses a binary Git diff, rejects unsafe paths, requires every changed path to be under `openspec/changes/<change>/`, verifies schema artifacts, and runs `openspec validate <change> --strict`.

Implementation validation rejects an empty or plan-only diff; protects Git internals, `AGENTS.md`, OpenSpec configuration, skills, GitHub workflows/Codex authority, and all local-runner entry point, prompt, schema, policy, and library paths; requires every task checkbox complete; reruns strict OpenSpec validation; and selects verification commands from a hard-coded changed-area policy rather than task or model output. Commands run in the temporary worktree with a minimized environment and no runner-supplied credentials.

The final patch includes both the new OpenSpec artifacts and implementation. A base hash and task hash bind the run record to its input and starting repository state.

Alternative considered: trust the model's reported checks. Rejected because structured output is a report, not evidence that scope and commands were enforced.

### Keep only sanitized ignored run metadata

Add `.ai-local/` to `.gitignore`. Write `.ai-local/runs/<run-id>.json` atomically with version, task-relative path, task hash, base commit, change name, timestamps, current phase, outcome, changed paths, verification command names, and a sanitized error when applicable. Do not store the task body, prompts, model transcript, environment, or credentials.

Human-facing output is phase oriented and ends with explicit `git diff`/test review guidance. The CLI never stages, commits, pushes, or publishes.

Alternative considered: no run record. Rejected because local failure diagnosis and stale-run identification would otherwise depend on terminal scrollback.

## Risks / Trade-offs

- A clean-worktree requirement is less convenient for active development -> Fail early with instructions to commit or move current work; never stash automatically.
- Local model and validation processes consume developer CPU, disk, and API allowance -> Show stages clearly, support a no-model dry run, process one task, and clean temporary storage.
- Generated test or build code still executes on the developer machine -> Run only trusted changed-area commands in a temporary worktree with a minimized environment and no supplied credentials; require human review of the resulting diff.
- Codex CLI behavior can change across versions -> Validate required flags during preflight, record the detected version, and cover argument construction with offline tests.
- A process kill that cannot run cleanup may leave a registered worktree -> Detect stale owned worktrees during later preflight and document a safe cleanup command; never delete an unverified path.
- Refusing an existing deterministic change prevents convenient retries -> Preserve failed metadata for diagnosis and defer explicit resume semantics rather than guessing how to merge partial plans.
- The repository currently has unrelated root-test failures -> The runner reports any trusted verification failure and does not weaken success criteria; operators must repair or intentionally scope repository health separately.

## Migration Plan

1. Add the CLI modules, trusted prompts/schemas, ignored run-state path, package scripts, and offline unit/contract tests without changing GitHub workflows.
2. Document local Codex authentication, clean-checkout requirements, dry-run behavior, normal execution, review, failure recovery, and stale-worktree cleanup.
3. Run offline CLI tests and strict OpenSpec validation.
4. From a clean disposable branch, dry-run a small Markdown task and verify no Codex invocation or tracked change occurs.
5. Execute one low-risk local task, inspect the unstaged plan and implementation, rerun the reported verification manually, and either commit or discard the diff.
6. Roll back by removing the local runner files and package script; existing GitHub automation is unaffected.
