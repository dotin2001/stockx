import { mkdir, readFile, readdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";

import { assertLocal, LocalRunError, sanitizeText } from "./errors.mjs";

export function createRunId(now = new Date(), taskHash = "run") {
  return `${now.toISOString().replace(/[-:.]/g, "").replace("Z", "Z")}-${taskHash.slice(0, 10)}`;
}

export function recordSource(source) {
  if (source?.kind === "markdown") return { kind: "markdown", path: source.path };
  assertLocal(source?.kind === "github-issue", "RUN_SOURCE", "Task source is unsupported");
  return {
    kind: "github-issue",
    projectOwner: source.projectOwner,
    projectNumber: source.projectNumber,
    repository: source.repository,
    issueNumber: source.issueNumber,
    url: source.url,
    itemId: source.itemId,
    statusField: source.statusField || "Status",
    statusValue: source.statusValue || "Todo",
    doneStatus: source.doneStatus || "Done",
    reviewStatus: source.reviewStatus || "Review",
    blockedStatus: source.blockedStatus || "Blocked",
  };
}

export function initialRunRecord({ runId, task, baseSha, branch, tools, mode = "plan", parentPlanRunId = null, approvedPlanHash = null, now = new Date() }) {
  return {
    version: 3,
    runId,
    mode,
    source: recordSource(task.source),
    taskHash: task.hash,
    changeName: task.changeName,
    baseSha,
    branch,
    parentPlanRunId,
    approvedPlanHash,
    tools: { node: tools.node, git: tools.git, openspec: tools.openspec, codex: tools.codex },
    startedAt: now.toISOString(),
    updatedAt: now.toISOString(),
    phase: "preflight",
    outcome: "running",
    changedPaths: [],
    verification: [],
    reviewReport: null,
    statusSync: null,
  };
}

export function initialLinkedRunRecord({ runId, mode, parent, baseSha, branch, tools = {}, approvedPlanHash = null, completionBasis = null, now = new Date() }) {
  const task = { source: parent.source, hash: parent.taskHash, changeName: parent.changeName };
  const record = initialRunRecord({ runId, task, baseSha, branch, tools, mode, parentPlanRunId: parent.mode === "plan" ? parent.runId : parent.parentPlanRunId, approvedPlanHash, now });
  return completionBasis ? { ...record, completionBasis } : record;
}

export function updateRunRecord(record, updates, now = new Date()) {
  const next = { ...record, ...updates, updatedAt: now.toISOString() };
  if (next.error) next.error = sanitizeText(next.error);
  return next;
}

export async function writeRunRecord(root, record) {
  const directory = path.join(root, ".ai-local", "runs");
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const target = path.join(directory, `${record.runId}.json`);
  const temporary = `${target}.tmp-${process.pid}`;
  await writeFile(temporary, `${JSON.stringify(record, null, 2)}\n`, { mode: 0o600, flag: "w" });
  await rename(temporary, target);
  return path.relative(root, target).split(path.sep).join("/");
}

async function readRecords(root) {
  const directory = path.join(root, ".ai-local", "runs");
  let entries;
  try { entries = await readdir(directory, { withFileTypes: true }); } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
  const records = [];
  for (const entry of entries.filter((item) => item.isFile() && item.name.endsWith(".json"))) {
    let value;
    try { value = JSON.parse(await readFile(path.join(directory, entry.name), "utf8")); } catch {
      throw new LocalRunError("RUN_RECORD_INVALID", `Local run record is malformed: ${entry.name}`);
    }
    records.push(value);
  }
  return records;
}

function validChangeName(value) {
  return typeof value === "string" && value.length <= 80 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
}

function assertUsableRecord(record, expectedMode) {
  assertLocal(record?.version === 3 && record.mode === expectedMode && typeof record.runId === "string", "RUN_RECORD_INVALID", `Local ${expectedMode} record has an unsupported shape`);
  assertLocal(validChangeName(record.changeName) && /^[a-f0-9]{64}$/i.test(record.taskHash || "") && /^[a-f0-9]{40}$/i.test(record.baseSha || ""), "RUN_RECORD_INVALID", `Local ${expectedMode} record identity is invalid`);
  recordSource(record.source);
  return record;
}

export async function findSuccessfulPlanRecord(root, changeName) {
  assertLocal(validChangeName(changeName), "CHANGE_NAME", "Apply requires a safe kebab-case change name");
  const matches = (await readRecords(root)).filter((record) => record?.version === 3 && record.mode === "plan" && record.changeName === changeName && record.phase === "complete" && record.outcome === "success");
  assertLocal(matches.length > 0, "PLAN_RECORD_MISSING", `No successful local plan record exists for ${changeName}`);
  assertLocal(matches.length === 1, "PLAN_RECORD_AMBIGUOUS", `Multiple successful local plan records exist for ${changeName}`);
  return Object.freeze(assertUsableRecord(matches[0], "plan"));
}

export async function findPendingStatusRecord(root, changeName) {
  assertLocal(validChangeName(changeName), "CHANGE_NAME", "Status sync requires a safe kebab-case change name");
  const matches = (await readRecords(root)).filter((record) => record?.version === 3 && record.changeName === changeName && record.statusSync?.state === "pending" && ["done", "review", "blocked"].includes(record.statusSync.target));
  assertLocal(matches.length > 0, "STATUS_SYNC_MISSING", `No pending Project status update exists for ${changeName}`);
  assertLocal(matches.length === 1, "STATUS_SYNC_AMBIGUOUS", `Multiple pending Project status updates exist for ${changeName}`);
  assertLocal(matches[0].source?.kind === "github-issue", "STATUS_SYNC_SOURCE", "Pending status update is not GitHub-backed");
  return Object.freeze(matches[0]);
}

export async function findStatusSyncDiagnosticRecord(root, changeName) {
  if (!validChangeName(changeName)) return null;
  const matches = (await readRecords(root)).filter((record) => record?.version === 3 && record.changeName === changeName && ["plan", "apply", "sync-status"].includes(record.mode));
  matches.sort((left, right) => String(right.updatedAt || right.startedAt || "").localeCompare(String(left.updatedAt || left.startedAt || "")));
  for (const record of matches) {
    try { return Object.freeze(assertUsableRecord(record, record.mode)); } catch { /* Try another record only for refusal provenance. */ }
  }
  return null;
}

function terminalIdentity(record) {
  const source = recordSource(record.source);
  return JSON.stringify({
    source,
    target: record.statusSync?.target,
    value: record.statusSync?.value,
    approvedPlanHash: record.approvedPlanHash || null,
  });
}

function assertTerminalRecord(record) {
  assertLocal(["plan", "apply", "sync-status"].includes(record?.mode), "RUN_RECORD_INVALID", "Local terminal status record has an unsupported mode");
  assertUsableRecord(record, record.mode);
  assertLocal(record.source?.kind === "github-issue", "STATUS_SYNC_SOURCE", "Terminal status update is not GitHub-backed");
  assertLocal(["done", "review", "blocked"].includes(record.statusSync?.target), "RUN_RECORD_INVALID", "Terminal status target is invalid");
  return record;
}

export async function findStatusSyncEvidence(root, changeName) {
  assertLocal(validChangeName(changeName), "CHANGE_NAME", "Status sync requires a safe kebab-case change name");
  const records = await readRecords(root);
  const pending = records.filter((record) => record?.version === 3 && record.changeName === changeName && record.statusSync?.state === "pending" && ["done", "review", "blocked"].includes(record.statusSync.target));
  assertLocal(pending.length <= 1, "STATUS_SYNC_AMBIGUOUS", `Multiple pending Project status updates exist for ${changeName}`);
  if (pending.length === 1) return Object.freeze({ kind: "pending", record: Object.freeze(assertTerminalRecord(pending[0])) });

  const reviewProducedBlocked = records.filter((record) => record?.version === 3 && record.changeName === changeName && record.statusSync?.state === "synchronized" && record.statusSync.target === "blocked" && record.reviewReport);
  reviewProducedBlocked.forEach(assertTerminalRecord);
  const synchronized = records.filter((record) => record?.version === 3 && record.changeName === changeName && record.statusSync?.state === "synchronized" && ["done", "blocked"].includes(record.statusSync.target) && !(record.statusSync.target === "blocked" && record.reviewReport));
  if (synchronized.length > 0) {
    synchronized.forEach(assertTerminalRecord);
    assertLocal(new Set(synchronized.map(terminalIdentity)).size === 1, "STATUS_SYNC_AMBIGUOUS", `Conflicting synchronized Project status updates exist for ${changeName}`);
    synchronized.sort((left, right) => String(right.updatedAt || right.startedAt || "").localeCompare(String(left.updatedAt || left.startedAt || "")));
    return Object.freeze({ kind: "synchronized", record: Object.freeze(synchronized[0]) });
  }

  const plan = await findSuccessfulPlanRecord(root, changeName);
  assertLocal(plan.source?.kind === "github-issue", "STATUS_SYNC_SOURCE", "Status sync requires a GitHub-backed plan");
  const allowBlockedCurrent = reviewProducedBlocked.some((record) => record.source?.itemId === plan.source.itemId && (record.parentPlanRunId === plan.runId || record.runId === plan.runId));
  return Object.freeze({ kind: "plan", record: plan, allowBlockedCurrent });
}
