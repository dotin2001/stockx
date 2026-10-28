## 1. Intake Contracts and CLI

- [x] 1.1 Extend the `ai:local` argument contract with mutually exclusive Markdown and Project modes, Project owner/number pairing, exact status overrides, issue selector, dry run, and updated help; verify focused CLI tests cover valid forms and reject mixed, partial, duplicate, and non-interactive-invalid forms.
- [x] 1.2 Refactor task resolution into a source-aware immutable task contract for Markdown files and GitHub issues, including bounded canonical-issue change identity and normalized context hashing; verify unit tests cover long repository names, title changes, cross-repository issue numbers, and malicious issue text.
- [x] 1.3 Version run records for allowlisted Markdown or GitHub source metadata without task bodies or credentials; verify serialization tests prove both source kinds are represented and sensitive/raw fields are absent.

## 2. Read-Only GitHub Project Inbox

- [x] 2.1 Add a GitHub CLI adapter that checks executable/authenticated Project access and resolves the configured Project node without exposing command output secrets; verify fake-command tests cover missing `gh`, unauthenticated access, insufficient Project scope, malformed output, and success.
- [x] 2.2 Implement GraphQL Project item pagination, response validation, exact field/value filtering, Issue-only filtering, and deterministic sorting; verify tests combine multiple pages and exclude non-`Todo`, pull request, draft, redacted, and malformed items.
- [x] 2.3 Implement numbered TTY selection, cancellation, and explicit `owner/repo#number` selection for non-interactive use; verify tests cover valid selection, EOF/cancel, invalid input, empty inbox, missing TTY selector, and selectors that are absent or non-unique.
- [x] 2.4 Re-query the selected Project item, confirm current eligibility, and create a frozen allowlisted issue snapshot plus untrusted Markdown context; verify tests cover current, moved, deleted, and authority-seeking issue bodies.

## 3. Local Runner Integration

- [x] 3.1 Split repository/tool preflight so Project mode checks the clean attached checkout before network intake and performs collision/tool checks after snapshot, while Markdown mode retains its existing behavior; verify preflight tests prove GitHub is never required for `--task` and Codex never starts after intake failure.
- [x] 3.2 Connect Project enumeration and selection to the existing worktree plan/validate/apply runner without creating a task file in the original checkout; verify orchestration tests show one selected issue reaches separate planning and implementation stages and produces only a validated unstaged patch.
- [x] 3.3 Update entry-point I/O, phase messages, dry-run behavior, success output, and interrupt handling for Project intake; verify dry-run and cancellation tests create no worktree, invoke no Codex process, apply no patch, and identify the chosen issue when applicable.

## 4. Security and Failure Containment

- [x] 4.1 Keep GitHub authentication confined to the read adapter and exclude GitHub credential variables from Codex, validation, context, output, patches, and records; verify environment and redaction tests with sentinel credentials pass.
- [x] 4.2 Revise source-contract tests to allow only the documented GitHub read transport while continuing to reject Project mutation, issue edits/comments, commits, branches, pushes, pull requests, merges, Actions workflows, unsafe Codex modes, and protected-authority edits; verify the focused source-contract test passes.
- [x] 4.3 Add failure-path orchestration coverage for pagination/access errors, empty inbox, cancellation, stale selection, deterministic collision, planning clarification, plan rejection, implementation failure, validation failure, and checkout drift; verify every case leaves the checkout and GitHub state unchanged and performs no publication command.

## 5. Operator Documentation

- [x] 5.1 Update `docs/ai-local-openspec.md` with GitHub CLI installation/authentication prerequisites, Project read access, interactive and explicit-selector examples, exact `Status=Todo` defaults, dry run, review, manual Project-status handling, and troubleshooting; verify every documented command matches CLI help.
- [x] 5.2 Update `AGENTS.md` and `project.md` to describe the local Project inbox as an intake source while preserving the prohibition on hosted execution, GitHub mutation, credential propagation, and publication; verify searches find no claim that local delivery cannot read GitHub Projects and no restored GitHub Actions workflow.

## 6. Verification

- [x] 6.1 Run `npm run ai:local:test` and the root `npm test`, fix any regressions in scope, and record the passing commands in the implementation handoff.
- [x] 6.2 Run `openspec validate add-local-github-project-inbox --strict` and `git diff --check`, and verify all OpenSpec tasks are complete and the change is strictly valid.
- [x] 6.3 Exercise Markdown dry-run compatibility plus Project-mode help and missing-`gh` diagnostics locally; document that a live Project smoke test requires the operator to install/authenticate `gh` and provide the real Project owner and number.
