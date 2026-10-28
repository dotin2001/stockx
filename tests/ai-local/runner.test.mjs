import assert from "node:assert/strict";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { runCodexStage } from "../../automation/ai-local/lib/codex.mjs";
import { LocalRunError } from "../../automation/ai-local/lib/errors.mjs";
import { runLocalWorkflow } from "../../automation/ai-local/lib/runner.mjs";
import { memoryIo, tempDirectory } from "./support/helpers.mjs";

function context(root) {
  return {
    root,
    baseSha: "a".repeat(40),
    branch: "main",
    tools: { node: "22.0.0", git: "git 2", openspec: "1.12.0", codex: "codex 1", auth: "local-session" },
    task: {
      relativePath: "tasks/pilot.md",
      path: path.join(root, "tasks", "pilot.md"),
      title: "Pilot",
      body: "# Pilot\n",
      hash: "b".repeat(64),
      changeName: "local-pilot",
    },
  };
}

async function harness(overrides = {}) {
  const root = await tempDirectory();
  await mkdir(path.join(root, "tasks"));
  await writeFile(path.join(root, "tasks", "pilot.md"), "# Pilot\n");
  const worktree = await tempDirectory("ai-local-fake-worktree-");
  const calls = [];
  const records = [];
  let captureCount = 0;
  const dependencies = {
    preflight: async () => context(root),
    createWorktree: async () => { calls.push("create"); return { worktree, baseDirectory: worktree, repositoryRoot: root, baseSha: "a".repeat(40) }; },
    cleanupWorktree: async () => { calls.push("cleanup"); await rm(worktree, { recursive: true, force: true }); },
    runStage: async ({ phase }) => { calls.push(phase); return { version: 1, phase, outcome: "success", summary: `${phase} ok`, verification: [] }; },
    captureDiff: async () => {
      captureCount += 1;
      calls.push(`capture-${captureCount}`);
      const plan = [
        "openspec/changes/local-pilot/.openspec.yaml",
        "openspec/changes/local-pilot/proposal.md",
        "openspec/changes/local-pilot/tasks.md",
        "openspec/changes/local-pilot/specs/pilot/spec.md",
      ];
      return { patch: "patch", paths: captureCount === 1 ? plan : [...plan, "docs/pilot.md"] };
    },
    validatePlan: async () => { calls.push("validate-plan"); },
    validateImplementation: async () => { calls.push("validate-implementation"); return ["git diff --check"]; },
    applyPatch: async () => { calls.push("apply"); },
    writeRecord: async (_root, record) => { records.push(structuredClone(record)); return `.ai-local/runs/${record.runId}.json`; },
    ...overrides,
  };
  return { root, calls, records, dependencies };
}

test("orchestration gates implementation and applies only after complete validation", async () => {
  const setup = await harness();
  const captured = memoryIo();
  const result = await runLocalWorkflow({ cwd: setup.root, taskPath: "tasks/pilot.md", io: captured.io, dependencies: setup.dependencies });
  assert.equal(result.outcome, "success");
  assert.deepEqual(setup.calls, ["create", "plan", "capture-1", "validate-plan", "implementation", "capture-2", "validate-implementation", "apply", "cleanup"]);
  assert.equal(setup.records.at(-1).outcome, "success");
  assert.match(captured.read().stdout, /unstaged local changes/);
  assert.doesNotMatch(captured.read().stdout, /pull request created|pushed|committed/i);
});

test("dry run reports stages without worktree, Codex, or patch application", async () => {
  const setup = await harness();
  const captured = memoryIo();
  const result = await runLocalWorkflow({ cwd: setup.root, taskPath: "tasks/pilot.md", dryRun: true, io: captured.io, dependencies: setup.dependencies });
  assert.equal(result.dryRun, true);
  assert.deepEqual(setup.calls, []);
  assert.match(captured.read().stdout, /No Codex stage or temporary worktree/);
});

for (const scenario of [
  {
    name: "clarification",
    overrides: { runStage: async ({ phase }) => ({ version: 1, phase, outcome: "clarification", summary: "Need a decision", verification: [] }) },
    expected: "PLAN_CLARIFICATION",
    forbidden: "implementation",
  },
  {
    name: "planning validation failure",
    overrides: { validatePlan: async () => { throw new LocalRunError("PLAN_INVALID", "bad plan"); } },
    expected: "PLAN_INVALID",
    forbidden: "implementation",
  },
  {
    name: "implementation failure",
    overrides: { runStage: async ({ phase }) => phase === "plan" ? { version: 1, phase, outcome: "success", summary: "ok", verification: [] } : { version: 1, phase, outcome: "failure", summary: "failed", verification: [] } },
    expected: "IMPLEMENTATION_FAILURE",
    forbidden: "apply",
  },
  {
    name: "combined validation failure",
    overrides: { validateImplementation: async () => { throw new LocalRunError("CHECK_FAILED", "failed check"); } },
    expected: "CHECK_FAILED",
    forbidden: "apply",
  },
  {
    name: "original checkout drift",
    overrides: { applyPatch: async () => { throw new LocalRunError("STALE_WORKTREE", "original changed"); } },
    expected: "STALE_WORKTREE",
  },
  {
    name: "interruption",
    overrides: { runStage: async () => { throw new LocalRunError("COMMAND_ABORTED", "interrupted"); } },
    expected: "COMMAND_ABORTED",
    forbidden: "implementation",
  },
]) {
  test(`fake Codex/OpenSpec integration contains ${scenario.name}`, async () => {
    const setup = await harness(scenario.overrides);
    const captured = memoryIo();
    await assert.rejects(
      () => runLocalWorkflow({ cwd: setup.root, taskPath: "tasks/pilot.md", io: captured.io, dependencies: setup.dependencies }),
      (error) => error.code === scenario.expected,
    );
    assert.ok(setup.calls.includes("cleanup"));
    assert.equal(setup.records.at(-1).outcome, "failure");
    if (scenario.forbidden) assert.ok(!setup.calls.includes(scenario.forbidden));
    assert.ok(!setup.calls.includes("apply") || scenario.name === "original checkout drift");
  });
}

test("Codex stage uses trusted prompt/schema and parses fake executable output", async () => {
  const root = await tempDirectory();
  const worktree = await tempDirectory();
  await mkdir(path.join(root, "automation", "ai-local", "prompts"), { recursive: true });
  await mkdir(path.join(root, "automation", "ai-local", "schemas"), { recursive: true });
  await writeFile(path.join(root, "automation", "ai-local", "prompts", "plan.md"), "Plan {{CHANGE_NAME}} from {{TASK_CONTEXT}}");
  await writeFile(path.join(root, "automation", "ai-local", "schemas", "plan-result.schema.json"), "{}");
  let invocation;
  const result = await runCodexStage({
    root,
    worktree,
    phase: "plan",
    changeName: "local-pilot",
    commandRunner: async (command, args, options) => {
      invocation = { command, args, options };
      const resultPath = args[args.indexOf("--output-last-message") + 1];
      await writeFile(resultPath, JSON.stringify({ version: 1, phase: "plan", outcome: "success", summary: "planned", verification: ["strict"] }));
      return { stdout: "", stderr: "" };
    },
  });
  assert.equal(result.outcome, "success");
  assert.equal(invocation.command, "codex");
  assert.match(invocation.options.stdin, /local-pilot/);
  assert.match(invocation.options.stdin, /\.ai-local\/context\/task\.md/);
  assert.equal(invocation.options.env.GITHUB_TOKEN, undefined);
});
