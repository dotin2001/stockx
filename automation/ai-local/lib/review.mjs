import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { lstat, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { addApplyTestEnvironment, TEST_POSTGRES_DATABASE_URL } from "./apply-environment.mjs";
import { hashApprovedPlan } from "./approved-plan.mjs";
import { assertLocal, LocalRunError, sanitizeText, secretValues } from "./errors.mjs";
import { runProcess, sanitizedChildEnvironment } from "./process.mjs";
import { assertSafeRelativePath, verificationCommandsForPaths } from "./validation.mjs";

const RESULT_VALUES = new Set(["PASS", "FAIL", "BLOCKED"]);
const SOURCE_VALUES = new Set(["issue", "openspec", "task", "check"]);
const MAX_ENTRIES = 200;
const MAX_CHANGED_PATHS = 500;

function splitNul(value) {
  return String(value || "").split("\0").filter(Boolean);
}

function hashText(value) {
  return createHash("sha256").update(value).digest("hex");
}

async function hashFile(filePath) {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(filePath)) hash.update(chunk);
  return hash.digest("hex");
}

function freezeSnapshot(snapshot) {
  return Object.freeze({
    ...snapshot,
    paths: Object.freeze([...snapshot.paths]),
    untracked: Object.freeze(snapshot.untracked.map((entry) => Object.freeze({ ...entry }))),
  });
}

export async function collectReviewSnapshot({ root, baseSha, branch, changeName, approvedPlanHash, issueTaskHash, commandRunner = runProcess }) {
  assertLocal(/^[a-f0-9]{40}$/i.test(baseSha || ""), "BASE_COMMIT", "Recorded base commit is invalid");
  assertLocal(/^[a-f0-9]{64}$/i.test(issueTaskHash || ""), "TASK_IDENTITY", "Recorded issue task identity is invalid");
  let branchResult;
  try {
    branchResult = await commandRunner("git", ["symbolic-ref", "--quiet", "--short", "HEAD"], { cwd: root });
  } catch {
    throw new LocalRunError("BRANCH_DETACHED", "Review requires the recorded attached Git branch");
  }
  assertLocal(branchResult.stdout.trim() === branch, "BRANCH_IDENTITY", `Current branch does not match recorded branch ${branch}`);
  const [head, status, staged, trackedNames, trackedDiff, untrackedResult, currentPlan] = await Promise.all([
    commandRunner("git", ["rev-parse", "HEAD"], { cwd: root }),
    commandRunner("git", ["status", "--porcelain=v1", "-z", "--untracked-files=all"], { cwd: root }),
    commandRunner("git", ["diff", "--cached", "--name-only", "-z", "--"], { cwd: root }),
    commandRunner("git", ["diff", "--name-only", "-z", baseSha, "--"], { cwd: root }),
    commandRunner("git", ["diff", "--binary", "--no-ext-diff", baseSha, "--"], { cwd: root }),
    commandRunner("git", ["ls-files", "--others", "--exclude-standard", "-z"], { cwd: root }),
    hashApprovedPlan(root, changeName),
  ]);
  assertLocal(currentPlan.hash === approvedPlanHash, "PLAN_CHANGED", "Approved OpenSpec contract changed after planning");
  const trackedPaths = splitNul(trackedNames.stdout).map(assertSafeRelativePath);
  const untrackedPaths = splitNul(untrackedResult.stdout).map(assertSafeRelativePath);
  assertLocal(trackedPaths.length + untrackedPaths.length <= MAX_CHANGED_PATHS, "REVIEW_PATH", `Review supports at most ${MAX_CHANGED_PATHS} changed paths`);
  const untracked = [];
  for (const relativePath of untrackedPaths) {
    const absolute = path.join(root, ...relativePath.split("/"));
    const file = await lstat(absolute);
    assertLocal(file.isFile() && !file.isSymbolicLink(), "REVIEW_PATH", `Untracked review path must be a regular file: ${relativePath}`);
    untracked.push({ path: relativePath, size: file.size, sha256: await hashFile(absolute) });
  }
  const paths = [...new Set([...trackedPaths, ...untrackedPaths])].sort();
  const identity = {
    branch,
    baseSha,
    headSha: head.stdout.trim(),
    statusSnapshot: status.stdout,
    stagedSnapshot: staged.stdout,
    trackedDiffHash: hashText(trackedDiff.stdout),
    untracked,
    paths,
    approvedPlanHash: currentPlan.hash,
    issueTaskHash,
  };
  return freezeSnapshot({ ...identity, digest: hashText(JSON.stringify(identity)) });
}

export async function assertReviewSnapshotUnchanged(snapshot, options) {
  const current = await collectReviewSnapshot(options);
  assertLocal(current.digest === snapshot.digest, "REVIEW_STALE", "Branch, history, index, working tree, issue identity, or approved plan changed during review");
  return current;
}

function checkEntry(id, label, result, evidence, remainingWork = []) {
  return Object.freeze({ source: "check", id, label, result, evidence: Object.freeze(evidence), remainingWork: Object.freeze(remainingWork) });
}

function checkId(name) {
  return `check:${String(name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}

function validationEnvironment(dependencyRoot, applyTestEnvironment) {
  const env = sanitizedChildEnvironment();
  addApplyTestEnvironment(env, applyTestEnvironment);
  if (dependencyRoot) {
    env.PATH = `${path.join(dependencyRoot, "node_modules", ".bin")}${path.delimiter}${env.PATH || ""}`;
    env.NODE_PATH = path.join(dependencyRoot, "node_modules");
  }
  return env;
}

function classifyCheckError(error) {
  const blocked = ["COMMAND_START", "COMMAND_ABORTED", "COMMAND_SIGNAL"].includes(error?.code);
  const result = blocked ? "BLOCKED" : "FAIL";
  const code = typeof error?.code === "string" ? error.code : "COMMAND_FAILED";
  return {
    result,
    evidence: [blocked ? "Required check could not run" : "Required check executed and failed"],
    remainingWork: [blocked ? `Restore the check prerequisite and retry (${code})` : `Correct the failure and rerun the check (${code})`],
  };
}

export async function collectReviewChecks({ root, dependencyRoot = root, changeName, paths, baseSha, applyTestEnvironment = {}, applyTestEnvironmentError = null, commandRunner = runProcess }) {
  const checks = [{ name: "openspec strict validation", command: "openspec", args: ["validate", changeName, "--strict"] }];
  let selected;
  try {
    selected = verificationCommandsForPaths(paths, { baseSha });
  } catch (error) {
    return Object.freeze([checkEntry("check:verification-policy", "trusted verification policy", "FAIL", ["Changed paths are outside the trusted verification policy"], [sanitizeText(error.message).slice(0, 500)])]);
  }
  checks.push(...selected);
  const results = [];
  const secrets = secretValues({ ...process.env, ...applyTestEnvironment });
  for (const check of checks) {
    const id = checkId(check.name);
    const requiresPostgres = check.command === "python" && check.args[0] === "-m" && check.args[1] === "pytest";
    if (requiresPostgres && (applyTestEnvironmentError || typeof applyTestEnvironment?.[TEST_POSTGRES_DATABASE_URL] !== "string")) {
      const reason = applyTestEnvironmentError?.message || `${TEST_POSTGRES_DATABASE_URL} is required to run backend verification`;
      results.push(checkEntry(id, check.name, "BLOCKED", ["Required PostgreSQL verification environment is unavailable"], [sanitizeText(reason, secrets).slice(0, 500)]));
      continue;
    }
    try {
      await commandRunner(check.command, check.args, {
        cwd: path.join(root, check.cwd || "."),
        env: validationEnvironment(dependencyRoot, applyTestEnvironment),
      });
      results.push(checkEntry(id, check.name, "PASS", [`${check.name} completed successfully`]));
    } catch (error) {
      const classified = classifyCheckError(error);
      results.push(checkEntry(id, check.name, classified.result, classified.evidence, classified.remainingWork));
    }
  }
  return Object.freeze(results);
}

async function walkSpecs(directory, output) {
  let entries;
  try { entries = await readdir(directory, { withFileTypes: true }); } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) await walkSpecs(absolute, output);
    else if (entry.isFile() && entry.name === "spec.md") output.push(absolute);
  }
}

function inventoryId(prefix, value, index, discriminator = "") {
  const slug = String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80);
  const suffix = hashText(`${discriminator}\0${value}\0${index}`).slice(0, 10);
  return `${prefix}:${slug || index + 1}-${suffix}`;
}

export async function collectRequiredReviewInventory({ root, changeName, checks }) {
  const changeRoot = path.join(root, "openspec", "changes", changeName);
  const specPaths = [];
  await walkSpecs(path.join(changeRoot, "specs"), specPaths);
  const inventory = [];
  for (const specPath of specPaths.sort()) {
    const content = await readFile(specPath, "utf8");
    const requirements = [...content.matchAll(/^### Requirement:\s+(.+)$/gm)];
    const relativeSpec = path.relative(changeRoot, specPath).split(path.sep).join("/");
    requirements.forEach((match, index) => inventory.push(Object.freeze({ source: "openspec", id: inventoryId("openspec", match[1], index, relativeSpec), label: match[1].trim() })));
  }
  const tasks = await readFile(path.join(changeRoot, "tasks.md"), "utf8");
  for (const [index, match] of [...tasks.matchAll(/^\s*- \[([ xX])\]\s+(.+)$/gm)].entries()) {
    const taskNumber = match[2].match(/^(\d+(?:\.\d+)*)\s+/)?.[1] || String(index + 1);
    inventory.push(Object.freeze({ source: "task", id: `task:${taskNumber}`, label: match[2].trim(), expectedResult: match[1].toLowerCase() === "x" ? null : "FAIL" }));
  }
  for (const check of checks) inventory.push(Object.freeze({ source: "check", id: check.id, label: check.label, expectedResult: check.result }));
  assertLocal(inventory.length > 0 && inventory.length <= MAX_ENTRIES, "REVIEW_INVENTORY", "Review inventory is empty or too large");
  assertLocal(new Set(inventory.map((entry) => entry.id)).size === inventory.length, "REVIEW_INVENTORY", "Review inventory contains duplicate identifiers");
  return Object.freeze(inventory);
}

function boundedStrings(value, name, { min = 0, max = 10, length = 500 } = {}) {
  assertLocal(Array.isArray(value) && value.length >= min && value.length <= max, "REVIEW_REPORT", `${name} has invalid item count`);
  assertLocal(value.every((item) => typeof item === "string" && item.trim().length > 0 && item.length <= length), "REVIEW_REPORT", `${name} contains invalid text`);
  return Object.freeze(value.map((item) => item.trim()));
}

export function validateReviewReport(value, requiredInventory = []) {
  assertLocal(value && typeof value === "object" && !Array.isArray(value), "REVIEW_REPORT", "Review report must be an object");
  const expectedKeys = ["entries", "humanReviewReasons", "humanReviewRequired", "phase", "summary", "version"].sort();
  const keys = Object.keys(value).sort();
  assertLocal(keys.length === expectedKeys.length && keys.every((key, index) => key === expectedKeys[index]), "REVIEW_REPORT", "Review report contains missing or unexpected fields");
  assertLocal(value.version === 1 && value.phase === "review", "REVIEW_REPORT", "Review report version or phase is invalid");
  assertLocal(typeof value.summary === "string" && value.summary.trim().length > 0 && value.summary.length <= 2000, "REVIEW_REPORT", "Review summary is invalid");
  assertLocal(typeof value.humanReviewRequired === "boolean", "REVIEW_REPORT", "Human review flag is invalid");
  const humanReviewReasons = boundedStrings(value.humanReviewReasons, "human review reasons", { min: value.humanReviewRequired ? 1 : 0, max: 10 });
  assertLocal(value.humanReviewRequired || humanReviewReasons.length === 0, "REVIEW_REPORT", "Human review reasons require the human review flag");
  assertLocal(Array.isArray(value.entries) && value.entries.length > 0 && value.entries.length <= MAX_ENTRIES, "REVIEW_REPORT", "Review entries are invalid");
  const entries = value.entries.map((entry) => {
    const entryKeys = ["evidence", "id", "label", "remainingWork", "result", "source"].sort();
    const actualKeys = Object.keys(entry || {}).sort();
    assertLocal(actualKeys.length === entryKeys.length && actualKeys.every((key, index) => key === entryKeys[index]), "REVIEW_REPORT", "Review entry contains missing or unexpected fields");
    assertLocal(SOURCE_VALUES.has(entry.source), "REVIEW_REPORT", "Review entry source is invalid");
    assertLocal(typeof entry.id === "string" && /^[a-z]+:[a-z0-9][a-z0-9._:-]{0,119}$/.test(entry.id), "REVIEW_REPORT", "Review entry id is invalid");
    assertLocal(typeof entry.label === "string" && entry.label.trim().length > 0 && entry.label.length <= 500, "REVIEW_REPORT", "Review entry label is invalid");
    assertLocal(RESULT_VALUES.has(entry.result), "REVIEW_REPORT", "Review entry result is invalid");
    const evidence = boundedStrings(entry.evidence, "review evidence", { min: 1 });
    const remainingWork = boundedStrings(entry.remainingWork, "review remaining work", { min: entry.result === "PASS" ? 0 : 1 });
    assertLocal(entry.result !== "PASS" || remainingWork.length === 0, "REVIEW_REPORT", "Passing entry cannot contain remaining work");
    return Object.freeze({ source: entry.source, id: entry.id, label: entry.label.trim(), result: entry.result, evidence, remainingWork });
  });
  assertLocal(new Set(entries.map((entry) => entry.id)).size === entries.length, "REVIEW_REPORT", "Review report contains duplicate ids");
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  for (const required of requiredInventory) {
    const actual = byId.get(required.id);
    assertLocal(actual && actual.source === required.source, "REVIEW_COVERAGE", `Review report omitted required entry ${required.id}`);
    if (required.expectedResult) assertLocal(actual.result === required.expectedResult, "REVIEW_CONSISTENCY", `Review result for ${required.id} contradicts deterministic evidence`);
  }
  const issueEntries = entries.filter((entry) => entry.source === "issue");
  const semanticReviewBlocked = entries.some((entry) => entry.id === "check:semantic-review" && entry.result === "BLOCKED");
  assertLocal(issueEntries.length > 0 || value.humanReviewRequired || semanticReviewBlocked, "REVIEW_COVERAGE", "Review report must enumerate issue criteria, require human review, or record an unavailable semantic review");
  return Object.freeze({ version: 1, phase: "review", summary: value.summary.trim(), humanReviewRequired: value.humanReviewRequired, humanReviewReasons, entries: Object.freeze(entries) });
}

export function blockedReviewReport(message, requiredInventory = []) {
  const detail = sanitizeText(message).slice(0, 500) || "Semantic review could not run";
  const inventoryEntries = requiredInventory.map((entry) => {
    const result = entry.expectedResult || "BLOCKED";
    return checkEntry(
      entry.id,
      entry.label,
      result,
      [result === "PASS" ? "Deterministic host evidence passed" : result === "FAIL" ? "Deterministic host evidence failed" : "Semantic evaluation is unavailable"],
      result === "PASS" ? [] : [result === "FAIL" ? "Complete or correct this requirement" : "Restore semantic review and retry"],
    );
  }).map((entry, index) => Object.freeze({ ...entry, source: requiredInventory[index].source }));
  return Object.freeze({
    version: 1,
    phase: "review",
    summary: "Required semantic review could not run.",
    humanReviewRequired: false,
    humanReviewReasons: Object.freeze([]),
    entries: Object.freeze([...inventoryEntries, checkEntry("check:semantic-review", "Codex semantic review", "BLOCKED", ["Required semantic review is unavailable"], [detail])]),
  });
}

export function deriveReviewTarget(report) {
  const hasFail = report.entries.some((entry) => entry.result === "FAIL");
  const hasBlocked = report.entries.some((entry) => entry.result === "BLOCKED");
  if (hasFail || report.humanReviewRequired) return "review";
  if (hasBlocked) return "blocked";
  return "done";
}

export function sanitizeReviewReport(report, secrets = secretValues()) {
  return Object.freeze({
    version: 1,
    phase: "review",
    summary: sanitizeText(report.summary, secrets).slice(0, 2000),
    humanReviewRequired: Boolean(report.humanReviewRequired),
    humanReviewReasons: Object.freeze((report.humanReviewReasons || []).map((item) => sanitizeText(item, secrets).slice(0, 500))),
    entries: Object.freeze((report.entries || []).slice(0, MAX_ENTRIES).map((entry) => Object.freeze({
      source: entry.source,
      id: entry.id,
      label: sanitizeText(entry.label, secrets).slice(0, 500),
      result: entry.result,
      evidence: Object.freeze((entry.evidence || []).slice(0, 10).map((item) => sanitizeText(item, secrets).slice(0, 500))),
      remainingWork: Object.freeze((entry.remainingWork || []).slice(0, 10).map((item) => sanitizeText(item, secrets).slice(0, 500))),
    }))),
  });
}

export async function createReviewContext({ root, runId, issueTaskBody, checks, baseSha, changeName }) {
  assertLocal(/^[A-Za-z0-9._-]+$/.test(runId), "REVIEW_CONTEXT", "Review run id is unsafe");
  assertLocal(path.isAbsolute(root), "REVIEW_CONTEXT", "Review context root must be absolute");
  const parent = path.join(root, ".ai-local", "review");
  await mkdir(parent, { recursive: true, mode: 0o700 });
  const directory = await mkdtemp(path.join(parent, `${runId}-`));
  const issuePath = path.join(directory, "issue.md");
  const checksPath = path.join(directory, "checks.json");
  await writeFile(issuePath, issueTaskBody, { mode: 0o600, flag: "wx" });
  await writeFile(checksPath, `${JSON.stringify({ baseSha, changeName, checks }, null, 2)}\n`, { mode: 0o600, flag: "wx" });
  return Object.freeze({ directory, issuePath, checksPath });
}

export async function cleanupReviewContext(context) {
  if (context?.directory) await rm(context.directory, { recursive: true, force: true });
}
