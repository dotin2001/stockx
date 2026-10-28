import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { readAgentResult } from "./contracts.mjs";
import { runProcess, sanitizedChildEnvironment } from "./process.mjs";

export function codexArguments({ worktree, schemaPath, resultPath }) {
  return [
    "exec",
    "--ephemeral",
    "--ignore-user-config",
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
  await mkdir(resultDirectory, { recursive: true, mode: 0o700 });
  const prompt = await buildPrompt(promptPath, { changeName });
  await commandRunner("codex", codexArguments({ worktree, schemaPath, resultPath }), {
    cwd: worktree,
    env: sanitizedChildEnvironment(),
    stdin: prompt,
    signal,
    onStderr,
  });
  return readAgentResult(resultPath, phase);
}
