## Why

The local OpenSpec runner currently inherits Codex's recommended model, which selected GPT-6 Astra and caused otherwise valid runs to fail when that model was at capacity. The runner needs a reviewed, deterministic model policy that uses the operator-requested GPT-5.6 Sol model for both agent stages.

## What Changes

- Pin local planning and implementation Codex invocations to the exact model identifier `gpt-5.6-sol`.
- Keep the model choice in trusted repository code so ignored user configuration and untrusted task or issue content cannot override it.
- Verify the model argument in automated tests and document the pinned execution model for operators.

## Capabilities

### New Capabilities

- `local-ai-runner-model-policy`: Defines the trusted, deterministic Codex model used by every local runner agent stage.

### Modified Capabilities

None.

## Impact

- Affects `automation/ai-local/lib/codex.mjs`, local runner contract tests, and `docs/ai-local-openspec.md`.
- Changes Codex usage, latency, and availability characteristics by selecting GPT-5.6 Sol instead of the CLI's recommended default.
- Does not change task intake, sandboxing, authentication, validation, worktree isolation, or publication behavior.
