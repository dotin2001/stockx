import { access, mkdtemp, realpath, rm } from "node:fs/promises";
import { constants } from "node:fs";
import os from "node:os";
import path from "node:path";

import { resolveApplyTestEnvironment } from "./apply-environment.mjs";
import { assertLocal, LocalRunError } from "./errors.mjs";
import { hashApprovedPlan, inspectApprovedPlanCheckout } from "./approved-plan.mjs";
import { loadGitHubProjectTask } from "./github-project.mjs";
import { runProcess } from "./process.mjs";
import { findPendingStatusRecord, findSuccessfulPlanRecord } from "./run-record.mjs";
import { resolveTaskFile } from "./task.mjs";
import { validatePlan } from "./validation.mjs";
import { findOwnedStaleWorktrees } from "./worktree.mjs";

function version(output) {
  return String(output).trim().split(/\r?\n/).at(-1)?.trim() || "unknown";
}

function nodeCompatible(nodeVersion) {
  const [major, minor] = nodeVersion.split(".").map(Number);
  return major > 18 || (major === 18 && minor >= 18);
}

export async function discoverRepository(cwd, commandRunner = runProcess) {
  const result = await commandRunner("git", ["rev-parse", "--show-toplevel"], { cwd });
  return realpath(result.stdout.trim());
}

export async function inspectRepository(root, commandRunner = runProcess) {
  let branchResult;
  try {
    branchResult = await commandRunner("git", ["symbolic-ref", "--quiet", "--short", "HEAD"], { cwd: root });
  } catch {
    throw new LocalRunError("BRANCH_DETACHED", "ai:local requires an attached Git branch; switch to a review branch first");
  }
  const status = await commandRunner("git", ["status", "--porcelain=v1", "--untracked-files=all"], { cwd: root });
  assertLocal(status.stdout.trim() === "", "WORKTREE_DIRTY", "Working tree must be clean; commit or move all tracked and untracked changes before running ai:local");
  const base = await commandRunner("git", ["rev-parse", "HEAD"], { cwd: root });
  const staged = await commandRunner("git", ["diff", "--cached", "--name-only"], { cwd: root });
  assertLocal(staged.stdout.trim() === "", "WORKTREE_STAGED", "Working tree must not contain staged changes");
  return { branch: branchResult.stdout.trim(), baseSha: base.stdout.trim() };
}

export async function inspectTools(root, commandRunner = runProcess, env = process.env) {
  assertLocal(nodeCompatible(process.versions.node), "NODE_VERSION", "Node 18.18.0 or newer is required");
  const [git, openspec, codex, execHelp] = await Promise.all([
    commandRunner("git", ["--version"], { cwd: root }),
    commandRunner("openspec", ["--version"], { cwd: root }),
    commandRunner("codex", ["--version"], { cwd: root }),
    commandRunner("codex", ["exec", "--help"], { cwd: root }),
  ]);
  const openspecVersion = version(openspec.stdout || openspec.stderr);
  assertLocal(/^1\.12(?:\.|$)/.test(openspecVersion), "OPENSPEC_VERSION", `OpenSpec 1.12.x is required; found ${openspecVersion}`);
  for (const flag of ["--ephemeral", "--sandbox", "--output-schema", "--output-last-message", "--ignore-user-config", "--model"]) {
    assertLocal(execHelp.stdout.includes(flag), "CODEX_FLAGS", `Installed Codex CLI does not support required flag ${flag}`);
  }
  let auth = "invocation-token";
  if (!env.CODEX_API_KEY && !env.CODEX_ACCESS_TOKEN) {
    const status = await commandRunner("codex", ["login", "status"], { cwd: root });
    assertLocal(/^\s*Logged in\b/im.test(`${status.stdout}\n${status.stderr}`), "CODEX_AUTH", "Codex CLI is not logged in; run `codex login` first");
    auth = "local-session";
  }
  return {
    node: process.versions.node,
    git: version(git.stdout || git.stderr),
    openspec: openspecVersion,
    codex: version(codex.stdout || codex.stderr),
    auth,
  };
}

export async function inspectTemporaryStorage() {
  await access(os.tmpdir(), constants.R_OK | constants.W_OK);
  const probe = await mkdtemp(path.join(os.tmpdir(), "ai-local-probe-"));
  await rm(probe, { recursive: true });
}

export async function assertNoChangeCollision(root, task) {
  const collision = path.join(root, "openspec", "changes", task.changeName);
  try {
    await access(collision);
    throw new LocalRunError("CHANGE_COLLISION", `OpenSpec change already exists: ${task.changeName}`);
  } catch (error) {
    if (error instanceof LocalRunError) throw error;
    if (error.code !== "ENOENT") throw error;
  }
}

async function inspectLocalState(root, commandRunner) {
  const repository = await inspectRepository(root, commandRunner);
  const stale = await findOwnedStaleWorktrees(root);
  assertLocal(stale.length === 0, "STALE_WORKTREE", `Found ${stale.length} stale ai-local worktree(s); follow the documented cleanup procedure`);
  await inspectTemporaryStorage();
  return repository;
}

export async function preflight({
  cwd = process.cwd(),
  taskPath,
  project = null,
  io,
  prompt,
  signal,
  commandRunner = runProcess,
  env = process.env,
  projectLoader = loadGitHubProjectTask,
}) {
  try {
    const root = await discoverRepository(cwd, commandRunner);
    let task;
    let repository;
    if (project) {
      repository = await inspectLocalState(root, commandRunner);
      io?.phase("inbox", `reading ${project.owner} Project ${project.number} (${project.statusField}=${project.statusValue})`);
      task = await projectLoader({ root, project, io, prompt, signal, commandRunner });
      await assertNoChangeCollision(root, task);
    } else {
      task = await resolveTaskFile(root, taskPath);
      await assertNoChangeCollision(root, task);
      repository = await inspectLocalState(root, commandRunner);
    }
    const tools = await inspectTools(root, commandRunner, env);
    return { root, task, ...repository, tools };
  } catch (error) {
    if (error instanceof LocalRunError) throw error;
    throw new LocalRunError("PREFLIGHT", `Local preflight failed: ${error?.message || error}`);
  }
}

export async function preflightApply({ cwd = process.cwd(), changeName, commandRunner = runProcess, env = process.env }) {
  try {
    const root = await discoverRepository(cwd, commandRunner);
    const applyTestEnvironment = resolveApplyTestEnvironment(env);
    const planRecord = await findSuccessfulPlanRecord(root, changeName);
    const repository = await inspectApprovedPlanCheckout(root, changeName, commandRunner);
    const stale = await findOwnedStaleWorktrees(root);
    assertLocal(stale.length === 0, "STALE_WORKTREE", `Found ${stale.length} stale ai-local worktree(s); follow the documented cleanup procedure`);
    await inspectTemporaryStorage();
    const approvedPlan = await hashApprovedPlan(root, changeName);
    await validatePlan({ root, changeName, paths: approvedPlan.paths, commandRunner });
    const tools = await inspectTools(root, commandRunner, env);
    return { root, planRecord, approvedPlan, applyTestEnvironment, ...repository, tools };
  } catch (error) {
    if (error instanceof LocalRunError) throw error;
    throw new LocalRunError("APPLY_PREFLIGHT", `Apply preflight failed: ${error?.message || error}`);
  }
}

export async function preflightStatusSync({ cwd = process.cwd(), changeName, commandRunner = runProcess }) {
  try {
    const root = await discoverRepository(cwd, commandRunner);
    const pendingRecord = await findPendingStatusRecord(root, changeName);
    return { root, pendingRecord };
  } catch (error) {
    if (error instanceof LocalRunError) throw error;
    throw new LocalRunError("STATUS_SYNC_PREFLIGHT", `Status-sync preflight failed: ${error?.message || error}`);
  }
}
