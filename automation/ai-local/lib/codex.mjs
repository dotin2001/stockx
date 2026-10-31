import { mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";

import { addApplyTestEnvironment } from "./apply-environment.mjs";
import { readAgentResult, readReviewResult } from "./contracts.mjs";
import { sanitizeText, secretValues } from "./errors.mjs";
import { runProcess, sanitizedChildEnvironment } from "./process.mjs";

export const CODEX_MODEL = "gpt-5.6-sol";

export function codexArguments({ worktree, schemaPath, resultPath, phase = "implementation" }) {
  return [
    "exec",
    "--ephemeral",
    "--ignore-user-config",
    "--model", CODEX_MODEL,
    "--sandbox", phase === "review" ? "read-only" : "workspace-write",
    "--cd", worktree,
    "--output-schema", schemaPath,
    "--output-last-message", resultPath,
    "-",
  ];
}

export async function buildPrompt(promptPath, { changeName, taskContext = ".ai-local/context/task.md", issueContext = "", checksContext = "", baseSha = "" }) {
  const source = await readFile(promptPath, "utf8");
  return source
    .replaceAll("{{CHANGE_NAME}}", changeName)
    .replaceAll("{{TASK_CONTEXT}}", taskContext)
    .replaceAll("{{ISSUE_CONTEXT}}", issueContext)
    .replaceAll("{{CHECKS_CONTEXT}}", checksContext)
    .replaceAll("{{BASE_SHA}}", baseSha);
}

export async function runCodexStage({ root, worktree, phase, changeName, applyTestEnvironment = {}, reviewContext = null, reviewInventory = [], baseSha = "", commandRunner = runProcess, signal, onStderr }) {
  const promptPath = path.join(root, "automation", "ai-local", "prompts", `${phase}.md`);
  const schemaPath = path.join(root, "automation", "ai-local", "schemas", `${phase}-result.schema.json`);
  const resultDirectory = path.join(worktree, ".ai-local", "results");
  const resultPath = path.join(resultDirectory, `${phase}.json`);
  const githubConfigDirectory = path.join(worktree, ".ai-local", "no-github-auth");
  const isolatedHomeDirectory = path.join(worktree, ".ai-local", "no-user-home");
  await mkdir(resultDirectory, { recursive: true, mode: 0o700 });
  await mkdir(githubConfigDirectory, { recursive: true, mode: 0o700 });
  await mkdir(isolatedHomeDirectory, { recursive: true, mode: 0o700 });
  const prompt = await buildPrompt(promptPath, {
    changeName,
    issueContext: reviewContext?.issuePath || "",
    checksContext: reviewContext?.checksPath || "",
    baseSha,
  });
  const childEnvironment = sanitizedChildEnvironment();
  if (phase === "implementation") addApplyTestEnvironment(childEnvironment, applyTestEnvironment);
  const codexHome = childEnvironment.CODEX_HOME || (childEnvironment.HOME ? path.join(childEnvironment.HOME, ".codex") : null);
  childEnvironment.HOME = isolatedHomeDirectory;
  if (codexHome) childEnvironment.CODEX_HOME = codexHome;
  childEnvironment.GH_CONFIG_DIR = githubConfigDirectory;
  const runtimeSecrets = secretValues(childEnvironment);
  const invoke = () => commandRunner("codex", codexArguments({ worktree, schemaPath, resultPath, phase }), {
    cwd: worktree,
    env: childEnvironment,
    stdin: prompt,
    signal,
    onStderr: onStderr ? (text) => onStderr(sanitizeText(text, runtimeSecrets)) : undefined,
  });
  if (phase === "review") {
    try {
      await invoke();
      return await readReviewResult(resultPath, reviewInventory);
    } finally {
      await rm(resultPath, { force: true });
    }
  }
  await invoke();
  const result = await readAgentResult(resultPath, phase);
  return Object.freeze({
    ...result,
    summary: sanitizeText(result.summary, runtimeSecrets),
    verification: Object.freeze(result.verification.map((item) => sanitizeText(item, runtimeSecrets))),
  });
}
