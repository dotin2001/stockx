import assert from "node:assert/strict";
import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { runCodexStage } from "../../automation/ai-local/lib/codex.mjs";
import { LocalRunError } from "../../automation/ai-local/lib/errors.mjs";
import { runLocalWorkflow } from "../../automation/ai-local/lib/runner.mjs";
import { writeRunRecord } from "../../automation/ai-local/lib/run-record.mjs";
import { initRepository, memoryIo, tempDirectory } from "./support/helpers.mjs";

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

test("apply passes the PostgreSQL test environment only to implementation and validation without persisting it", async () => {
  const setup = await commonHarness();
  const testUrl = "postgresql+psycopg://sentinel-user:sentinel-password@localhost:5432/stockx";
  const applyTestEnvironment = Object.freeze({ TEST_POSTGRES_DATABASE_URL: testUrl });
  const received = {};
  const baseDependencies = applyDependencies(setup);
  const dependencies = {
    ...baseDependencies,
    preflightApply: async () => ({
      root: setup.root,
      planRecord: planRecord(),
      approvedPlan: { hash: planHash, paths: planPaths },
      applyTestEnvironment,
      baseSha,
      branch: "main",
      tools: tools(),
      planDirty: false,
      statusSnapshot: "",
    }),
    runStage: async (options) => {
      setup.calls.push(options.phase);
      received.stage = options.applyTestEnvironment;
      return { version: 1, phase: options.phase, outcome: "success", summary: "implemented", verification: [] };
    },
    validateImplementation: async (options) => {
      setup.calls.push("validate-implementation");
      received.validation = options.applyTestEnvironment;
      return ["git diff --check"];
    },
  };

  await runLocalWorkflow({ mode: "apply", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io, dependencies });
  assert.equal(received.stage, applyTestEnvironment);
  assert.equal(received.validation, applyTestEnvironment);
  assert.doesNotMatch(JSON.stringify(setup.records), /sentinel-user|sentinel-password|TEST_POSTGRES_DATABASE_URL/);
});

test("apply dry run validates context without exposing the PostgreSQL test environment to a child", async () => {
  const setup = await commonHarness();
  const testUrl = "postgresql+psycopg://sentinel-user:sentinel-password@localhost:5432/stockx";
  const dependencies = applyDependencies(setup, {
    preflightApply: async () => ({
      root: setup.root,
      planRecord: planRecord(),
      approvedPlan: { hash: planHash, paths: planPaths },
      applyTestEnvironment: Object.freeze({ TEST_POSTGRES_DATABASE_URL: testUrl }),
      baseSha,
      branch: "main",
      tools: tools(),
      planDirty: false,
      statusSnapshot: "",
    }),
    runStage: async () => { throw new Error("dry run must not start Codex"); },
    validateImplementation: async () => { throw new Error("dry run must not start verification"); },
  });
  const result = await runLocalWorkflow({ mode: "apply", changeName: "local-pilot", cwd: setup.root, dryRun: true, io: memoryIo().io, dependencies });
  assert.equal(result.dryRun, true);
  assert.deepEqual(setup.calls, []);
  assert.doesNotMatch(JSON.stringify(setup.records), /sentinel-user|sentinel-password|TEST_POSTGRES_DATABASE_URL/);
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

test("status sync verifies a manual OpenSpec completion before persisting and applying Done", async () => {
  const setup = await commonHarness();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  const parent = planRecord(source);
  const implementationPaths = ["openspec/changes/local-pilot/tasks.md", "docs/pilot.md"];
  const order = [];
  const testUrl = "postgresql+psycopg://sentinel-user:sentinel-password@localhost:5432/stockx";
  const result = await runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: {
      ...setup.lifecycle,
      preflightStatusSync: async () => ({ root: setup.root, evidence: { kind: "plan", record: parent }, baseSha, branch: "main", applyTestEnvironment: { TEST_POSTGRES_DATABASE_URL: testUrl } }),
      inspectCompletion: async () => { order.push("inspect"); return { baseSha, branch: "main", paths: implementationPaths }; },
      validateImplementation: async (options) => {
        order.push("validate");
        assert.equal(options.requirePostgres, true);
        assert.equal(options.applyTestEnvironment.TEST_POSTGRES_DATABASE_URL, testUrl);
        return ["git diff --check"];
      },
      prepareStatus: async ({ source: preparedSource, target }) => {
        order.push("prepare");
        assert.equal(preparedSource.itemId, "PVTI_1");
        assert.equal(target, "done");
        return { prepared: true };
      },
      updateStatus: async ({ target }) => {
        order.push("update");
        assert.equal(target, "done");
        assert.deepEqual(setup.records.at(-1).statusSync, { state: "pending", target: "done", value: "Done" });
        return { status: "Done" };
      },
      runStage: async () => { throw new Error("status sync must not invoke Codex"); },
      applyImplementationPatch: async () => { throw new Error("status sync must not apply a patch"); },
    },
  });
  assert.equal(result.projectStatus, "Done");
  assert.equal(result.completionBasis, "verified-completion");
  assert.deepEqual(order, ["inspect", "validate", "prepare", "update"]);
  assert.deepEqual(result.paths, implementationPaths);
  assert.equal(setup.records.at(-1).statusSync.state, "synchronized");
  assert.equal(setup.records.at(-1).completionBasis, "verified-completion");
  assert.deepEqual(setup.records.at(-1).verification, ["git diff --check"]);
  assert.doesNotMatch(JSON.stringify(setup.records), /sentinel-user|sentinel-password|TEST_POSTGRES_DATABASE_URL/);
  assert.deepEqual(setup.calls, []);
});

test("verified status sync records technical verification failure without preparing GitHub", async () => {
  const setup = await commonHarness();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  let remoteCalls = 0;
  await assert.rejects(() => runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: {
      ...setup.lifecycle,
      preflightStatusSync: async () => ({ root: setup.root, evidence: { kind: "plan", record: planRecord(source) }, baseSha, branch: "main", applyTestEnvironment: {} }),
      inspectCompletion: async () => ({ baseSha, branch: "main", paths: ["openspec/changes/local-pilot/tasks.md", "docs/pilot.md"] }),
      validateImplementation: async () => { throw new LocalRunError("TASK_INCOMPLETE", "tasks remain"); },
      prepareStatus: async () => { remoteCalls += 1; },
      updateStatus: async () => { remoteCalls += 1; },
    },
  }), (error) => error.code === "TASK_INCOMPLETE");
  assert.equal(remoteCalls, 0);
  assert.equal(setup.records.at(-1).outcome, "failure");
  assert.equal(setup.records.at(-1).statusSync, null);
});

test("verified status sync leaves one pending Done transition when GitHub update fails", async () => {
  const setup = await commonHarness();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  await assert.rejects(() => runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: {
      ...setup.lifecycle,
      preflightStatusSync: async () => ({ root: setup.root, evidence: { kind: "plan", record: planRecord(source) }, baseSha, branch: "main", applyTestEnvironment: {} }),
      inspectCompletion: async () => ({ baseSha, branch: "main", paths: ["openspec/changes/local-pilot/tasks.md", "docs/pilot.md"] }),
      validateImplementation: async () => ["git diff --check"],
      prepareStatus: async () => ({ prepared: true }),
      updateStatus: async () => { throw new LocalRunError("STATUS_SYNC_FAILED", "offline"); },
    },
  }), (error) => error.code === "STATUS_SYNC_FAILED" && /--sync-status local-pilot/.test(error.message));
  const final = setup.records.at(-1);
  assert.equal(final.outcome, "failure");
  assert.deepEqual(final.statusSync, { state: "pending", target: "done", value: "Done" });
});

test("already synchronized status is idempotent and skips checkout verification and GitHub", async () => {
  const setup = await commonHarness();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  const synchronized = { ...planRecord(source), mode: "sync-status", parentPlanRunId: "plan-run", statusSync: { state: "synchronized", target: "done", value: "Done" } };
  const never = async () => { throw new Error("idempotent status sync must not perform expensive or remote work"); };
  const result = await runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: setup.root, io: memoryIo().io,
    dependencies: {
      ...setup.lifecycle,
      preflightStatusSync: async () => ({ root: setup.root, evidence: { kind: "synchronized", record: synchronized } }),
      inspectCompletion: never,
      validateImplementation: never,
      prepareStatus: never,
      updateStatus: never,
    },
  });
  assert.equal(result.projectStatus, "Done");
  assert.equal(result.completionBasis, "synchronized-result");
});

test("offline GitHub-plan fixture reaches Done after manual completion despite failed apply history", async () => {
  const root = await initRepository();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  const parent = planRecord(source);
  await writeRunRecord(root, parent);
  await writeRunRecord(root, { ...parent, runId: "failed-apply", mode: "apply", parentPlanRunId: parent.runId, phase: "validation", outcome: "failure", error: "technical failure" });
  const changeRoot = path.join(root, "openspec", "changes", "local-pilot");
  await mkdir(path.join(changeRoot, "specs", "pilot"), { recursive: true });
  await writeFile(path.join(changeRoot, ".openspec.yaml"), "schema: spec-driven\n");
  await writeFile(path.join(changeRoot, "proposal.md"), "# Proposal\n");
  await writeFile(path.join(changeRoot, "design.md"), "# Design\n");
  await writeFile(path.join(changeRoot, "tasks.md"), "- [x] implement\n");
  await writeFile(path.join(changeRoot, "specs", "pilot", "spec.md"), "## Purpose\nPilot.\n");
  await mkdir(path.join(root, "docs"));
  await writeFile(path.join(root, "docs", "pilot.md"), "implemented\n");

  const order = [];
  const result = await runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: root, io: memoryIo().io,
    dependencies: {
      validateImplementation: async ({ paths }) => {
        order.push("validate");
        assert.ok(paths.includes("openspec/changes/local-pilot/tasks.md"));
        assert.ok(paths.includes("docs/pilot.md"));
        return ["git diff --check"];
      },
      prepareStatus: async ({ source: recorded, target }) => {
        order.push("prepare");
        assert.equal(recorded.itemId, source.itemId);
        assert.equal(target, "done");
        return { prepared: true };
      },
      updateStatus: async () => { order.push("update"); return { status: "Done" }; },
    },
  });
  assert.equal(result.projectStatus, "Done");
  assert.equal(result.completionBasis, "verified-completion");
  assert.deepEqual(order, ["validate", "prepare", "update"]);
});

test("ambiguous status evidence records a technical refusal and never calls GitHub", async () => {
  const root = await initRepository();
  const source = { kind: "github-issue", projectOwner: "acme", projectNumber: 7, repository: "acme/shop", issueNumber: 12, url: "https://github.com/acme/shop/issues/12", itemId: "PVTI_1", statusField: "Status", statusValue: "Todo", doneStatus: "Done", blockedStatus: "Blocked" };
  const pending = { ...planRecord(source), runId: "pending-one", mode: "apply", parentPlanRunId: "plan-run", statusSync: { state: "pending", target: "done", value: "Done" } };
  await writeRunRecord(root, pending);
  await writeRunRecord(root, { ...pending, runId: "pending-two" });
  let remoteCalls = 0;
  await assert.rejects(() => runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: root, io: memoryIo().io,
    dependencies: {
      prepareStatus: async () => { remoteCalls += 1; },
      updateStatus: async () => { remoteCalls += 1; },
    },
  }), (error) => error.code === "STATUS_SYNC_AMBIGUOUS" && /run record/.test(error.message));
  assert.equal(remoteCalls, 0);
  const directory = path.join(root, ".ai-local", "runs");
  const records = await Promise.all((await readdir(directory)).map(async (name) => JSON.parse(await readFile(path.join(directory, name), "utf8"))));
  const refusal = records.find((record) => record.mode === "sync-status");
  assert.equal(refusal.outcome, "failure");
  assert.equal(refusal.completionBasis, "refused-evidence");
  assert.equal(refusal.statusSync, null);

  const markdownRoot = await initRepository();
  const markdown = planRecord({ kind: "markdown", path: "tasks/pilot.md" });
  await writeRunRecord(markdownRoot, markdown);
  await assert.rejects(() => runLocalWorkflow({
    mode: "sync-status", changeName: "local-pilot", cwd: markdownRoot, io: memoryIo().io,
    dependencies: {
      prepareStatus: async () => { remoteCalls += 1; },
      updateStatus: async () => { remoteCalls += 1; },
    },
  }), (error) => error.code === "STATUS_SYNC_SOURCE" && /run record/.test(error.message));
  assert.equal(remoteCalls, 0);
  const markdownRecords = await Promise.all((await readdir(path.join(markdownRoot, ".ai-local", "runs"))).map(async (name) => JSON.parse(await readFile(path.join(markdownRoot, ".ai-local", "runs", name), "utf8"))));
  assert.equal(markdownRecords.find((record) => record.mode === "sync-status").outcome, "failure");
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

test("Codex exposes and redacts the test database URL only during implementation", async () => {
  const root = await tempDirectory();
  const worktree = await tempDirectory();
  const testUrl = "postgresql+psycopg://sentinel-user:sentinel-password@localhost:5432/stockx";
  const applyTestEnvironment = Object.freeze({ TEST_POSTGRES_DATABASE_URL: testUrl });
  await mkdir(path.join(root, "automation", "ai-local", "prompts"), { recursive: true });
  await mkdir(path.join(root, "automation", "ai-local", "schemas"), { recursive: true });
  for (const phase of ["plan", "implementation"]) {
    await writeFile(path.join(root, "automation", "ai-local", "prompts", `${phase}.md`), `${phase} {{CHANGE_NAME}}`);
    await writeFile(path.join(root, "automation", "ai-local", "schemas", `${phase}-result.schema.json`), "{}");
  }

  const environments = {};
  let streamed = "";
  const run = (phase) => runCodexStage({
    root,
    worktree,
    phase,
    changeName: "local-pilot",
    applyTestEnvironment,
    onStderr: (text) => { streamed += text; },
    commandRunner: async (_command, args, options) => {
      environments[phase] = options.env;
      options.onStderr?.(`child echoed ${options.env.TEST_POSTGRES_DATABASE_URL || "no test URL"}`);
      const resultPath = args[args.indexOf("--output-last-message") + 1];
      await writeFile(resultPath, JSON.stringify({
        version: 1,
        phase,
        outcome: "success",
        summary: phase === "implementation" ? `completed ${testUrl}` : "completed plan",
        verification: [phase === "implementation" ? `checked ${testUrl}` : "checked plan"],
      }));
      return { stdout: "", stderr: "" };
    },
  });

  const planResult = await run("plan");
  const implementationResult = await run("implementation");
  assert.equal(environments.plan.TEST_POSTGRES_DATABASE_URL, undefined);
  assert.equal(environments.implementation.TEST_POSTGRES_DATABASE_URL, testUrl);
  assert.equal(planResult.summary, "completed plan");
  assert.match(implementationResult.summary, /\[REDACTED\]/);
  assert.match(implementationResult.verification[0], /\[REDACTED\]/);
  assert.doesNotMatch(streamed, /sentinel-user|sentinel-password/);
});
