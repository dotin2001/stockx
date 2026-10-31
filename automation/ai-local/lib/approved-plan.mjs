import { createHash } from "node:crypto";
import { access, cp, lstat, readFile, readdir, rm } from "node:fs/promises";
import path from "node:path";

import { assertLocal, LocalRunError } from "./errors.mjs";
import { runProcess } from "./process.mjs";

function safeRelativePath(filePath) {
  assertLocal(typeof filePath === "string" && filePath.length > 0 && filePath.length <= 4096, "PATCH_PATH", "Changed path is invalid");
  assertLocal(!filePath.includes("\0") && !filePath.includes("\\") && !path.posix.isAbsolute(filePath), "PATCH_PATH", "Changed path is unsafe");
  const normalized = path.posix.normalize(filePath);
  assertLocal(normalized === filePath && normalized !== ".." && !normalized.startsWith("../") && !normalized.split("/").includes(".git"), "PATCH_PATH", "Changed path escapes the repository");
  return normalized;
}

export function assertChangeName(changeName) {
  assertLocal(typeof changeName === "string" && changeName.length <= 80 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(changeName), "CHANGE_NAME", "Change name must be safe kebab-case");
  return changeName;
}

function changeRelative(changeName) {
  return `openspec/changes/${assertChangeName(changeName)}`;
}

async function walk(directory, relativeBase, output) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    const relative = `${relativeBase}/${entry.name}`.split(path.sep).join("/");
    if (entry.isSymbolicLink()) throw new LocalRunError("PLAN_SYMLINK", `Approved plan cannot contain symbolic links: ${relative}`);
    if (entry.isDirectory()) await walk(absolute, relative, output);
    else if (entry.isFile()) output.push(safeRelativePath(relative));
    else throw new LocalRunError("PLAN_FILE", `Approved plan contains an unsupported file: ${relative}`);
  }
}

export async function listApprovedPlanPaths(root, changeName) {
  const relative = changeRelative(changeName);
  const directory = path.join(root, ...relative.split("/"));
  try {
    const stat = await lstat(directory);
    assertLocal(stat.isDirectory() && !stat.isSymbolicLink(), "PLAN_MISSING", `OpenSpec change does not exist: ${changeName}`);
  } catch (error) {
    if (error instanceof LocalRunError) throw error;
    throw new LocalRunError("PLAN_MISSING", `OpenSpec change does not exist: ${changeName}`);
  }
  const paths = [];
  await walk(directory, relative, paths);
  paths.sort();
  for (const required of [".openspec.yaml", "proposal.md", "tasks.md"]) {
    assertLocal(paths.includes(`${relative}/${required}`), "PLAN_ARTIFACT", `Approved plan is missing ${required}`);
  }
  return paths;
}

function normalizedPlanContent(relativePath, content) {
  if (!relativePath.endsWith("/tasks.md")) return content;
  return content.replace(/^(\s*- \[)[ xX](\]\s+.+)$/gm, "$1 $2");
}

export async function hashApprovedPlan(root, changeName) {
  const paths = await listApprovedPlanPaths(root, changeName);
  const hash = createHash("sha256");
  for (const relativePath of paths) {
    const content = await readFile(path.join(root, ...relativePath.split("/")));
    hash.update(relativePath).update("\0").update(normalizedPlanContent(relativePath, content.toString("utf8"))).update("\0");
  }
  return { hash: hash.digest("hex"), paths };
}

function parseStatus(raw) {
  const records = raw.split("\0").filter(Boolean);
  return records.map((record) => {
    assertLocal(record.length >= 4 && record[2] === " ", "WORKTREE_STATUS", "Git status output is malformed");
    const x = record[0];
    const y = record[1];
    const relativePath = safeRelativePath(record.slice(3));
    assertLocal(x === " " || x === "?", "WORKTREE_STAGED", "Apply does not accept staged changes");
    assertLocal((x === "?" && y === "?") || (x === " " && ["M", "D"].includes(y)), "WORKTREE_STATUS", `Unsupported checkout change state for ${relativePath}`);
    return relativePath;
  });
}

export async function inspectApprovedPlanCheckout(root, changeName, commandRunner = runProcess) {
  const branchResult = await commandRunner("git", ["symbolic-ref", "--quiet", "--short", "HEAD"], { cwd: root }).catch(() => { throw new LocalRunError("BRANCH_DETACHED", "ai:local apply requires an attached Git branch"); });
  const [head, status] = await Promise.all([
    commandRunner("git", ["rev-parse", "HEAD"], { cwd: root }),
    commandRunner("git", ["status", "--porcelain=v1", "-z", "--untracked-files=all"], { cwd: root }),
  ]);
  const paths = parseStatus(status.stdout);
  const prefix = `${changeRelative(changeName)}/`;
  assertLocal(paths.every((filePath) => filePath.startsWith(prefix)), "WORKTREE_DIRTY", `Apply accepts changes only inside ${changeRelative(changeName)}`);
  await access(path.join(root, ...changeRelative(changeName).split("/")));
  return {
    branch: branchResult.stdout.trim(),
    baseSha: head.stdout.trim(),
    dirtyPaths: Object.freeze(paths),
    statusSnapshot: status.stdout,
    planDirty: paths.length > 0,
  };
}

export async function inspectCompletedImplementationCheckout(root, commandRunner = runProcess) {
  const branchResult = await commandRunner("git", ["symbolic-ref", "--quiet", "--short", "HEAD"], { cwd: root }).catch(() => { throw new LocalRunError("BRANCH_DETACHED", "Status sync requires an attached Git branch"); });
  const [head, staged, status] = await Promise.all([
    commandRunner("git", ["rev-parse", "HEAD"], { cwd: root }),
    commandRunner("git", ["diff", "--cached", "--name-only", "-z", "--"], { cwd: root }),
    commandRunner("git", ["status", "--porcelain=v1", "-z", "--untracked-files=all"], { cwd: root }),
  ]);
  assertLocal(staged.stdout.length === 0, "WORKTREE_STAGED", "Status sync does not accept staged changes");
  const paths = parseStatus(status.stdout);
  assertLocal(paths.length > 0, "IMPLEMENTATION_EMPTY", "Status sync requires a non-empty unstaged implementation delta");
  return Object.freeze({
    branch: branchResult.stdout.trim(),
    baseSha: head.stdout.trim(),
    paths: Object.freeze(paths),
    statusSnapshot: status.stdout,
  });
}

export async function assertApprovedCheckoutUnchanged({ root, changeName, baseSha, statusSnapshot, approvedPlanHash, commandRunner = runProcess }) {
  const [head, status, currentPlan] = await Promise.all([
    commandRunner("git", ["rev-parse", "HEAD"], { cwd: root }),
    commandRunner("git", ["status", "--porcelain=v1", "-z", "--untracked-files=all"], { cwd: root }),
    hashApprovedPlan(root, changeName),
  ]);
  assertLocal(head.stdout.trim() === baseSha, "STALE_BASE", "Original checkout HEAD changed during apply");
  assertLocal(status.stdout === statusSnapshot, "STALE_WORKTREE", "Original checkout changed during apply");
  assertLocal(currentPlan.hash === approvedPlanHash, "STALE_PLAN", "Approved OpenSpec plan changed during apply");
}

export async function copyApprovedPlan({ sourceRoot, worktree, changeName, commandRunner = runProcess }) {
  const relative = changeRelative(changeName);
  const source = path.join(sourceRoot, ...relative.split("/"));
  const target = path.join(worktree, ...relative.split("/"));
  await rm(target, { recursive: true, force: true });
  await cp(source, target, { recursive: true, errorOnExist: true });
  await commandRunner("git", ["add", "--", relative], { cwd: worktree });
}
