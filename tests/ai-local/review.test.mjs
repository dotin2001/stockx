import assert from "node:assert/strict";
import { access, mkdir, readFile, rm, stat, symlink, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { hashApprovedPlan } from "../../automation/ai-local/lib/approved-plan.mjs";
import { runCodexStage } from "../../automation/ai-local/lib/codex.mjs";
import { LocalRunError } from "../../automation/ai-local/lib/errors.mjs";
import {
  assertReviewSnapshotUnchanged,
  blockedReviewReport,
  cleanupReviewContext,
  collectReviewChecks,
  collectReviewSnapshot,
  createReviewContext,
  deriveReviewTarget,
  validateReviewReport,
} from "../../automation/ai-local/lib/review.mjs";
import { git, initRepository } from "./support/helpers.mjs";

const changeName = "local-review-test";
const issueTaskHash = "a".repeat(64);

async function reviewRepository() {
  const root = await initRepository();
  await writeFile(path.join(root, ".gitignore"), ".ai-local/\n.cache/\n");
  await mkdir(path.join(root, "docs"));
  await writeFile(path.join(root, "docs", "modified.md"), "base modified\n");
  await writeFile(path.join(root, "docs", "staged.md"), "base staged\n");
  await writeFile(path.join(root, "docs", "deleted.md"), "delete me\n");
  git(root, ["add", "."]);
  git(root, ["commit", "-m", "review base"]);
  const baseSha = git(root, ["rev-parse", "HEAD"]).stdout.trim();

  const changeRoot = path.join(root, "openspec", "changes", changeName);
  await mkdir(path.join(changeRoot, "specs", "review"), { recursive: true });
  await writeFile(path.join(changeRoot, ".openspec.yaml"), "schema: spec-driven\n");
  await writeFile(path.join(changeRoot, "proposal.md"), "# Proposal\n\nReview changes.\n");
  await writeFile(path.join(changeRoot, "design.md"), "# Design\n\nRead only.\n");
  await writeFile(path.join(changeRoot, "tasks.md"), "- [x] 1.1 Review every state\n");
  await writeFile(path.join(changeRoot, "specs", "review", "spec.md"), "## Requirements\n\n### Requirement: Complete review\nThe review is complete.\n");
  await writeFile(path.join(root, "docs", "committed.md"), "committed after base\n");
  git(root, ["add", "."]);
  git(root, ["commit", "-m", "committed implementation"]);

  await writeFile(path.join(root, "docs", "staged.md"), "staged change\n");
  git(root, ["add", "docs/staged.md"]);
  await writeFile(path.join(root, "docs", "modified.md"), "unstaged change\n");
  await rm(path.join(root, "docs", "deleted.md"));
  await writeFile(path.join(root, "docs", "untracked.md"), "untracked change\n");
  await writeFile(path.join(root, "docs", "binary.bin"), Buffer.from([0, 255, 1, 2, 3]));
  await writeFile(path.join(root, "docs", "large.bin"), Buffer.alloc(1024 * 1024, 7));
  const approvedPlanHash = (await hashApprovedPlan(root, changeName)).hash;
  const options = { root, baseSha, branch: "main", changeName, approvedPlanHash, issueTaskHash };
  return { root, options };
}

test("review snapshot covers committed, staged, unstaged, deleted, binary, large, and untracked files without changing the index", async () => {
  const { root, options } = await reviewRepository();
  const indexBefore = await readFile(path.join(root, ".git", "index"));
  const snapshot = await collectReviewSnapshot(options);
  const indexAfter = await readFile(path.join(root, ".git", "index"));
  assert.deepEqual(indexAfter, indexBefore);
  for (const expected of [
    "docs/committed.md",
    "docs/staged.md",
    "docs/modified.md",
    "docs/deleted.md",
    "docs/untracked.md",
    "docs/binary.bin",
    "docs/large.bin",
    `openspec/changes/${changeName}/tasks.md`,
  ]) assert.ok(snapshot.paths.includes(expected), expected);
  assert.ok(snapshot.stagedSnapshot.includes("docs/staged.md"));
  assert.equal(snapshot.untracked.find((entry) => entry.path === "docs/large.bin").size, 1024 * 1024);
  await assertReviewSnapshotUnchanged(snapshot, options);

  await mkdir(path.join(root, ".cache"));
  await writeFile(path.join(root, ".cache", "test-output"), "ignored\n");
  await assertReviewSnapshotUnchanged(snapshot, options);

  await writeFile(path.join(root, "docs", "untracked.md"), "changed concurrently\n");
  await assert.rejects(() => assertReviewSnapshotUnchanged(snapshot, options), (error) => error.code === "REVIEW_STALE");
});

test("review snapshot rejects unsafe symlinks and detects branch, commit, index, plan, and issue drift", async () => {
  const unsafe = await reviewRepository();
  await symlink("modified.md", path.join(unsafe.root, "docs", "link.md"));
  await assert.rejects(() => collectReviewSnapshot(unsafe.options), (error) => error.code === "REVIEW_PATH");

  for (const mutation of ["branch", "commit", "index", "plan", "issue"]) {
    const { root, options } = await reviewRepository();
    const snapshot = await collectReviewSnapshot(options);
    let currentOptions = options;
    if (mutation === "branch") git(root, ["switch", "-c", "other"]);
    if (mutation === "commit") git(root, ["commit", "-m", "staged concurrent commit"]);
    if (mutation === "index") {
      await writeFile(path.join(root, "docs", "modified.md"), "new staged content\n");
      git(root, ["add", "docs/modified.md"]);
    }
    if (mutation === "plan") await writeFile(path.join(root, "openspec", "changes", changeName, "proposal.md"), "# Proposal\n\nDrifted.\n");
    if (mutation === "issue") currentOptions = { ...options, issueTaskHash: "b".repeat(64) };
    await assert.rejects(
      () => assertReviewSnapshotUnchanged(snapshot, currentOptions),
      (error) => ["REVIEW_STALE", "BRANCH_IDENTITY", "PLAN_CHANGED"].includes(error.code),
      mutation,
    );
  }
});

test("review checks classify pass, fail, blocked prerequisites, and unsupported paths", async () => {
  const calls = [];
  const runner = async (command, args) => {
    calls.push([command, args]);
    if (command === "git") throw new LocalRunError("COMMAND_FAILED", "whitespace failure");
    if (command === "npm") throw new LocalRunError("COMMAND_START", "npm missing");
    return { stdout: "", stderr: "" };
  };
  const checks = await collectReviewChecks({
    root: "/repo",
    changeName,
    paths: ["automation/ai-local/lib/review.mjs"],
    baseSha: "1".repeat(40),
    commandRunner: runner,
  });
  assert.deepEqual(checks.map((entry) => entry.result), ["PASS", "FAIL", "BLOCKED"]);
  assert.deepEqual(calls.find(([command]) => command === "git")[1], ["diff", "--check", "1".repeat(40), "--"]);

  const databaseChecks = await collectReviewChecks({
    root: "/repo",
    changeName,
    paths: ["apps/api/app.py"],
    baseSha: "1".repeat(40),
    applyTestEnvironmentError: new LocalRunError("TEST_POSTGRES_DATABASE_URL", "database unavailable"),
    commandRunner: async () => ({ stdout: "", stderr: "" }),
  });
  assert.equal(databaseChecks.at(-1).result, "BLOCKED");

  const unsupported = await collectReviewChecks({
    root: "/repo",
    changeName,
    paths: ["secrets/unknown.txt"],
    baseSha: "1".repeat(40),
    commandRunner: async () => ({ stdout: "", stderr: "" }),
  });
  assert.equal(unsupported[0].result, "FAIL");
});

function requiredInventory() {
  return [
    { source: "openspec", id: "openspec:complete-review-123", label: "Complete review" },
    { source: "task", id: "task:1.1", label: "1.1 Complete implementation" },
    { source: "check", id: "check:git-diff-check", label: "git diff --check", expectedResult: "PASS" },
  ];
}

function validReport() {
  return {
    version: 1,
    phase: "review",
    summary: "Everything passes.",
    humanReviewRequired: false,
    humanReviewReasons: [],
    entries: [
      { source: "issue", id: "issue:acceptance", label: "Acceptance", result: "PASS", evidence: ["Implemented in docs/example.md"], remainingWork: [] },
      { source: "openspec", id: "openspec:complete-review-123", label: "Complete review", result: "PASS", evidence: ["Implementation matches the spec"], remainingWork: [] },
      { source: "task", id: "task:1.1", label: "1.1 Complete implementation", result: "PASS", evidence: ["Task is complete"], remainingWork: [] },
      { source: "check", id: "check:git-diff-check", label: "git diff --check", result: "PASS", evidence: ["Check passed"], remainingWork: [] },
    ],
  };
}

test("review report validation enforces coverage, unique ids, consistency, and bounded PASS semantics", () => {
  const inventory = requiredInventory();
  const valid = validateReviewReport(validReport(), inventory);
  assert.equal(deriveReviewTarget(valid), "done");

  const missing = validReport();
  missing.entries = missing.entries.filter((entry) => entry.id !== "task:1.1");
  assert.throws(() => validateReviewReport(missing, inventory), (error) => error.code === "REVIEW_COVERAGE");

  const duplicate = validReport();
  duplicate.entries.push({ ...duplicate.entries[0] });
  assert.throws(() => validateReviewReport(duplicate, inventory), (error) => error.code === "REVIEW_REPORT");

  const inconsistent = validReport();
  inconsistent.entries[0] = { ...inconsistent.entries[0], remainingWork: ["should be empty"] };
  assert.throws(() => validateReviewReport(inconsistent, inventory), (error) => error.code === "REVIEW_REPORT");

  const wrongCheck = validReport();
  wrongCheck.entries.at(-1).result = "FAIL";
  wrongCheck.entries.at(-1).remainingWork = ["fix it"];
  assert.throws(() => validateReviewReport(wrongCheck, inventory), (error) => error.code === "REVIEW_CONSISTENCY");

  const oversized = validReport();
  oversized.summary = "x".repeat(2001);
  assert.throws(() => validateReviewReport(oversized, inventory), (error) => error.code === "REVIEW_REPORT");
  assert.throws(() => validateReviewReport({ phase: "review" }, inventory), (error) => error.code === "REVIEW_REPORT");
});

test("status derivation gives Review precedence over Blocked and human review", () => {
  const report = validReport();
  report.entries[0] = { ...report.entries[0], result: "BLOCKED", remainingWork: ["restore a dependency"] };
  assert.equal(deriveReviewTarget(report), "blocked");
  report.entries[1] = { ...report.entries[1], result: "FAIL", remainingWork: ["implement the requirement"] };
  assert.equal(deriveReviewTarget(report), "review");
  report.entries[1] = { ...report.entries[1], result: "PASS", remainingWork: [] };
  report.humanReviewRequired = true;
  assert.equal(deriveReviewTarget(report), "review");
  assert.equal(deriveReviewTarget(blockedReviewReport("Codex unavailable", requiredInventory())), "blocked");
});

test("review context is private, ephemeral, and removed without returning raw issue content", async () => {
  const secret = "raw issue sentinel";
  const root = await initRepository();
  const context = await createReviewContext({
    root,
    runId: "review-run",
    issueTaskBody: secret,
    checks: [],
    baseSha: "1".repeat(40),
    changeName,
  });
  assert.equal((await stat(context.issuePath)).mode & 0o777, 0o600);
  assert.equal(await readFile(context.issuePath, "utf8"), secret);
  assert.doesNotMatch(JSON.stringify(context), new RegExp(secret));
  await cleanupReviewContext(context);
  await assert.rejects(() => access(context.directory), (error) => error.code === "ENOENT");
});

test("Codex review uses a read-only sandbox, sanitized environment, private contexts, and removes raw model output", async () => {
  const worktree = await initRepository();
  const context = await createReviewContext({ root: worktree, runId: "codex-review", issueTaskBody: "issue", checks: [], baseSha: "1".repeat(40), changeName });
  const inventory = requiredInventory();
  const report = validReport();
  let resultPath;
  const result = await runCodexStage({
    root: process.cwd(),
    worktree,
    phase: "review",
    changeName,
    reviewContext: context,
    reviewInventory: inventory,
    baseSha: "1".repeat(40),
    applyTestEnvironment: { TEST_POSTGRES_DATABASE_URL: "postgresql://must-not-leak" },
    commandRunner: async (_command, args, options) => {
      assert.equal(args[args.indexOf("--sandbox") + 1], "read-only");
      assert.equal(args[args.indexOf("--model") + 1], "gpt-5.6-sol");
      assert.equal(options.env.TEST_POSTGRES_DATABASE_URL, undefined);
      assert.equal(options.env.GITHUB_TOKEN, undefined);
      assert.ok(options.env.GH_CONFIG_DIR.endsWith("no-github-auth"));
      assert.ok(options.env.HOME.endsWith("no-user-home"));
      assert.notEqual(options.env.CODEX_HOME, options.env.HOME);
      assert.match(options.stdin, new RegExp(context.issuePath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
      assert.match(options.stdin, /Do not choose or recommend a GitHub Project status/i);
      resultPath = args[args.indexOf("--output-last-message") + 1];
      await writeFile(resultPath, JSON.stringify(report));
      return { stdout: "", stderr: "" };
    },
  });
  assert.equal(result.phase, "review");
  await assert.rejects(() => access(resultPath), (error) => error.code === "ENOENT");
  await cleanupReviewContext(context);
});
