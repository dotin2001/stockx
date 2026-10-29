import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { readAgentResult } from "./contracts.mjs";
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

export async function runCodexStage({ root, worktree, phase, changeName, commandRunner = runProcess, signal, onStderr }) {
  const promptPath = path.join(root, "automation", "ai-local", "prompts", `${phase}.md`);
  const schemaPath = path.join(root, "automation", "ai-local", "schemas", `${phase}-result.schema.json`);
  const resultDirectory = path.join(worktree, ".ai-local", "results");
  const resultPath = path.join(resultDirectory, `${phase}.json`);
  const githubConfigDirectory = path.join(worktree, ".ai-local", "no-github-auth");
  await mkdir(resultDirectory, { recursive: true, mode: 0o700 });
  await mkdir(githubConfigDirectory, { recursive: true, mode: 0o700 });
  const prompt = await buildPrompt(promptPath, { changeName });
  const childEnvironment = sanitizedChildEnvironment();
  childEnvironment.GH_CONFIG_DIR = githubConfigDirectory;
  await commandRunner("codex", codexArguments({ worktree, schemaPath, resultPath }), {
    cwd: worktree,
    env: childEnvironment,
    stdin: prompt,
    signal,
    onStderr,
  });
  return readAgentResult(resultPath, phase);
}
