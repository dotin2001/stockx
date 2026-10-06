## 1. CLI Entry Point

- [x] 1.1 Add a dependency-free repo-local `lazy` executable and verify it can print usage output from the repository root.
- [x] 1.2 Expose the executable through root package metadata as the `lazy` bin and verify the package metadata remains valid.
- [x] 1.3 Add documented invocation guidance for direct `lazy push "<message>"` usage and verify the documentation matches the configured entry point.

## 2. Argument Handling

- [x] 2.1 Implement `lazy push "<commit message>"` parsing and verify a valid message reaches the push workflow unchanged.
- [x] 2.2 Reject missing or blank commit messages before staging and verify the command exits non-zero with a clear message.
- [x] 2.3 Reject unsupported subcommands before staging and verify the command exits non-zero with supported usage text.

## 3. Preflight Checks

- [x] 3.1 Detect non-Git directories and verify the command exits non-zero before staging when run outside a repository.
- [x] 3.2 Detect detached HEAD or missing upstream branch configuration and verify the command exits non-zero before staging with the branch issue reported.
- [x] 3.3 Detect unresolved conflict or unmerged paths and verify the command exits non-zero before staging with the blocking paths listed.
- [x] 3.4 Detect Git-visible local-only artifacts such as env files, dependency directories, build output, caches, logs, coverage, and virtual environments, and verify the command exits non-zero before staging with exact path reasons.
- [x] 3.5 Summarize candidate Git-visible changes before mutation and verify ignored local artifacts do not block the command.

## 4. Git Workflow Execution

- [x] 4.1 Run `git add .` only after preflight passes and verify files are staged in a temporary Git repository.
- [x] 4.2 Detect an empty staged diff after `git add .` and verify the command exits non-zero before commit or push.
- [x] 4.3 Run `git commit -m "<commit message>"` after staging and verify the created commit uses the supplied message.
- [x] 4.4 Run `git push` after a successful commit and verify success output includes the commit and upstream target.
- [x] 4.5 Preserve and report Git error output when commit or push fails and verify the command exits non-zero without hiding Git diagnostics.

## 5. Verification

- [x] 5.1 Add focused automated coverage for argument handling, preflight blockers, empty-change handling, and successful Git command sequencing, and verify the tests pass.
- [x] 5.2 Run the repository's relevant lint/type/build checks for changed tooling files, or document why no existing check applies.
- [x] 5.3 Manually smoke-test the documented command invocation in a disposable local Git repository and verify it does not publish this project during testing.
