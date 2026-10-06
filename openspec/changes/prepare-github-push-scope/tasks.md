## 1. Working Tree Inventory

- [x] 1.1 Run `git status --porcelain --untracked-files=all` and verify the Git-visible file count is recorded with untracked directories expanded.
- [x] 1.2 Run `git status --ignored --short` and verify ignored local artifacts such as env files, virtual environments, dependency installs, caches, build output, logs, and coverage are separated from GitHub candidates.
- [x] 1.3 Run targeted `git check-ignore -v -n --no-index` checks for common frontend/backend generated paths and verify expected source, config, lockfile, and OpenSpec paths are not ignored.

## 2. Candidate Classification

- [x] 2.1 Classify Git-visible files into `include`, `exclude`, and `needs-review` groups and verify each group has an explicit reason.
- [x] 2.2 Verify the `include` group contains only necessary files for the current repository state, such as root package files, `apps/web` source/config files, `.gitignore`, and selected OpenSpec artifacts.
- [x] 2.3 Verify the `include` group contains no `.env` files, virtual environments, dependency install directories, Python caches, Next.js build output, static export output, logs, or coverage reports.

## 3. Push Boundary

- [x] 3.1 Present the final candidate file list and verify no files are staged, committed, or pushed as part of this audit.
- [x] 3.2 If the user approves a follow-up Git operation, stage only the reviewed `include` files and verify `git diff --cached --stat` matches the approved list before any commit or push.
