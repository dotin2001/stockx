import { lstat, mkdtemp, readFile, readdir, realpath, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { assertLocal, LocalRunError } from "./errors.mjs";
import { runProcess } from "./process.mjs";

const PREFIX = "stockx-ai-local-";

function ownedBase(directory) {
  return path.basename(directory).startsWith(PREFIX) && path.resolve(path.dirname(directory)) === path.resolve(os.tmpdir());
}

export async function findOwnedStaleWorktrees(repositoryRoot) {
  const root = await realpath(repositoryRoot);
  const entries = await readdir(os.tmpdir(), { withFileTypes: true });
  const found = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith(PREFIX)) continue;
    const baseDirectory = path.join(os.tmpdir(), entry.name);
    try {
      const marker = JSON.parse(await readFile(path.join(baseDirectory, "owner.json"), "utf8"));
      if (marker.version === 1 && marker.repositoryRoot === root && marker.worktree === path.join(baseDirectory, "worktree")) found.push(baseDirectory);
    } catch {
      // Unmarked temporary directories are never considered owned.
    }
  }
  return found;
}

export async function createIsolatedWorktree({ repositoryRoot, baseSha, commandRunner = runProcess }) {
  const root = await realpath(repositoryRoot);
  const baseDirectory = await mkdtemp(path.join(os.tmpdir(), PREFIX));
  const worktree = path.join(baseDirectory, "worktree");
  const marker = { version: 1, repositoryRoot: root, worktree, baseSha };
  await writeFile(path.join(baseDirectory, "owner.json"), `${JSON.stringify(marker)}\n`, { mode: 0o600, flag: "wx" });
  try {
    await commandRunner("git", ["worktree", "add", "--detach", worktree, baseSha], { cwd: root });
  } catch (error) {
    await rm(baseDirectory, { recursive: true, force: true });
    throw error;
  }
  return { baseDirectory, worktree, repositoryRoot: root, baseSha };
}

export async function cleanupIsolatedWorktree(owned, commandRunner = runProcess) {
  if (!owned) return;
  const { baseDirectory, worktree, repositoryRoot, baseSha } = owned;
  assertLocal(ownedBase(baseDirectory) && worktree === path.join(baseDirectory, "worktree"), "WORKTREE_OWNERSHIP", "Refusing to clean an unverified worktree path");
  let marker;
  try {
    marker = JSON.parse(await readFile(path.join(baseDirectory, "owner.json"), "utf8"));
  } catch {
    throw new LocalRunError("WORKTREE_OWNERSHIP", "Refusing to clean a worktree without its ownership marker");
  }
  assertLocal(marker.version === 1 && marker.repositoryRoot === repositoryRoot && marker.worktree === worktree && marker.baseSha === baseSha, "WORKTREE_OWNERSHIP", "Worktree ownership marker does not match");
  try {
    const stat = await lstat(worktree);
    if (stat.isDirectory()) await commandRunner("git", ["worktree", "remove", "--force", worktree], { cwd: repositoryRoot });
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  await rm(baseDirectory, { recursive: true, force: true });
}
