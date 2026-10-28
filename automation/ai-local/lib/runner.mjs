import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { LocalRunError, asLocalError, sanitizeText } from "./errors.mjs";
import { formatSuccess } from "./output.mjs";
import { preflight } from "./preflight.mjs";
import { createRunId, initialRunRecord, updateRunRecord, writeRunRecord } from "./run-record.mjs";
import { runCodexStage } from "./codex.mjs";
import { cleanupIsolatedWorktree, createIsolatedWorktree } from "./worktree.mjs";
import { applyValidatedPatch, captureBinaryDiff, validateImplementation, validatePlan } from "./validation.mjs";

async function writeTaskContext(worktree, task) {
  const directory = path.join(worktree, ".ai-local", "context");
  await mkdir(directory, { recursive: true, mode: 0o700 });
  await writeFile(path.join(directory, "task.md"), task.body, { mode: 0o600, flag: "wx" });
}

export async function runLocalWorkflow(options) {
  const {
    cwd = process.cwd(),
    taskPath,
    dryRun = false,
    io,
    signal,
    now = () => new Date(),
    dependencies = {},
  } = options;
  const preflightFn = dependencies.preflight || preflight;
  const createWorktreeFn = dependencies.createWorktree || createIsolatedWorktree;
  const cleanupWorktreeFn = dependencies.cleanupWorktree || cleanupIsolatedWorktree;
  const stageFn = dependencies.runStage || runCodexStage;
  const captureFn = dependencies.captureDiff || captureBinaryDiff;
  const validatePlanFn = dependencies.validatePlan || validatePlan;
  const validateImplementationFn = dependencies.validateImplementation || validateImplementation;
  const applyPatchFn = dependencies.applyPatch || applyValidatedPatch;
  const recordWriter = dependencies.writeRecord || writeRunRecord;

  io.phase("preflight", "checking repository, task, tools, and authentication");
  const context = await preflightFn({ cwd, taskPath });
  const runId = createRunId(now(), context.task.hash);
  let record = initialRunRecord({ runId, task: context.task, baseSha: context.baseSha, branch: context.branch, tools: context.tools, now: now() });
  let recordPath = await recordWriter(context.root, record);
  io.info(`Task: ${context.task.relativePath}`);
  io.info(`Change: ${context.task.changeName}`);
  io.info(`Base: ${context.baseSha}`);
  io.info(`Tools: Node ${context.tools.node}; ${context.tools.openspec}; ${context.tools.codex}`);

  if (dryRun) {
    record = updateRunRecord(record, { phase: "dry-run", outcome: "success" }, now());
    recordPath = await recordWriter(context.root, record);
    io.info("Dry run complete. Planned stages: isolated planning -> strict plan validation -> isolated implementation -> verification -> unstaged patch application.");
    io.info(`No Codex stage or temporary worktree was started. Run record: ${recordPath}`);
    return { outcome: "success", dryRun: true, context, recordPath, paths: [], verification: [] };
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

    io.phase("implementation", "applying the validated OpenSpec plan");
    record = updateRunRecord(record, { phase: "implementation" }, now());
    recordPath = await recordWriter(context.root, record);
    const implementationResult = await stageFn({
      root: context.root,
      worktree: ownedWorktree.worktree,
      phase: "implementation",
      changeName: context.task.changeName,
      signal,
      onStderr: (text) => io.info(sanitizeText(text).trimEnd()),
    });
    if (implementationResult.outcome !== "success") throw new LocalRunError("IMPLEMENTATION_FAILURE", implementationResult.summary);
    const combined = await captureFn(ownedWorktree.worktree, context.baseSha);

    io.phase("validation", "checking scope, tasks, OpenSpec, and changed areas");
    record = updateRunRecord(record, { phase: "validation" }, now());
    recordPath = await recordWriter(context.root, record);
    const verification = await validateImplementationFn({
      root: ownedWorktree.worktree,
      dependencyRoot: context.root,
      changeName: context.task.changeName,
      paths: combined.paths,
      baseSha: context.baseSha,
      taskHash: context.task.hash,
    });

    io.phase("apply", "applying the validated patch as unstaged local changes");
    record = updateRunRecord(record, { phase: "apply" }, now());
    recordPath = await recordWriter(context.root, record);
    await applyPatchFn({ root: context.root, baseSha: context.baseSha, patch: combined.patch });

    record = updateRunRecord(record, {
      phase: "complete",
      outcome: "success",
      changedPaths: combined.paths,
      verification,
    }, now());
    recordPath = await recordWriter(context.root, record);
    io.info(formatSuccess({ changeName: context.task.changeName, paths: combined.paths, verification, recordPath }));
    return { outcome: "success", dryRun: false, context, recordPath, paths: combined.paths, verification };
  } catch (error) {
    const localError = asLocalError(error);
    record = updateRunRecord(record, { phase: record.phase, outcome: "failure", error: `${localError.code}: ${localError.message}` }, now());
    recordPath = await recordWriter(context.root, record).catch(() => recordPath);
    localError.message = `${localError.message} (run record: ${recordPath})`;
    throw localError;
  } finally {
    if (ownedWorktree) await cleanupWorktreeFn(ownedWorktree).catch((error) => io.error(`Cleanup warning: ${sanitizeText(error.message)}`));
  }
}
