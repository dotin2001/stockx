import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { addApplyTestEnvironment } from "./apply-environment.mjs";
import { readAgentResult } from "./contracts.mjs";
import { sanitizeText, secretValues } from "./errors.mjs";
import { runProcess, sanitizedChildEnvironment } from "./process.mjs";

export const CODEX_MODEL = "gpt-5.6-sol";

export function codexArguments({ worktree, schemaPath, resultPath }) {
  return [
    "exec",
    "--ephemeral",
    "--ignore-user-config",
    "--model", CODEX_MODEL,
    "--sandbox", "workspace-write",
    "--cd", worktree,
    "--output-schema", schemaPath,
    "--output-last-message", resultPath,
    "-",
  ];
}

export async function buildPrompt(promptPath, { changeName, taskContext = ".ai-local/context/task.md" }) {
  const source = await readFile(promptPath, "utf8");
  return source.replaceAll("{{CHANGE_NAME}}", changeName).replaceAll("{{TASK_CONTEXT}}", taskContext);
}

export async function runCodexStage({ root, worktree, phase, changeName, applyTestEnvironment = {}, commandRunner = runProcess, signal, onStderr }) {
  const promptPath = path.join(root, "automation", "ai-local", "prompts", `${phase}.md`);
  const schemaPath = path.join(root, "automation", "ai-local", "schemas", `${phase}-result.schema.json`);
  const resultDirectory = path.join(worktree, ".ai-local", "results");
  const resultPath = path.join(resultDirectory, `${phase}.json`);
  const githubConfigDirectory = path.join(worktree, ".ai-local", "no-github-auth");
  await mkdir(resultDirectory, { recursive: true, mode: 0o700 });
  await mkdir(githubConfigDirectory, { recursive: true, mode: 0o700 });
  const prompt = await buildPrompt(promptPath, { changeName });
  const childEnvironment = sanitizedChildEnvironment();
  if (phase === "implementation") addApplyTestEnvironment(childEnvironment, applyTestEnvironment);
  childEnvironment.GH_CONFIG_DIR = githubConfigDirectory;
  const runtimeSecrets = secretValues(childEnvironment);
  await commandRunner("codex", codexArguments({ worktree, schemaPath, resultPath }), {
    cwd: worktree,
    env: childEnvironment,
    stdin: prompt,
    signal,
    onStderr: onStderr ? (text) => onStderr(sanitizeText(text, runtimeSecrets)) : undefined,
  });
  const result = await readAgentResult(resultPath, phase);
  return Object.freeze({
    ...result,
    summary: sanitizeText(result.summary, runtimeSecrets),
    verification: Object.freeze(result.verification.map((item) => sanitizeText(item, runtimeSecrets))),
  });
}
