## Context

The local runner already invokes Codex with `--ignore-user-config`, but it does not pass a model argument. Codex therefore chose its recommended model, GPT-6 Astra, and a run failed at implementation when Astra was temporarily at capacity. The exact requested replacement, `gpt-5.6-sol`, is supported by Codex model selection and non-interactive `exec` accepts the same model flag.

The model is part of the runner's trusted execution authority: task and issue text cannot select it, and user defaults must not affect deterministic runner behavior.

## Goals / Non-Goals

**Goals:**

- Select `gpt-5.6-sol` explicitly for both planning and implementation.
- Fail preflight if the installed Codex CLI lacks the required model flag.
- Make the pin observable in contract tests and operator documentation.

**Non-Goals:**

- Add an operator-provided model option or automatic fallback routing.
- Change reasoning effort, service tier, authentication, sandboxing, prompts, or validation.
- Retry transient model failures automatically.

## Decisions

### Pass an explicit model argument in trusted runner code

Define the exact model identifier alongside Codex argument construction and pass `--model gpt-5.6-sol` to every `codex exec` invocation. Argument construction is shared by both stages, so one pin covers planning and implementation without duplicating policy.

An explicit command argument is preferred over `config.toml` because the runner intentionally uses `--ignore-user-config`; relying on user configuration would also make results nondeterministic. An environment variable is rejected because the minimized child environment is intentionally allowlisted and task execution must not influence authority.

### Extend preflight compatibility validation

Add `--model` to the flags required from `codex exec --help`. This preserves the fail-closed behavior used for every other runner-required CLI capability and prevents a run from reaching planning with an incompatible Codex binary.

### Test the exact identifier and document it

Update the argument contract test to assert the exact model flag/value and the source contract to prevent silent removal. Update local runner documentation to list model selection as a prerequisite and identify the pinned model.

## Risks / Trade-offs

- [GPT-5.6 Sol can also become unavailable or reach capacity] → Surface the Codex failure unchanged and keep retry/fallback outside this focused change.
- [A hard pin does not automatically follow future recommended models] → Treat future model changes as reviewed repository policy updates with matching tests and documentation.
- [The authenticated account might not have GPT-5.6 Sol access] → Codex reports the access failure; operators must use an account for which the exact requested model is available.

## Migration Plan

1. Add the explicit model argument and preflight capability check.
2. Update contract tests and operator documentation.
3. Run the local runner test suite and strict OpenSpec validation.
4. Roll back by reverting this focused change if the pinned model is unavailable to the intended account.
