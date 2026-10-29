import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { copyApprovedPlan, hashApprovedPlan, inspectApprovedPlanCheckout } from "../../automation/ai-local/lib/approved-plan.mjs";
import { applyImplementationPatch, captureIndexDiff } from "../../automation/ai-local/lib/validation.mjs";
import { cleanupIsolatedWorktree, createIsolatedWorktree } from "../../automation/ai-local/lib/worktree.mjs";
import { git, initRepository } from "./support/helpers.mjs";

const changeName = "local-reviewed-plan";

async function writePlan(root, task = "- [ ] 1.1 Implement feature\n") {
  const changeRoot = path.join(root, "openspec", "changes", changeName);
  await mkdir(path.join(changeRoot, "specs", "feature"), { recursive: true });
  await writeFile(path.join(changeRoot, ".openspec.yaml"), "schema: spec-driven\n");
  await writeFile(path.join(changeRoot, "proposal.md"), "# Proposal\n");
  await writeFile(path.join(changeRoot, "design.md"), "# Design\n");
  await writeFile(path.join(changeRoot, "tasks.md"), task);
  await writeFile(path.join(changeRoot, "specs", "feature", "spec.md"), "## Purpose\nFeature contract.\n");
}

test("approved plan hashing ignores only checkbox state", async () => {
  const root = await initRepository();
  await writePlan(root);
  const first = await hashApprovedPlan(root, changeName);
  await writeFile(path.join(root, "openspec", "changes", changeName, "tasks.md"), "- [x] 1.1 Implement feature\n");
  const completed = await hashApprovedPlan(root, changeName);
  assert.equal(completed.hash, first.hash);
  await writeFile(path.join(root, "openspec", "changes", changeName, "tasks.md"), "- [x] 1.1 Implement a different feature\n");
  const rewritten = await hashApprovedPlan(root, changeName);
  assert.notEqual(rewritten.hash, first.hash);
});

test("apply checkout accepts only the selected unstaged plan", async () => {
  const root = await initRepository();
  await writePlan(root);
  const inspected = await inspectApprovedPlanCheckout(root, changeName);
  assert.equal(inspected.planDirty, true);
  assert.ok(inspected.dirtyPaths.every((filePath) => filePath.startsWith(`openspec/changes/${changeName}/`)));
  await writeFile(path.join(root, "unrelated.txt"), "no\n");
  await assert.rejects(() => inspectApprovedPlanCheckout(root, changeName), (error) => error.code === "WORKTREE_DIRTY");

  const staged = await initRepository();
  await writePlan(staged);
  git(staged, ["add", "openspec"]);
  await assert.rejects(() => inspectApprovedPlanCheckout(staged, changeName), (error) => error.code === "WORKTREE_STAGED");
});

test("uncommitted plan becomes an isolated index baseline without a commit", async () => {
  const root = await initRepository();
  await writePlan(root);
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const owned = await createIsolatedWorktree({ repositoryRoot: root, baseSha });
  try {
    const original = await inspectApprovedPlanCheckout(root, changeName);
    const approved = await hashApprovedPlan(root, changeName);
    await copyApprovedPlan({ sourceRoot: root, worktree: owned.worktree, changeName });
    await writeFile(path.join(owned.worktree, "openspec", "changes", changeName, "tasks.md"), "- [x] 1.1 Implement feature\n");
    await mkdir(path.join(owned.worktree, "docs"));
    await writeFile(path.join(owned.worktree, "docs", "feature.md"), "implemented\n");
    const delta = await captureIndexDiff(owned.worktree);
    assert.deepEqual(delta.paths.sort(), ["docs/feature.md", `openspec/changes/${changeName}/tasks.md`].sort());
    assert.equal(git(owned.worktree, ["rev-parse", "HEAD"]).stdout.trim(), baseSha);
    await applyImplementationPatch({ root, changeName, baseSha, statusSnapshot: original.statusSnapshot, approvedPlanHash: approved.hash, patch: delta.patch });
    assert.equal(await readFile(path.join(root, "openspec", "changes", changeName, "tasks.md"), "utf8"), "- [x] 1.1 Implement feature\n");
  } finally {
    await cleanupIsolatedWorktree(owned);
  }
});

test("implementation application rejects checkout or approved-plan drift", async () => {
  const root = await initRepository();
  await writePlan(root);
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();
  const inspected = await inspectApprovedPlanCheckout(root, changeName);
  const approved = await hashApprovedPlan(root, changeName);
  await writeFile(path.join(root, "openspec", "changes", changeName, "proposal.md"), "# Changed after approval\n");
  await assert.rejects(() => applyImplementationPatch({ root, changeName, baseSha, statusSnapshot: inspected.statusSnapshot, approvedPlanHash: approved.hash, patch: "" }), (error) => ["STALE_WORKTREE", "STALE_PLAN"].includes(error.code));
});
