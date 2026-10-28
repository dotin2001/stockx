import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";
import path from "node:path";

import { assertLocal, LocalRunError } from "./errors.mjs";
import { runProcess, sanitizedChildEnvironment } from "./process.mjs";

const PROTECTED_PATHS = [
  ".git/",
  ".github/workflows/",
  ".github/codex/",
  ".agents/skills/",
  ".codex/",
  "AGENTS.md",
  "openspec/config.yaml",
  "openspec/config.yml",
  "bin/ai-local.mjs",
  "automation/ai-local/",
];

function splitNul(value) {
  return value.split("\0").filter(Boolean);
}

export function assertSafeRelativePath(filePath) {
  assertLocal(typeof filePath === "string" && filePath.length > 0 && filePath.length <= 4096, "PATCH_PATH", "Changed path is invalid");
  assertLocal(!filePath.includes("\0") && !filePath.includes("\\") && !path.posix.isAbsolute(filePath), "PATCH_PATH", "Changed path is unsafe");
  const normalized = path.posix.normalize(filePath);
  assertLocal(normalized === filePath && normalized !== ".." && !normalized.startsWith("../"), "PATCH_PATH", "Changed path escapes the repository");
  assertLocal(!normalized.split("/").includes(".git"), "PATCH_PATH", "Changes may not modify Git internals");
  return normalized;
}

export async function captureBinaryDiff(root, baseSha, commandRunner = runProcess) {
  const untracked = await commandRunner("git", ["ls-files", "--others", "--exclude-standard", "-z"], { cwd: root });
  const untrackedPaths = splitNul(untracked.stdout).map(assertSafeRelativePath);
  if (untrackedPaths.length) await commandRunner("git", ["add", "-N", "--", ...untrackedPaths], { cwd: root });
  const [diff, names] = await Promise.all([
    commandRunner("git", ["diff", "--binary", "--no-ext-diff", baseSha, "--"], { cwd: root }),
    commandRunner("git", ["diff", "--name-only", "-z", baseSha, "--"], { cwd: root }),
  ]);
  const paths = splitNul(names.stdout).map(assertSafeRelativePath);
  assertLocal(diff.stdout.length > 0 && paths.length > 0, "PATCH_EMPTY", "Agent produced no Git-visible changes");
  assertLocal(new Set(paths).size === paths.length, "PATCH_PATH", "Changed path list contains duplicates");
  return { patch: diff.stdout, paths };
}

export function assertPlanPaths(paths, changeName) {
  const prefix = `openspec/changes/${changeName}/`;
  assertLocal(paths.every((filePath) => filePath.startsWith(prefix)), "PLAN_SCOPE", "Planning changed a path outside its deterministic OpenSpec change directory");
  for (const required of [".openspec.yaml", "proposal.md", "tasks.md"]) {
    assertLocal(paths.includes(`${prefix}${required}`), "PLAN_ARTIFACT", `Planning is missing ${required}`);
  }
  return paths;
}

export function assertImplementationPaths(paths, changeName) {
  const prefix = `openspec/changes/${changeName}/`;
  assertLocal(paths.some((filePath) => filePath.startsWith(prefix)), "IMPLEMENTATION_SCOPE", "Combined changes do not include the accepted OpenSpec plan");
  for (const filePath of paths) {
    const protectedPath = PROTECTED_PATHS.find((candidate) => candidate.endsWith("/") ? filePath.startsWith(candidate) : filePath === candidate);
    assertLocal(!protectedPath, "IMPLEMENTATION_AUTHORITY", `Implementation attempted to modify protected authority path: ${filePath}`);
  }
  assertLocal(paths.some((filePath) => !filePath.startsWith(prefix)), "IMPLEMENTATION_EMPTY", "Implementation contains planning artifacts only");
  return paths;
}

export function assertTaskMarkersComplete(tasksText) {
  const markers = [...String(tasksText).matchAll(/^\s*- \[([ xX])\]\s+.+$/gm)];
  assertLocal(markers.length > 0, "TASK_MARKERS", "OpenSpec tasks file has no task markers");
  assertLocal(markers.every((marker) => marker[1].toLowerCase() === "x"), "TASK_INCOMPLETE", "OpenSpec implementation tasks are not all complete");
  return markers.length;
}

async function requiredFile(root, relativePath) {
  try {
    await access(path.join(root, relativePath), constants.R_OK);
  } catch {
    throw new LocalRunError("PLAN_ARTIFACT", `Required planning artifact is missing: ${relativePath}`);
  }
}

export async function validatePlan({ root, changeName, paths, commandRunner = runProcess }) {
  assertPlanPaths(paths, changeName);
  const prefix = `openspec/changes/${changeName}`;
  await Promise.all([
    requiredFile(root, `${prefix}/.openspec.yaml`),
    requiredFile(root, `${prefix}/proposal.md`),
    requiredFile(root, `${prefix}/tasks.md`),
  ]);
  const status = await commandRunner("openspec", ["status", "--change", changeName, "--json"], { cwd: root });
  let parsed;
  try { parsed = JSON.parse(status.stdout); } catch { throw new LocalRunError("PLAN_STATUS", "OpenSpec status did not return valid JSON"); }
  const artifacts = Array.isArray(parsed.artifacts) ? parsed.artifacts : [];
  const applyRequires = Array.isArray(parsed.applyRequires) ? parsed.applyRequires : [];
  const requiredForApplyComplete = applyRequires.length > 0 && applyRequires.every((artifactId) =>
    artifacts.some((artifact) => artifact?.id === artifactId && ["done", "skipped"].includes(artifact.status)),
  );
  assertLocal(parsed.isPlanningComplete === true || parsed.isComplete === true || requiredForApplyComplete, "PLAN_INCOMPLETE", "OpenSpec planning artifacts required for apply are incomplete");

  const specsSkipped = artifacts.some((artifact) => artifact?.id === "specs" && artifact.status === "skipped");
  const hasCapabilitySpec = paths.some((filePath) => filePath.startsWith(`${prefix}/specs/`) && filePath.endsWith("/spec.md"));
  assertLocal(specsSkipped || hasCapabilitySpec, "PLAN_ARTIFACT", "Planning has no capability specification and OpenSpec did not mark specs as skipped");
  await commandRunner("openspec", ["validate", changeName, "--strict"], { cwd: root });
}

export function verificationCommandsForPaths(paths) {
  const commands = [{ name: "git diff --check", command: "git", args: ["diff", "--check", "HEAD", "--"] }];
  const nonPlan = paths.filter((filePath) => !filePath.startsWith("openspec/changes/"));
  const known = nonPlan.every((filePath) => [
    "apps/", "automation/", "bin/", "css/", "docs/", "infra/", "js/", "packages/", "tests/",
  ].some((prefix) => filePath.startsWith(prefix)) || /^(?:README|LICENSE|CONTRIBUTING)(?:\.|$)/i.test(filePath) || ["package.json", "package-lock.json", "project.md"].includes(filePath));
  assertLocal(known, "VERIFICATION_POLICY", "No trusted verification policy matches one or more implementation paths");
  if (nonPlan.some((filePath) => filePath.startsWith("apps/web/"))) {
    commands.push(
      { name: "npm run web:lint", command: "npm", args: ["run", "web:lint"] },
      { name: "npm run web:typecheck", command: "npm", args: ["run", "web:typecheck"] },
      { name: "npm run web:build", command: "npm", args: ["run", "web:build"] },
    );
  }
  if (nonPlan.some((filePath) => filePath.startsWith("apps/api/") || filePath.startsWith("infra/"))) {
    commands.push({ name: "python -m pytest", command: "python", args: ["-m", "pytest"], cwd: "apps/api" });
  }
  if (nonPlan.some((filePath) => filePath.startsWith("automation/") || filePath.startsWith("bin/") || filePath.startsWith("tests/") || filePath === "package.json" || filePath === "package-lock.json")) {
    commands.push({ name: "npm test", command: "npm", args: ["test"] });
  }
  return commands;
}

export async function assertRunIdentity({ root, baseSha, taskHash, commandRunner = runProcess }) {
  assertLocal(/^[a-f0-9]{40}$/i.test(baseSha || ""), "RUN_IDENTITY", "Recorded base commit is invalid");
  assertLocal(/^[a-f0-9]{64}$/i.test(taskHash || ""), "RUN_IDENTITY", "Recorded task hash is invalid");
  const head = await commandRunner("git", ["rev-parse", "HEAD"], { cwd: root });
  assertLocal(head.stdout.trim() === baseSha, "STALE_BASE", "Isolated worktree no longer matches the recorded base commit");
  const taskBody = await readFile(path.join(root, ".ai-local", "context", "task.md"));
  const actualHash = createHash("sha256").update(taskBody).digest("hex");
  assertLocal(actualHash === taskHash, "TASK_IDENTITY", "Isolated task context no longer matches the recorded task hash");
}

function validationEnvironment(dependencyRoot) {
  const env = sanitizedChildEnvironment();
  if (dependencyRoot) {
    const bin = path.join(dependencyRoot, "node_modules", ".bin");
    env.PATH = `${bin}${path.delimiter}${env.PATH || ""}`;
    env.NODE_PATH = path.join(dependencyRoot, "node_modules");
  }
  return env;
}

export async function validateImplementation({ root, dependencyRoot, changeName, paths, baseSha, taskHash, commandRunner = runProcess }) {
  assertImplementationPaths(paths, changeName);
  await assertRunIdentity({ root, baseSha, taskHash, commandRunner });
  const tasksPath = path.join(root, "openspec", "changes", changeName, "tasks.md");
  assertTaskMarkersComplete(await readFile(tasksPath, "utf8"));
  await commandRunner("openspec", ["validate", changeName, "--strict"], { cwd: root });
  const checks = verificationCommandsForPaths(paths);
  for (const check of checks) {
    await commandRunner(check.command, check.args, {
      cwd: path.join(root, check.cwd || "."),
      env: validationEnvironment(dependencyRoot),
    });
  }
  return checks.map((check) => check.name);
}

export async function assertOriginalCheckoutUnchanged({ root, baseSha, commandRunner = runProcess }) {
  const head = await commandRunner("git", ["rev-parse", "HEAD"], { cwd: root });
  assertLocal(head.stdout.trim() === baseSha, "STALE_BASE", "Original checkout HEAD changed during the local run");
  const status = await commandRunner("git", ["status", "--porcelain=v1", "--untracked-files=all"], { cwd: root });
  assertLocal(status.stdout.trim() === "", "STALE_WORKTREE", "Original checkout changed during the local run");
}

export async function applyValidatedPatch({ root, baseSha, patch, commandRunner = runProcess }) {
  await assertOriginalCheckoutUnchanged({ root, baseSha, commandRunner });
  await commandRunner("git", ["apply", "--check", "--binary", "-"], { cwd: root, stdin: patch });
  await commandRunner("git", ["apply", "--binary", "-"], { cwd: root, stdin: patch });
  const [head, staged] = await Promise.all([
    commandRunner("git", ["rev-parse", "HEAD"], { cwd: root }),
    commandRunner("git", ["diff", "--cached", "--name-only"], { cwd: root }),
  ]);
  assertLocal(head.stdout.trim() === baseSha, "APPLY_COMMIT", "Local runner must not create commits");
  assertLocal(staged.stdout.trim() === "", "APPLY_STAGED", "Local runner must leave changes unstaged");
}
