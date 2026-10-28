import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";

import { sanitizeText } from "./errors.mjs";

export function createRunId(now = new Date(), taskHash = "run") {
  return `${now.toISOString().replace(/[-:.]/g, "").replace("Z", "Z")}-${taskHash.slice(0, 10)}`;
}

export function initialRunRecord({ runId, task, baseSha, branch, tools, now = new Date() }) {
  return {
    version: 1,
    runId,
    taskPath: task.relativePath,
    taskHash: task.hash,
    changeName: task.changeName,
    baseSha,
    branch,
    tools: { node: tools.node, git: tools.git, openspec: tools.openspec, codex: tools.codex },
    startedAt: now.toISOString(),
    updatedAt: now.toISOString(),
    phase: "preflight",
    outcome: "running",
    changedPaths: [],
    verification: [],
  };
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
