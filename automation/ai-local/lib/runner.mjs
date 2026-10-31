import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { copyApprovedPlan, hashApprovedPlan, listApprovedPlanPaths } from "./approved-plan.mjs";
import { LocalRunError, asLocalError, sanitizeText } from "./errors.mjs";
import { prepareProjectStatus, refreshRecordedIssue, restorePreparedProjectStatus, serializePreparedProjectStatus, updateProjectStatus } from "./github-project.mjs";
import { formatApplySuccess, formatBlocked, formatPlanReady, formatStatusSync } from "./output.mjs";
import { preflight, preflightApply, preflightStatusSync } from "./preflight.mjs";
import {
  assertReviewSnapshotUnchanged,
  blockedReviewReport,
  cleanupReviewContext,
  collectRequiredReviewInventory,
  collectReviewChecks,
  collectReviewSnapshot,
  createReviewContext,
  deriveReviewTarget,
  sanitizeReviewReport,
  validateReviewReport,
} from "./review.mjs";
import { createRunId, initialLinkedRunRecord, initialRunRecord, updateRunRecord, writeRunRecord } from "./run-record.mjs";
import { runCodexStage } from "./codex.mjs";
import { createGitHubIssueTask, taskLabel } from "./task.mjs";
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
  if (target === "done") return source.doneStatus || "Done";
  if (target === "review") return source.reviewStatus || "Review";
  return source.blockedStatus || "Blocked";
}

function pendingStatus(source, target, prepared) {
  const status = { state: "pending", target, value: statusValue(source, target) };
  const intent = serializePreparedProjectStatus(prepared, target);
  return intent ? { ...status, prepared: intent } : status;
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
    record = updateRunRecord(record, { phase: "status-sync", statusSync: pendingStatus(context.planRecord.source, target, preparedStatus) }, now());
    recordPath = await recordWriter(context.root, record);
    try {
      const result = await updateStatusFn({ root: context.root, prepared: preparedStatus, target, signal });
      record = updateRunRecord(record, { statusSync: { ...record.statusSync, state: "synchronized", value: result.status } }, now());
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
      applyTestEnvironment: context.applyTestEnvironment,
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
      applyTestEnvironment: context.applyTestEnvironment,
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
  const collectSnapshotFn = dependencies.collectReviewSnapshot || collectReviewSnapshot;
  const collectChecksFn = dependencies.collectReviewChecks || collectReviewChecks;
  const collectInventoryFn = dependencies.collectReviewInventory || collectRequiredReviewInventory;
  const createReviewContextFn = dependencies.createReviewContext || createReviewContext;
  const cleanupReviewContextFn = dependencies.cleanupReviewContext || cleanupReviewContext;
  const reviewStageFn = dependencies.runReview || dependencies.runStage || runCodexStage;
  const validateReviewFn = dependencies.validateReviewReport || validateReviewReport;
  const assertSnapshotFn = dependencies.assertReviewSnapshot || assertReviewSnapshotUnchanged;
  const refreshIssueFn = dependencies.refreshIssue || refreshRecordedIssue;
  const prepareStatusFn = dependencies.prepareStatus || prepareProjectStatus;
  const updateStatusFn = dependencies.updateStatus || updateProjectStatus;
  const recordWriter = dependencies.writeRecord || writeRunRecord;
  io.phase("status-sync", `resolving retry or verified completion for ${changeName}`);
  const context = await preflightFn({ cwd, changeName, signal });
  const evidence = context.evidence || (context.pendingRecord ? { kind: "pending", record: context.pendingRecord } : context.diagnosticRecord ? { kind: "refusal", record: context.diagnosticRecord } : null);
  if (!evidence?.record) throw new LocalRunError("STATUS_SYNC_EVIDENCE", "Status-sync preflight returned no usable evidence");
  const parent = evidence.record;
  const completionBasis = evidence.kind === "plan" ? "reviewed-current-state" : evidence.kind === "pending" ? "pending-retry" : evidence.kind === "synchronized" ? "synchronized-result" : "refused-evidence";
  const runId = createRunId(now(), parent.taskHash);
  let record = initialLinkedRunRecord({
    runId,
    mode: "sync-status",
    parent,
    baseSha: context.baseSha || parent.baseSha,
    branch: context.branch || parent.branch,
    tools: parent.tools,
    approvedPlanHash: parent.approvedPlanHash,
    completionBasis,
    now: now(),
  });
  let recordPath = await recordWriter(context.root, record);
  try {
    if (context.refusal) throw context.refusal;
    if (evidence.kind === "synchronized") {
      record = updateRunRecord(record, {
        phase: "complete",
        outcome: "success",
        changedPaths: parent.changedPaths || [],
        verification: parent.verification || [],
        reviewReport: parent.reviewReport || null,
        derivedTarget: parent.derivedTarget || parent.statusSync.target,
        effectiveTarget: parent.effectiveTarget || parent.statusSync.target,
        fallbackReason: parent.fallbackReason || null,
        statusSync: { ...parent.statusSync },
      }, now());
      recordPath = await recordWriter(context.root, record);
      io.info(formatStatusSync({
        changeName,
        status: parent.statusSync.value,
        recordPath,
        completionBasis,
        verification: parent.verification || [],
        report: parent.reviewReport || null,
        derivedTarget: parent.derivedTarget || null,
        effectiveTarget: parent.effectiveTarget || null,
        fallbackReason: parent.fallbackReason || null,
      }));
      return { outcome: "success", mode: "sync-status", recordPath, projectStatus: parent.statusSync.value, completionBasis };
    }

    if (evidence.kind === "pending") {
      const prepared = parent.statusSync.prepared
        ? restorePreparedProjectStatus(parent.source, parent.statusSync.target, parent.statusSync.prepared)
        : await prepareStatusFn({ root: context.root, source: parent.source, target: parent.statusSync.target, allowReviewStates: true, allowBlockedCurrent: true, signal });
      const result = await updateStatusFn({ root: context.root, prepared, target: parent.statusSync.target, signal });
      const completedPending = updateRunRecord(parent, { statusSync: { ...parent.statusSync, state: "synchronized", value: result.status } }, now());
      await recordWriter(context.root, completedPending);
      record = updateRunRecord(record, {
        phase: "complete",
        outcome: "success",
        changedPaths: parent.changedPaths || [],
        verification: parent.verification || [],
        reviewReport: parent.reviewReport || null,
        derivedTarget: parent.derivedTarget || parent.statusSync.target,
        effectiveTarget: parent.effectiveTarget || parent.statusSync.target,
        fallbackReason: parent.fallbackReason || null,
        statusSync: { ...parent.statusSync, state: "synchronized", value: result.status },
      }, now());
      recordPath = await recordWriter(context.root, record);
      io.info(formatStatusSync({
        changeName,
        status: result.status,
        recordPath,
        completionBasis,
        verification: parent.verification || [],
        report: parent.reviewReport || null,
        derivedTarget: parent.derivedTarget || parent.statusSync.target,
        effectiveTarget: parent.effectiveTarget || parent.statusSync.target,
        fallbackReason: parent.fallbackReason || null,
      }));
      return { outcome: "success", mode: "sync-status", recordPath, projectStatus: result.status, completionBasis };
    }

    if (evidence.kind !== "plan") throw new LocalRunError("STATUS_SYNC_EVIDENCE", "Status-sync evidence kind is unsupported");
    io.phase("review-snapshot", "capturing committed and uncommitted changes from the recorded base");
    record = updateRunRecord(record, { phase: "review-snapshot" }, now());
    recordPath = await recordWriter(context.root, record);
    const snapshotOptions = {
      root: context.root,
      baseSha: parent.baseSha,
      branch: parent.branch,
      changeName,
      approvedPlanHash: parent.approvedPlanHash,
      issueTaskHash: context.issueTask.hash,
    };
    const snapshot = await collectSnapshotFn(snapshotOptions);

    io.phase("verification", "running strict OpenSpec and trusted path-selected checks");
    record = updateRunRecord(record, { phase: "verification", changedPaths: snapshot.paths }, now());
    recordPath = await recordWriter(context.root, record);
    const checks = await collectChecksFn({
      root: context.root,
      dependencyRoot: context.root,
      changeName,
      paths: snapshot.paths,
      baseSha: parent.baseSha,
      applyTestEnvironment: context.applyTestEnvironment,
      applyTestEnvironmentError: context.applyTestEnvironmentError,
    });
    const inventory = await collectInventoryFn({ root: context.root, changeName, checks });
    const verification = checks.map((check) => `${check.label}: ${check.result}`);

    io.phase("review", "evaluating issue acceptance criteria and approved OpenSpec requirements");
    record = updateRunRecord(record, { phase: "review", verification }, now());
    recordPath = await recordWriter(context.root, record);
    let reviewContext;
    let report;
    try {
      reviewContext = await createReviewContextFn({
        root: context.root,
        runId,
        issueTaskBody: context.issueTask.body,
        checks,
        baseSha: parent.baseSha,
        changeName,
      });
      try {
        const candidate = await reviewStageFn({
          root: context.root,
          worktree: context.root,
          phase: "review",
          changeName,
          reviewContext,
          reviewInventory: inventory,
          baseSha: parent.baseSha,
          signal,
        });
        report = validateReviewFn(candidate, inventory);
      } catch (error) {
        const localError = asLocalError(error);
        report = validateReviewFn(blockedReviewReport(`${localError.code}: semantic review could not complete`, inventory), inventory);
      }
      report = sanitizeReviewReport(report);
      await assertSnapshotFn(snapshot, snapshotOptions);
      const currentIssue = await refreshIssueFn({ root: context.root, source: parent.source, signal });
      const currentTask = createGitHubIssueTask(currentIssue);
      if (currentTask.hash !== parent.taskHash || currentTask.changeName !== changeName) {
        throw new LocalRunError("TASK_IDENTITY", "Linked GitHub issue changed during review");
      }
    } finally {
      if (reviewContext) await cleanupReviewContextFn(reviewContext).catch((error) => io.error(`Cleanup warning: ${sanitizeText(error.message)}`));
    }

    const derivedTarget = deriveReviewTarget(report);
    const prepared = await prepareStatusFn({
      root: context.root,
      source: parent.source,
      target: derivedTarget,
      allowReviewFallback: derivedTarget === "blocked",
      allowReviewStates: true,
      allowBlockedCurrent: derivedTarget === "blocked" || Boolean(evidence.allowBlockedCurrent),
      signal,
    });
    const effectiveTarget = prepared.effectiveTarget || derivedTarget;
    const fallbackReason = prepared.fallbackReason ? sanitizeText(prepared.fallbackReason) : null;
    const pending = pendingStatus(parent.source, effectiveTarget, prepared);
    record = updateRunRecord(record, {
      phase: "status-sync",
      changedPaths: snapshot.paths,
      verification,
      reviewReport: report,
      derivedTarget,
      effectiveTarget,
      fallbackReason,
      statusSync: pending,
    }, now());
    recordPath = await recordWriter(context.root, record);
    const result = await updateStatusFn({ root: context.root, prepared, target: effectiveTarget, signal });
    record = updateRunRecord(record, { phase: "complete", outcome: "success", statusSync: { ...pending, state: "synchronized", value: result.status } }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(formatStatusSync({ changeName, status: result.status, recordPath, completionBasis, verification, report, derivedTarget, effectiveTarget, fallbackReason }));
    return {
      outcome: "success",
      mode: "sync-status",
      recordPath,
      paths: snapshot.paths,
      verification,
      report,
      derivedTarget,
      effectiveTarget,
      fallbackReason,
      projectStatus: result.status,
      completionBasis,
    };
  } catch (error) {
    const localError = asLocalError(error, "STATUS_SYNC_FAILED");
    record = updateRunRecord(record, { outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
    recordPath = await recordWriter(context.root, record).catch(() => recordPath);
    const retry = record.statusSync?.state === "pending" ? ` Retry with: npm run ai:local -- --sync-status ${changeName}.` : "";
    localError.message = `${localError.message.replace(/[.\s]+$/, "")}.${retry} (run record: ${recordPath})`;
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
