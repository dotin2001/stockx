## 1. Remove GitHub AI Delivery

- [x] 1.1 Verify `.github/` contains only the AI OpenSpec delivery feature, then remove its workflows and `.github/codex/` helpers; verify no `.github` AI delivery file remains.
- [x] 1.2 Remove `tests/ai-workflow/` and `docs/ai-openspec-delivery.md`; verify neither path remains and no retained test imports the deleted helpers.
- [x] 1.3 Remove `openspec/changes/automate-github-project-ai-openspec-flow/`; verify `openspec list --json` no longer reports that change.

## 2. Make Repository Guidance Local-Only

- [x] 2.1 Remove `ai:workflow:test` and the GitHub workflow test glob from `package.json`; verify the remaining `test`, `ai:local`, and `ai:local:test` commands resolve to retained files.
- [x] 2.2 Remove GitHub Project delivery sections from `AGENTS.md` and `project.md`, and revise the local sections to identify `ai:local` as the only supported AI OpenSpec path; verify neither file references the deleted guide or workflows.
- [x] 2.3 Replace the local guide's dual-mode comparison and workflow-test command with local-only guidance; verify every documented command maps to a retained script.
- [x] 2.4 Update local-runner source-contract test wording and assertions where they describe coexistence with GitHub workflow tests, while retaining checks that the local runner cannot publish or receive GitHub credentials; verify the focused source-contract test passes.

## 3. Validate the Local-Only Result

- [x] 3.1 Search active code, package scripts, tests, and guidance for removed workflow names, `ai:workflow:test`, `tests/ai-workflow`, and `github-project-ai-delivery`; verify any remaining GitHub references are only local-runner non-publication guarantees or historical OpenSpec context.
- [x] 3.2 Run `npm run ai:local:test` and verify all local-runner tests pass.
- [x] 3.3 Run the remaining root `npm test` suite and verify the removal introduces no new failures, recording any unchanged unrelated baseline failures explicitly.
- [x] 3.4 Run strict OpenSpec validation for `add-local-ai-openspec-runner` and `remove-github-ai-delivery`; verify both changes pass and the removal checklist reflects the implemented state.
