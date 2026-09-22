## Context

See `proposal.md` for motivation. The current working tree shows `.gitignore` modified, untracked root npm workspace files, untracked `apps/web` source/config files, and untracked OpenSpec change artifacts. A `git status --ignored --short` check also shows local backend env/cache/venv artifacts are ignored, while `apps/web` contains 47 files and the relevant Git-visible candidate set is around 59 entries rather than thousands.

## Goals / Non-Goals

**Goals:**

- Produce a clear candidate file list for GitHub that separates required source/config/planning files from generated or local-only files.
- Verify `.gitignore` catches dependency installs, build output, env files, caches, logs, and coverage before staging.
- Make the push boundary explicit: no commit or push happens until the candidate file list has been reviewed and approved.

**Non-Goals:**

- Do not implement application behavior changes.
- Do not delete local ignored artifacts unless a later implementation step identifies a safe cleanup and the user explicitly wants it.
- Do not stage, commit, or push automatically as part of the audit.
- Do not remove user work from the working tree.

## Decisions

- Use Git's own views as the source of truth for push scope.
  - Rationale: `git status --porcelain --untracked-files=all`, `git status --ignored --short`, and `git check-ignore` reveal what can be committed and what is excluded.
  - Alternative considered: filesystem-only counts; rejected because they include ignored local artifacts that GitHub will not receive.
- Classify files into include, exclude, and needs-review groups.
  - Rationale: source/config/lockfile/OpenSpec artifacts are likely legitimate, while env/cache/build/dependency files should stay out, and any unexpected large/binary files need human review.
  - Alternative considered: stage every visible file; rejected because it can accidentally publish unfinished planning changes or unrelated user work.
- Keep push as a separate action after review.
  - Rationale: the user specifically asked whether only necessary files should go to GitHub, so implementation should stop at an auditable staging recommendation unless explicitly told to commit or push.
  - Alternative considered: automatically push the cleaned set; rejected because publishing is an external side effect that should require a fresh explicit request.

## Risks / Trade-offs

- A legitimate new file could be misclassified as unnecessary. -> Keep a `needs-review` group and do not delete or hide files silently.
- A generated artifact could remain Git-visible if `.gitignore` misses it. -> Run ignored checks and direct `git check-ignore` checks for common generated paths before recommending staging.
- Existing untracked OpenSpec changes may not all belong in the same GitHub push. -> Report each change directory separately so the user can decide whether to include completed planning/application artifacts together.
- Local ignored files may still consume disk space even though they will not push. -> Call them out separately as optional local cleanup, not as commit blockers.

## Migration Plan

1. Generate a full Git-visible inventory with untracked files expanded.
2. Generate an ignored-file inventory to prove local artifacts are excluded from GitHub.
3. Classify candidate files into include, exclude, and needs-review groups.
4. Verify the include group does not contain env files, dependency installs, caches, build output, coverage, or logs.
5. Present the final candidate list and wait for an explicit staging/commit/push request.

## Open Questions

None.
