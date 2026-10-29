import assert from "node:assert/strict";
import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { runCodexStage } from "../../automation/ai-local/lib/codex.mjs";
import { LocalRunError } from "../../automation/ai-local/lib/errors.mjs";
import { runLocalWorkflow } from "../../automation/ai-local/lib/runner.mjs";
import { memoryIo, tempDirectory } from "./support/helpers.mjs";

const baseSha = "a".repeat(40);
const taskHash = "b".repeat(64);
const planHash = "c".repeat(64);
const planPaths = [
  "openspec/changes/local-pilot/.openspec.yaml",
  "openspec/changes/local-pilot/proposal.md",
  "openspec/changes/local-pilot/tasks.md",
  "openspec/changes/local-pilot/specs/pilot/spec.md",
];

function tools() {
  return { node: "22.0.0", git: "git 2", openspec: "1.12.0", codex: "codex 1", auth: "local-session" };
}

function task(root, source = { kind: "markdown", path: "tasks/pilot.md" }) {
  return { path: path.join(root, "tasks", "pilot.md"), relativePath: "tasks/pilot.md", title: "Pilot", body: "# Pilot\n", hash: taskHash, changeName: "local-pilot", source };
}

function planRecord(source = { kind: "markdown", path: "tasks/pilot.md" }) {
  return { version: 3, runId: "plan-run", mode: "plan", source, taskHash, changeName: "local-pilot", baseSha, branch: "main", phase: "complete", outcome: "success", approvedPlanHash: planHash, tools: tools() };
}

async function commonHarness() {
  const root = await tempDirectory();
  await mkdir(path.join(root, "tasks"));
  await writeFile(path.join(root, "tasks", "pilot.md"), "# Pilot\n");
  const worktree = await tempDirectory("ai-local-fake-worktree-");
  const calls = [];
  const records = [];
  const lifecycle = {
    createWorktree: async () => { calls.push("create"); return { worktree, baseDirectory: worktree, repositoryRoot: root, baseSha }; },
    cleanupWorktree: async () => { calls.push("cleanup"); await rm(worktree, { recursive: true, force: true }); },
    writeRecord: async (_root, record) => { records.push(structuredClone(record)); return `.ai-local/runs/${record.runId}.json`; },
  };
  return { root, worktree, calls, records, lifecycle };
}

test("intake runs planning only, applies only the plan, and prints approval command", async () => {
  const setup = await commonHarness();
  const captured = memoryIo();
  const dependencies = {
    ...setup.lifecycle,
    preflight: async () => ({ root: setup.root, baseSha, branch: "main", tools: tools(), task: task(setup.root) }),
    runStage: async ({ phase }) => { setup.calls.push(phase); return { version: 1, phase, outcome: "success", summary: "planned", verification: [] }; },
    captureDiff: async () => { setup.calls.push("capture"); return { patch: "plan-patch", paths: planPaths }; },
    validatePlan: async () => { setup.calls.push("validate-plan"); },
    hashPlan: async () => { setup.calls.push("hash-plan"); return { hash: planHash, paths: planPaths }; },
    applyPatch: async () => { setup.calls.push("apply-plan"); },
  };
  const result = await runLocalWorkflow({ mode: "plan", cwd: setup.root, taskPath: "tasks/pilot.md", io: captured.io, dependencies });
  assert.equal(result.outcome, "success");
  assert.deepEqual(setup.calls, ["create", "plan", "capture", "validate-plan", "hash-plan", "apply-plan", "cleanup"]);
  assert.match(captured.read().stdout, /Implementation did not run/);
  assert.match(captured.read().stdout, /--apply local-pilot/);
  assert.equal(setup.records.at(-1).approvedPlanHash, planHash);
});

test("plan dry run starts neither Codex nor a worktree", async () => {
  const setup = await commonHarness();
  const captured = memoryIo();
  const result = await runLocalWorkflow({
    mode: "plan", cwd: setup.root, taskPath: "tasks/pilot.md", dryRun: true, io: captured.io,
    dependencies: { ...setup.lifecycle, preflight: async () => ({ root: setup.root, baseSha, branch: "main", tools: tools(), task: task(setup.root) }) },
  });
  assert.equal(result.dryRun, true);
  assert.deepEqual(setup.calls, []);
  assert.match(captured.read().stdout, /stop for human review/);
});

for (const scenario of [
  { name: "clarification", code: "PLAN_CLARIFICATION", runStage: async ({ phase }) => ({ version: 1, phase, outcome: "clarification", summary: "Need a decision", verification: [] }) },
  { name: "invalid plan", code: "PLAN_INVALID", validatePlan: async () => { throw new LocalRunError("PLAN_INVALID", "bad plan"); } },
  { name: "checkout drift", code: "STALE_WORKTREE", applyPatch: async () => { throw new LocalRunError("STALE_WORKTREE", "changed"); } },
  { name: "interruption", code: "COMMAND_ABORTED", runStage: async () => { throw new LocalRunError("COMMAND_ABORTED", "interrupted"); } },
]) {
  test(`plan failure containment handles ${scenario.name}`, async () => {
    const setup = await commonHarness();
    let mutations = 0;
    const dependencies = {
      ...setup.lifecycle,
      preflight: async () => ({ root: setup.root, baseSha, branch: "main", tools: tools(), task: task(setup.root) }),
      runStage: scenario.runStage || (async ({ phase }) => ({ version: 1, phase, outcome: "success", summary: "planned", verification: [] })),
      captureDiff: async () => ({ patch: "plan-patch", paths: planPaths }),
      validatePlan: scenario.validatePlan || (async () => {}),
      hashPlan: async () => ({ hash: planHash, paths: planPaths }),
      applyPatch: scenario.applyPatch || (async () => {}),
      updateStatus: async () => { mutations += 1; },
    };
    await assert.rejects(() => runLocalWorkflow({ mode: "plan", cwd: setup.root, taskPath: "tasks/pilot.md", io: memoryIo().io, dependencies }), (error) => error.code === scenario.code);
    assert.equal(mutations, 0);
    assert.equal(setup.records.at(-1).outcome, "failure");
    assert.ok(setup.calls.includes("cleanup"));
  });
}

function applyDependencies(setup, overrides = {}, source = { kind: "markdown", path: "tasks/pilot.md" }) {
  return {
    ...setup.lifecycle,
    preflightApply: async () => ({
      root: setup.root,
      planRecord: planRecord(source),
      approvedPlan: { hash: planHash, paths: planPaths },
      baseSha,
      branch: "main",
      tools: tools(),
      planDirty: false,
      statusSnapshot: "",
    }),
    planPaths: async () => planPaths,
    validatePlan: async () => { setup.calls.push("validate-plan"); },
    hashPlan: async () => ({ hash: planHash, paths: planPaths }),
    runStage: async ({ phase }) => { setup.calls.push(phase); return { version: 1, phase, outcome: "success", summary: "implemented", verification: [] }; },
    captureImplementationDiff: async () => { setup.calls.push("capture-implementation"); return { patch: "implementation-patch", paths: ["openspec/changes/local-pilot/tasks.md", "docs/pilot.md"] }; },
    validateImplementation: async () => { setup.calls.push("validate-implementation"); return ["git diff --check"]; },
    applyImplementationPatch: async () => { setup.calls.push("apply-implementation"); },
    ...overrides,
  };
}

test("explicit apply runs implementation without proposal generation", async () => {
  const setup = await commonHarness();
  const captured = memoryIo();
  const result = await runLocalWorkflow({ mode: "apply", changeName: "local-pilot", cwd: setup.root, io: captured.io, dependencies: applyDependencies(setup) });
  assert.equal(result.outcome, "success");
  assert.deepEqual(setup.calls, ["create", "validate-plan", "implementation", "capture-implementation", "validate-implementation", "apply-implementation", "cleanup"]);
  assert.match(captured.read().stdout, /Approved OpenSpec implementation complete/);
  assert.doesNotMatch(setup.calls.join(" "), /plan$/);
});

test("GitHub apply maps success to Done and structured blocker to Blocked", async () => {
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };

  const success = await commonHarness();
  const successTargets = [];
  const successResult = await runLocalWorkflow({
    mode: "apply", changeName: "local-pilot", cwd: success.root, io: memoryIo().io,
    dependencies: applyDependencies(success, {
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async ({ target }) => { successTargets.push(target); return { status: "Done" }; },
    }, source),
  });
  assert.equal(successResult.projectStatus, "Done");
  assert.deepEqual(successTargets, ["done"]);

  const blocked = await commonHarness();
  const blockedTargets = [];
  const blockedResult = await runLocalWorkflow({
    mode: "apply", changeName: "local-pilot", cwd: blocked.root, io: memoryIo().io,
    dependencies: applyDependencies(blocked, {
      runStage: async ({ phase }) => ({ version: 1, phase, outcome: "blocked", summary: "Need product decision", verification: [] }),
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async ({ target }) => { blockedTargets.push(target); return { status: "Blocked" }; },
    }, source),
  });
  assert.equal(blockedResult.outcome, "blocked");
  assert.deepEqual(blockedTargets, ["blocked"]);
  assert.ok(!blocked.calls.includes("apply-implementation"));
});

test("technical apply failures leave GitHub status unchanged", async () => {
  const setup = await commonHarness();
  let mutations = 0;
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  await assert.rejects(() => runLocalWorkflow({
    mode: "apply", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: applyDependencies(setup, {
      runStage: async ({ phase }) => ({ version: 1, phase, outcome: "failure", summary: "capacity", verification: [] }),
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async () => { mutations += 1; },
    }, source),
  }), (error) => error.code === "IMPLEMENTATION_FAILURE");
  assert.equal(mutations, 0);
});

test("failed terminal status update remains pending for no-model retry", async () => {
  const setup = await commonHarness();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  await assert.rejects(() => runLocalWorkflow({
    mode: "apply", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: applyDependencies(setup, {
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async () => { throw new LocalRunError("STATUS_SYNC_FAILED", "offline"); },
    }, source),
  }), (error) => error.code === "STATUS_SYNC_FAILED" && /--sync-status/.test(error.message));
  assert.equal(setup.records.at(-1).statusSync.state, "pending");
  assert.ok(setup.calls.includes("apply-implementation"));
});

test("status sync retry invokes neither Codex nor patch application", async () => {
  const setup = await commonHarness();
  const pending = { ...planRecord({ kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" }), mode: "apply", parentPlanRunId: "plan-run", statusSync: { state: "pending", target: "done", value: "Done" } };
  const targets = [];
  const result = await runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: {
      ...setup.lifecycle,
      preflightStatusSync: async () => ({ root: setup.root, pendingRecord: pending }),
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async ({ target }) => { targets.push(target); return { status: "Done" }; },
    },
  });
  assert.equal(result.projectStatus, "Done");
  assert.deepEqual(targets, ["done"]);
  assert.deepEqual(setup.calls, []);
});

test("Codex stage uses trusted prompt/schema and parses fake executable output", async () => {
  const root = await tempDirectory();
  const worktree = await tempDirectory();
  await mkdir(path.join(root, "automation", "ai-local", "prompts"), { recursive: true });
  await mkdir(path.join(root, "automation", "ai-local", "schemas"), { recursive: true });
  await writeFile(path.join(root, "automation", "ai-local", "prompts", "plan.md"), "Plan {{CHANGE_NAME}} from {{TASK_CONTEXT}}");
  await writeFile(path.join(root, "automation", "ai-local", "schemas", "plan-result.schema.json"), "{}");
  let invocation;
  const result = await runCodexStage({
    root, worktree, phase: "plan", changeName: "local-pilot",
    commandRunner: async (command, args, options) => {
      invocation = { command, args, options };
      const resultPath = args[args.indexOf("--output-last-message") + 1];
      await writeFile(resultPath, JSON.stringify({ version: 1, phase: "plan", outcome: "success", summary: "planned", verification: ["strict"] }));
      return { stdout: "", stderr: "" };
    },
  });
  assert.equal(result.outcome, "success");
  assert.equal(invocation.command, "codex");
  assert.equal(invocation.options.env.GITHUB_TOKEN, undefined);
  assert.equal(invocation.options.env.GH_TOKEN, undefined);
  assert.match(invocation.options.env.GH_CONFIG_DIR, /\.ai-local\/no-github-auth$/);
});
