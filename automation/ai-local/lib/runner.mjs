import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { copyApprovedPlan, hashApprovedPlan, listApprovedPlanPaths } from "./approved-plan.mjs";
import { LocalRunError, asLocalError, sanitizeText } from "./errors.mjs";
import { prepareProjectStatus, updateProjectStatus } from "./github-project.mjs";
import { formatApplySuccess, formatBlocked, formatPlanReady, formatStatusSync } from "./output.mjs";
import { preflight, preflightApply, preflightStatusSync } from "./preflight.mjs";
import { createRunId, initialLinkedRunRecord, initialRunRecord, updateRunRecord, writeRunRecord } from "./run-record.mjs";
import { runCodexStage } from "./codex.mjs";
import { taskLabel } from "./task.mjs";
import { cleanupIsolatedWorktree, createIsolatedWorktree } from "./worktree.mjs";
import { applyImplementationPatch, applyValidatedPatch, captureBinaryDiff, captureIndexDiff, validateImplementation, validatePlan } from "./validation.mjs";

async function writeTaskContext(worktree, task) {
  const directory = path.join(worktree, ".ai-local", "context");
  await mkdir(directory, { recursive: true, mode: 0o700 });
  await writeFile(path.join(directory, "task.md"), task.body, { mode: 0o600, flag: "wx" });
}

function sourceLabel(source) {
  return source.kind === "markdown" ? source.path : `${source.repository}#${source.issueNumber} (${source.url})`;
}

function statusValue(source, target) {
  return target === "done" ? source.doneStatus || "Done" : source.blockedStatus || "Blocked";
}

async function runPlanWorkflow(options) {
  const { cwd, taskPath, project, dryRun, io, signal, prompt, now, dependencies } = options;
  const preflightFn = dependencies.preflight || preflight;
  const createWorktreeFn = dependencies.createWorktree || createIsolatedWorktree;
  const cleanupWorktreeFn = dependencies.cleanupWorktree || cleanupIsolatedWorktree;
  const stageFn = dependencies.runStage || runCodexStage;
  const captureFn = dependencies.captureDiff || captureBinaryDiff;
  const validatePlanFn = dependencies.validatePlan || validatePlan;
  const hashPlanFn = dependencies.hashPlan || hashApprovedPlan;
  const applyPatchFn = dependencies.applyPatch || applyValidatedPatch;
  const recordWriter = dependencies.writeRecord || writeRunRecord;

  io.phase("preflight", "checking repository, task source, tools, and authentication");
  const context = await preflightFn({ cwd, taskPath, project, io, prompt, signal });
  const runId = createRunId(now(), context.task.hash);
  let record = initialRunRecord({ runId, mode: "plan", task: context.task, baseSha: context.baseSha, branch: context.branch, tools: context.tools, now: now() });
  let recordPath = await recordWriter(context.root, record);
  const label = taskLabel(context.task);
  io.info(`Task: ${label}`);
  io.info(`Change: ${context.task.changeName}`);
  io.info(`Base: ${context.baseSha}`);

  if (dryRun) {
    record = updateRunRecord(record, { phase: "dry-run", outcome: "success" }, now());
    recordPath = await recordWriter(context.root, record);
    io.info("Dry run complete. Planned stages: isolated planning -> strict plan validation -> unstaged plan application -> stop for human review.");
    io.info(`No Codex stage or temporary worktree was started. Run record: ${recordPath}`);
    return { outcome: "success", mode: "plan", dryRun: true, context, recordPath, paths: [] };
  }

  let ownedWorktree;
  try {
    record = updateRunRecord(record, { phase: "worktree" }, now());
    recordPath = await recordWriter(context.root, record);
    ownedWorktree = await createWorktreeFn({ repositoryRoot: context.root, baseSha: context.baseSha });
    await writeTaskContext(ownedWorktree.worktree, context.task);

    io.phase("planning", `creating ${context.task.changeName}`);
    record = updateRunRecord(record, { phase: "planning" }, now());
    recordPath = await recordWriter(context.root, record);
    const planResult = await stageFn({
      root: context.root,
      worktree: ownedWorktree.worktree,
      phase: "plan",
      changeName: context.task.changeName,
      signal,
      onStderr: (text) => io.info(sanitizeText(text).trimEnd()),
    });
    if (planResult.outcome !== "success") {
      const code = planResult.outcome === "clarification" ? "PLAN_CLARIFICATION" : "PLAN_FAILURE";
      throw new LocalRunError(code, planResult.summary);
    }
    const planDiff = await captureFn(ownedWorktree.worktree, context.baseSha);
    await validatePlanFn({ root: ownedWorktree.worktree, changeName: context.task.changeName, paths: planDiff.paths });
    const approvedPlan = await hashPlanFn(ownedWorktree.worktree, context.task.changeName);

    io.phase("plan-ready", "saving validated OpenSpec artifacts for human review");
    record = updateRunRecord(record, { phase: "plan-apply", approvedPlanHash: approvedPlan.hash }, now());
    recordPath = await recordWriter(context.root, record);
    await applyPatchFn({ root: context.root, baseSha: context.baseSha, patch: planDiff.patch });

    record = updateRunRecord(record, { phase: "complete", outcome: "success", changedPaths: planDiff.paths, approvedPlanHash: approvedPlan.hash }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(formatPlanReady({ changeName: context.task.changeName, sourceLabel: label, paths: planDiff.paths, recordPath }));
    return { outcome: "success", mode: "plan", dryRun: false, context, recordPath, paths: planDiff.paths };
  } catch (error) {
    const localError = asLocalError(error);
    record = updateRunRecord(record, { outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
    recordPath = await recordWriter(context.root, record).catch(() => recordPath);
    localError.message = `${localError.message} (run record: ${recordPath})`;
    throw localError;
  } finally {
    if (ownedWorktree) await cleanupWorktreeFn(ownedWorktree).catch((error) => io.error(`Cleanup warning: ${sanitizeText(error.message)}`));
  }
}

async function runApplyWorkflow(options) {
  const { cwd, changeName, dryRun, io, signal, now, dependencies } = options;
  const preflightFn = dependencies.preflightApply || preflightApply;
  const createWorktreeFn = dependencies.createWorktree || createIsolatedWorktree;
  const cleanupWorktreeFn = dependencies.cleanupWorktree || cleanupIsolatedWorktree;
  const stageFn = dependencies.runStage || runCodexStage;
  const copyPlanFn = dependencies.copyPlan || copyApprovedPlan;
  const planPathsFn = dependencies.planPaths || listApprovedPlanPaths;
  const validatePlanFn = dependencies.validatePlan || validatePlan;
  const hashPlanFn = dependencies.hashPlan || hashApprovedPlan;
  const captureFn = dependencies.captureImplementationDiff || captureIndexDiff;
  const validateImplementationFn = dependencies.validateImplementation || validateImplementation;
  const applyPatchFn = dependencies.applyImplementationPatch || applyImplementationPatch;
  const prepareStatusFn = dependencies.prepareStatus || prepareProjectStatus;
  const updateStatusFn = dependencies.updateStatus || updateProjectStatus;
  const recordWriter = dependencies.writeRecord || writeRunRecord;

  io.phase("apply-preflight", `validating approved plan ${changeName}`);
  const context = await preflightFn({ cwd, changeName });
  const label = sourceLabel(context.planRecord.source);
  const runId = createRunId(now(), context.planRecord.taskHash);
  let record = initialLinkedRunRecord({
    runId,
    mode: "apply",
    parent: context.planRecord,
    baseSha: context.baseSha,
    branch: context.branch,
    tools: context.tools,
    approvedPlanHash: context.approvedPlan.hash,
    now: now(),
  });
  let recordPath = await recordWriter(context.root, record);
  let preparedStatus = null;
  if (context.planRecord.source.kind === "github-issue") {
    try {
      preparedStatus = await prepareStatusFn({ root: context.root, source: context.planRecord.source, signal });
    } catch (error) {
      const localError = asLocalError(error);
      record = updateRunRecord(record, { outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
      recordPath = await recordWriter(context.root, record).catch(() => recordPath);
      localError.message = `${localError.message} (run record: ${recordPath})`;
      throw localError;
    }
  }

  if (dryRun) {
    record = updateRunRecord(record, { phase: "dry-run", outcome: "success" }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(`Apply dry run complete for ${changeName}. The approved plan is valid; Codex, patch application, and Project mutation did not run.`);
    return { outcome: "success", mode: "apply", dryRun: true, context, recordPath, paths: [] };
  }

  let ownedWorktree;
  const synchronize = async (target) => {
    if (!preparedStatus) return null;
    const value = statusValue(context.planRecord.source, target);
    record = updateRunRecord(record, { phase: "status-sync", statusSync: { state: "pending", target, value } }, now());
    recordPath = await recordWriter(context.root, record);
    try {
      const result = await updateStatusFn({ root: context.root, prepared: preparedStatus, target, signal });
      record = updateRunRecord(record, { statusSync: { state: "synchronized", target, value: result.status } }, now());
      recordPath = await recordWriter(context.root, record);
      return result.status;
    } catch (error) {
      const localError = asLocalError(error, "STATUS_SYNC_FAILED");
      throw new LocalRunError("STATUS_SYNC_FAILED", `${localError.message}. Retry with: npm run ai:local -- --sync-status ${changeName}`);
    }
  };

  try {
    record = updateRunRecord(record, { phase: "worktree" }, now());
    recordPath = await recordWriter(context.root, record);
    ownedWorktree = await createWorktreeFn({ repositoryRoot: context.root, baseSha: context.baseSha });
    if (context.planDirty) await copyPlanFn({ sourceRoot: context.root, worktree: ownedWorktree.worktree, changeName });
    const worktreePlanPaths = await planPathsFn(ownedWorktree.worktree, changeName);
    await validatePlanFn({ root: ownedWorktree.worktree, changeName, paths: worktreePlanPaths });
    const worktreePlan = await hashPlanFn(ownedWorktree.worktree, changeName);
    if (worktreePlan.hash !== context.approvedPlan.hash) throw new LocalRunError("PLAN_IDENTITY", "Isolated approved plan does not match the reviewed plan");

    io.phase("implementation", `applying approved change ${changeName}`);
    record = updateRunRecord(record, { phase: "implementation" }, now());
    recordPath = await recordWriter(context.root, record);
    const implementationResult = await stageFn({
      root: context.root,
      worktree: ownedWorktree.worktree,
      phase: "implementation",
      changeName,
      signal,
      onStderr: (text) => io.info(sanitizeText(text).trimEnd()),
    });
    if (implementationResult.outcome === "blocked") {
      const projectStatus = await synchronize("blocked");
      record = updateRunRecord(record, { phase: "complete", outcome: "blocked", error: implementationResult.summary }, now());
      recordPath = await recordWriter(context.root, record);
      io.info(formatBlocked({ changeName, sourceLabel: label, summary: implementationResult.summary, projectStatus, recordPath }));
      return { outcome: "blocked", mode: "apply", context, recordPath, paths: [] };
    }
    if (implementationResult.outcome !== "success") throw new LocalRunError("IMPLEMENTATION_FAILURE", implementationResult.summary);

    const delta = await captureFn(ownedWorktree.worktree);
    io.phase("validation", "checking approved contract, tasks, scope, and changed areas");
    record = updateRunRecord(record, { phase: "validation" }, now());
    recordPath = await recordWriter(context.root, record);
    const verification = await validateImplementationFn({
      root: ownedWorktree.worktree,
      dependencyRoot: context.root,
      changeName,
      paths: delta.paths,
      approvedPlanHash: context.approvedPlan.hash,
    });

    io.phase("apply", "applying the validated implementation as unstaged changes");
    record = updateRunRecord(record, { phase: "apply" }, now());
    recordPath = await recordWriter(context.root, record);
    await applyPatchFn({
      root: context.root,
      changeName,
      baseSha: context.baseSha,
      statusSnapshot: context.statusSnapshot,
      approvedPlanHash: context.approvedPlan.hash,
      patch: delta.patch,
    });
    record = updateRunRecord(record, { changedPaths: delta.paths, verification }, now());
    recordPath = await recordWriter(context.root, record);
    const projectStatus = await synchronize("done");

    record = updateRunRecord(record, { phase: "complete", outcome: "success", changedPaths: delta.paths, verification }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(formatApplySuccess({ changeName, sourceLabel: label, paths: delta.paths, verification, projectStatus, recordPath }));
    return { outcome: "success", mode: "apply", context, recordPath, paths: delta.paths, verification, projectStatus };
  } catch (error) {
    const localError = asLocalError(error);
    record = updateRunRecord(record, { outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
    recordPath = await recordWriter(context.root, record).catch(() => recordPath);
    localError.message = `${localError.message} (run record: ${recordPath})`;
    throw localError;
  } finally {
    if (ownedWorktree) await cleanupWorktreeFn(ownedWorktree).catch((error) => io.error(`Cleanup warning: ${sanitizeText(error.message)}`));
  }
}

async function runStatusSyncWorkflow(options) {
  const { cwd, changeName, io, signal, now, dependencies } = options;
  const preflightFn = dependencies.preflightStatusSync || preflightStatusSync;
  const prepareStatusFn = dependencies.prepareStatus || prepareProjectStatus;
  const updateStatusFn = dependencies.updateStatus || updateProjectStatus;
  const recordWriter = dependencies.writeRecord || writeRunRecord;
  io.phase("status-sync", `retrying recorded Project update for ${changeName}`);
  const context = await preflightFn({ cwd, changeName });
  const pending = context.pendingRecord;
  const runId = createRunId(now(), pending.taskHash);
  let record = initialLinkedRunRecord({ runId, mode: "sync-status", parent: pending, baseSha: pending.baseSha, branch: pending.branch, tools: pending.tools, approvedPlanHash: pending.approvedPlanHash, now: now() });
  let recordPath = await recordWriter(context.root, record);
  try {
    const prepared = await prepareStatusFn({ root: context.root, source: pending.source, target: pending.statusSync.target, signal });
    const result = await updateStatusFn({ root: context.root, prepared, target: pending.statusSync.target, signal });
    const completedPending = updateRunRecord(pending, { statusSync: { ...pending.statusSync, state: "synchronized", value: result.status } }, now());
    await recordWriter(context.root, completedPending);
    record = updateRunRecord(record, { phase: "complete", outcome: "success", statusSync: { state: "synchronized", target: pending.statusSync.target, value: result.status } }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(formatStatusSync({ changeName, status: result.status, recordPath }));
    return { outcome: "success", mode: "sync-status", recordPath, projectStatus: result.status };
  } catch (error) {
    const localError = asLocalError(error, "STATUS_SYNC_FAILED");
    record = updateRunRecord(record, { outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
    recordPath = await recordWriter(context.root, record).catch(() => recordPath);
    localError.message = `${localError.message} (run record: ${recordPath})`;
    throw localError;
  }
}

export async function runLocalWorkflow(options) {
  const normalized = {
    cwd: options.cwd || process.cwd(),
    taskPath: options.taskPath || null,
    project: options.project || null,
    changeName: options.changeName || null,
    mode: options.mode || "plan",
    dryRun: Boolean(options.dryRun),
    io: options.io,
    signal: options.signal,
    prompt: options.prompt,
    now: options.now || (() => new Date()),
    dependencies: options.dependencies || {},
  };
  if (normalized.mode === "apply") return runApplyWorkflow(normalized);
  if (normalized.mode === "sync-status") return runStatusSyncWorkflow(normalized);
  return runPlanWorkflow(normalized);
}
