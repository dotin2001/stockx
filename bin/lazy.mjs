#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";

const USAGE = `Usage:
  lazy push "<commit message>"

Automates a guarded Git workflow:
  1. check repository state
  2. git add .
  3. git commit -m "<commit message>"
  4. git push`;

const LOCAL_ONLY_SEGMENTS = new Set([
  ".git",
  ".mypy_cache",
  ".next",
  ".npm",
  ".pnpm-store",
  ".pytest_cache",
  ".ruff_cache",
  ".swc",
  ".turbo",
  ".venv",
  ".vercel",
  "__pycache__",
  "build",
  "coverage",
  "dist",
  "htmlcov",
  "logs",
  "node_modules",
  "out",
  "venv"
]);

function createDefaultIo() {
  return {
    stdout: (message = "") => process.stdout.write(message),
    stderr: (message = "") => process.stderr.write(message)
  };
}

function line(message = "") {
  return `${message}\n`;
}

function runCommand(command, args, { cwd }) {
  return spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    env: process.env
  });
}

function runGit(args, options) {
  return runCommand(options.gitBin ?? "git", args, options);
}

function printCommandOutput(result, io) {
  if (result.stdout) {
    io.stdout(result.stdout);
  }
  if (result.stderr) {
    io.stderr(result.stderr);
  }
}

function fail(message, io, details = []) {
  io.stderr(line(message));
  for (const detail of details) {
    io.stderr(line(`  - ${detail}`));
  }
  return 1;
}

function parseStatus(output) {
  return output
    .split("\n")
    .filter(Boolean)
    .map((entry) => ({
      code: entry.slice(0, 2),
      path: entry.slice(3)
    }));
}

function isUnmerged(code) {
  return code.includes("U") || code === "AA" || code === "DD";
}

function normalizePath(path) {
  return path.replaceAll("\\", "/");
}

function localOnlyReason(path) {
  const normalized = normalizePath(path);
  const segments = normalized.split("/");
  const basename = segments.at(-1) ?? normalized;

  if (basename === ".env" || (basename.startsWith(".env.") && basename !== ".env.example")) {
    return "environment file";
  }

  if (basename.endsWith(".env") && basename !== ".env.example") {
    return "environment file";
  }

  if (basename.endsWith(".log")) {
    return "log file";
  }

  if (basename === ".coverage" || basename.startsWith(".coverage.")) {
    return "coverage file";
  }

  if (basename.endsWith(".pyc") || basename === "$py.class") {
    return "Python cache artifact";
  }

  if (basename.endsWith(".tsbuildinfo")) {
    return "TypeScript build info";
  }

  if (segments.some((segment) => LOCAL_ONLY_SEGMENTS.has(segment))) {
    return "local generated/dependency/cache path";
  }

  if (segments.some((segment) => segment.endsWith(".egg-info"))) {
    return "Python package build metadata";
  }

  if (normalized.startsWith(".yarn/cache/") || normalized.startsWith(".yarn/unplugged/")) {
    return "package manager cache";
  }

  return null;
}

function summarizeChanges(statusEntries, io) {
  if (statusEntries.length === 0) {
    io.stdout(line("No Git-visible changes found."));
    return;
  }

  io.stdout(line(`Candidate Git-visible changes (${statusEntries.length}):`));
  for (const entry of statusEntries.slice(0, 25)) {
    io.stdout(line(`  ${entry.code} ${entry.path}`));
  }
  if (statusEntries.length > 25) {
    io.stdout(line(`  ...and ${statusEntries.length - 25} more`));
  }
}

function preflight({ cwd, gitBin, io }) {
  const insideWorkTree = runGit(["rev-parse", "--is-inside-work-tree"], { cwd, gitBin });
  if (insideWorkTree.status !== 0 || insideWorkTree.stdout.trim() !== "true") {
    return { ok: false, code: fail("Cannot run lazy push outside a Git working tree.", io) };
  }

  const branch = runGit(["symbolic-ref", "--quiet", "--short", "HEAD"], { cwd, gitBin });
  if (branch.status !== 0) {
    return { ok: false, code: fail("Cannot push from a detached HEAD state.", io) };
  }

  const upstream = runGit(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], { cwd, gitBin });
  if (upstream.status !== 0) {
    return {
      ok: false,
      code: fail(`Current branch '${branch.stdout.trim()}' has no upstream remote.`, io, [
        "Set an upstream branch before running lazy push."
      ])
    };
  }

  const status = runGit(["status", "--porcelain=v1", "--untracked-files=all"], { cwd, gitBin });
  if (status.status !== 0) {
    printCommandOutput(status, io);
    return { ok: false, code: fail("Could not inspect Git status.", io) };
  }

  const statusEntries = parseStatus(status.stdout);
  const conflicts = statusEntries.filter((entry) => isUnmerged(entry.code));
  const localOnly = statusEntries
    .map((entry) => ({ ...entry, reason: localOnlyReason(entry.path) }))
    .filter((entry) => entry.reason !== null);

  if (conflicts.length > 0 || localOnly.length > 0) {
    summarizeChanges(statusEntries, io);
    const blockers = [
      ...conflicts.map((entry) => `${entry.path} (${entry.code.trim() || "conflict"})`),
      ...localOnly.map((entry) => `${entry.path} (${entry.reason})`)
    ];
    return {
      ok: false,
      code: fail("Cannot push until blocking file changes are resolved.", io, blockers)
    };
  }

  summarizeChanges(statusEntries, io);
  return {
    ok: true,
    branch: branch.stdout.trim(),
    upstream: upstream.stdout.trim(),
    statusEntries
  };
}

function executePushWorkflow({ cwd, gitBin, io, message, upstream }) {
  const add = runGit(["add", "."], { cwd, gitBin });
  if (add.status !== 0) {
    printCommandOutput(add, io);
    return fail("Git step failed: git add .", io);
  }

  const stagedDiff = runGit(["diff", "--cached", "--quiet"], { cwd, gitBin });
  if (stagedDiff.status === 0) {
    return fail("Nothing to commit after staging changes.", io);
  }
  if (stagedDiff.status !== 1) {
    printCommandOutput(stagedDiff, io);
    return fail("Could not inspect staged changes.", io);
  }

  const commit = runGit(["commit", "-m", message], { cwd, gitBin });
  if (commit.status !== 0) {
    printCommandOutput(commit, io);
    return fail("Git step failed: git commit", io);
  }
  printCommandOutput(commit, io);

  const commitHash = runGit(["rev-parse", "--short", "HEAD"], { cwd, gitBin });
  const shortHash = commitHash.status === 0 ? commitHash.stdout.trim() : "unknown";

  const push = runGit(["push"], { cwd, gitBin });
  if (push.status !== 0) {
    printCommandOutput(push, io);
    return fail("Git step failed: git push", io);
  }
  printCommandOutput(push, io);

  io.stdout(line(`Lazy push complete: ${shortHash} pushed to ${upstream}.`));
  return 0;
}

export function runLazy(args, options = {}) {
  const io = options.io ?? createDefaultIo();
  const cwd = options.cwd ?? process.cwd();
  const gitBin = options.gitBin ?? "git";
  const [command, ...rest] = args;

  if (command !== "push") {
    io.stderr(line(USAGE));
    return 1;
  }

  const message = rest.join(" ").trim();
  if (!message) {
    return fail("Commit message is required.", io, [USAGE]);
  }

  const check = preflight({ cwd, gitBin, io });
  if (!check.ok) {
    return check.code;
  }

  return executePushWorkflow({ cwd, gitBin, io, message, upstream: check.upstream });
}

function isCliEntrypoint() {
  if (!process.argv[1]) {
    return false;
  }

  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isCliEntrypoint()) {
  process.exitCode = runLazy(process.argv.slice(2));
}
