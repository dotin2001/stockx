import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { cleanupIsolatedWorktree, createIsolatedWorktree, findOwnedStaleWorktrees } from "../../automation/ai-local/lib/worktree.mjs";
import {
  applyValidatedPatch,
  assertImplementationPaths,
  assertPlanPaths,
  assertSafeRelativePath,
  assertRunIdentity,
  assertTaskMarkersComplete,
  captureBinaryDiff,
  validateImplementation,
  validatePlan,
  verificationCommandsForPaths,
} from "../../automation/ai-local/lib/validation.mjs";
import { git, initRepository, tempDirectory } from "./support/helpers.mjs";

const changeName = "local-add-search";

async function writePlan(root, complete = false) {
  const changeRoot = path.join(root, "openspec", "changes", changeName);
  await mkdir(path.join(changeRoot, "specs", "search"), { recursive: true });
  await writeFile(path.join(changeRoot, ".openspec.yaml"), "schema: spec-driven\n");
  await writeFile(path.join(changeRoot, "proposal.md"), "# Proposal\n");
  await writeFile(path.join(changeRoot, "design.md"), "# Design\n");
  await writeFile(path.join(changeRoot, "tasks.md"), complete ? "- [x] implement\n" : "- [ ] implement\n");
  await writeFile(path.join(changeRoot, "specs", "search", "spec.md"), "## ADDED Requirements\n");
  return changeRoot;
}

test("temporary worktree is owned, isolated, discoverable, and cleaned safely", async () => {
  const root = await initRepository();
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const owned = await createIsolatedWorktree({ repositoryRoot: root, baseSha });
  assert.equal(git(owned.worktree, ["rev-parse", "HEAD"]).stdout.trim(), baseSha);
  assert.ok((await findOwnedStaleWorktrees(root)).includes(owned.baseDirectory));
  await writeFile(path.join(owned.worktree, "temporary.txt"), "temporary\n");
  assert.equal(git(root, ["status", "--porcelain"]).stdout.trim(), "");
  await cleanupIsolatedWorktree(owned);
  assert.deepEqual(await findOwnedStaleWorktrees(root), []);
  assert.equal(git(root, ["status", "--porcelain"]).stdout.trim(), "");
  await assert.rejects(() => cleanupIsolatedWorktree({ ...owned, baseDirectory: root }), /unverified/);
});

test("plan diff capture includes untracked artifacts and enforces exact scope", async () => {
  const root = await initRepository();
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  await writePlan(root);
  const captured = await captureBinaryDiff(root, baseSha);
  assert.ok(captured.patch.includes("proposal.md"));
  assertPlanPaths(captured.paths, changeName);
  assert.throws(() => assertPlanPaths([...captured.paths, "outside.txt"], changeName), /outside/);
  assert.throws(() => assertPlanPaths(captured.paths.filter((entry) => !entry.endsWith("tasks.md")), changeName), /missing/);
  assert.throws(() => assertSafeRelativePath("../../etc/passwd"), /escapes/);
});

test("plan validation requires complete status and strict validation", async () => {
  const root = await initRepository();
  await writePlan(root);
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const captured = await captureBinaryDiff(root, baseSha);
  const calls = [];
  const runner = async (command, args) => {
    calls.push([command, args]);
    if (args[0] === "status") return { stdout: JSON.stringify({ isPlanningComplete: true }), stderr: "" };
    return { stdout: "", stderr: "" };
  };
  await validatePlan({ root, changeName, paths: captured.paths, commandRunner: runner });
  assert.deepEqual(calls.map((entry) => entry[1][0]), ["status", "validate"]);
  await assert.rejects(() => validatePlan({ root, changeName, paths: captured.paths, commandRunner: async () => ({ stdout: JSON.stringify({ isPlanningComplete: false }), stderr: "" }) }), /incomplete/);
});

test("plan validation accepts schema-authorized skipped specs and optional design", async () => {
  const root = await initRepository();
  const changeRoot = path.join(root, "openspec", "changes", changeName);
  await mkdir(changeRoot, { recursive: true });
  await writeFile(path.join(changeRoot, ".openspec.yaml"), "schema: spec-driven\nskip_specs: true\n");
  await writeFile(path.join(changeRoot, "proposal.md"), "# Proposal\n");
  await writeFile(path.join(changeRoot, "tasks.md"), "- [ ] implement\n");
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const captured = await captureBinaryDiff(root, baseSha);
  const status = {
    isPlanningComplete: false,
    isComplete: false,
    applyRequires: ["tasks"],
    artifacts: [
      { id: "proposal", status: "done" },
      { id: "specs", status: "skipped" },
      { id: "design", status: "ready" },
      { id: "tasks", status: "done" },
    ],
  };
  const calls = [];
  await validatePlan({
    root,
    changeName,
    paths: captured.paths,
    commandRunner: async (command, args) => {
      calls.push([command, args]);
      return args[0] === "status" ? { stdout: JSON.stringify(status), stderr: "" } : { stdout: "", stderr: "" };
    },
  });
  assert.deepEqual(calls.map((entry) => entry[1][0]), ["status", "validate"]);

  const specsRequired = {
    ...status,
    artifacts: status.artifacts.map((artifact) => artifact.id === "specs" ? { ...artifact, status: "ready" } : artifact),
  };
  await assert.rejects(() => validatePlan({
    root,
    changeName,
    paths: captured.paths,
    commandRunner: async (_command, args) => args[0] === "status" ? { stdout: JSON.stringify(specsRequired), stderr: "" } : { stdout: "", stderr: "" },
  }), /no capability specification/);
});

test("implementation validation protects authority, task truth, and verification policy", async () => {
  const root = await initRepository();
  await writePlan(root, true);
  await mkdir(path.join(root, "docs"));
  await writeFile(path.join(root, "docs", "feature.md"), "feature\n");
  await mkdir(path.join(root, ".ai-local", "context"), { recursive: true });
  const taskBody = Buffer.from("# Task\n");
  await writeFile(path.join(root, ".ai-local", "context", "task.md"), taskBody);
  const { createHash } = await import("node:crypto");
  const taskHash = createHash("sha256").update(taskBody).digest("hex");
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const captured = await captureBinaryDiff(root, baseSha);
  assertImplementationPaths(captured.paths, changeName);
  assert.equal(assertTaskMarkersComplete("- [x] one\n- [X] two\n"), 2);
  assert.throws(() => assertTaskMarkersComplete("- [ ] incomplete\n"), /not all complete/);
  assert.throws(() => assertImplementationPaths([...captured.paths, "bin/ai-local.mjs"], changeName), /protected authority/);
  assert.throws(() => verificationCommandsForPaths([`openspec/changes/${changeName}/tasks.md`, "unknown/file.xyz"]), /No trusted/);

  const calls = [];
  const verification = await validateImplementation({
    root,
    changeName,
    paths: captured.paths,
    baseSha,
    taskHash,
    commandRunner: async (command, args, options) => {
      calls.push({ command, args, options });
      if (command === "git" && args[0] === "rev-parse") return { stdout: `${baseSha}\n`, stderr: "" };
      return { stdout: "", stderr: "" };
    },
  });
  assert.deepEqual(verification, ["git diff --check"]);
  assert.equal(calls[0].command, "git");
  await assert.rejects(() => assertRunIdentity({ root, baseSha, taskHash: "c".repeat(64) }), /task context/);
});

test("validated binary patch applies unstaged and rejects stale or conflicting targets", async () => {
  const source = await initRepository();
  const baseSha = git(source, ["rev-parse", "HEAD"]).stdout.trim();
  await writeFile(path.join(source, "README.md"), "# Changed\n");
  const patch = git(source, ["diff", "--binary", "HEAD", "--"]).stdout;

  const targetParent = await tempDirectory();
  const target = path.join(targetParent, "target");
  git(targetParent, ["clone", "--quiet", source, target]);
  git(target, ["checkout", "--detach", baseSha]);
  await applyValidatedPatch({ root: target, baseSha, patch });
  assert.equal(await readFile(path.join(target, "README.md"), "utf8"), "# Changed\n");
  assert.equal(git(target, ["diff", "--cached", "--name-only"]).stdout.trim(), "");
  assert.equal(git(target, ["rev-parse", "HEAD"]).stdout.trim(), baseSha);

  await writeFile(path.join(target, "other.txt"), "drift\n");
  await assert.rejects(() => applyValidatedPatch({ root: target, baseSha, patch }), /changed during/);
});
