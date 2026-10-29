## 1. Pin the trusted execution model

- [x] 1.1 Add the repository-controlled `gpt-5.6-sol` selection to shared Codex argument construction and verify the argument contract covers both agent stages.
- [x] 1.2 Require Codex `exec --model` support during preflight and verify an incompatible CLI fails before model execution.

## 2. Protect and document the policy

- [x] 2.1 Update local runner contract tests to assert the exact `gpt-5.6-sol` model identifier and verify task content or user defaults cannot supply the model.
- [x] 2.2 Document the pinned GPT-5.6 Sol model and required CLI model option in the local runner guide, then verify the documented command remains accurate.

## 3. Validate the change

- [x] 3.1 Run `npm run ai:local:test` and `openspec validate pin-local-runner-gpt-5-6-sol --strict`, recording completion only after both pass.
