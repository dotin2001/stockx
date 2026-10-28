import assert from "node:assert/strict";
import { mkdir, readFile, symlink, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { codexArguments } from "../../automation/ai-local/lib/codex.mjs";
import { parseCliArgs } from "../../automation/ai-local/lib/cli.mjs";
import { parseAgentResult } from "../../automation/ai-local/lib/contracts.mjs";
import { LocalRunError, sanitizeText } from "../../automation/ai-local/lib/errors.mjs";
import { inspectRepository, inspectTools, preflight } from "../../automation/ai-local/lib/preflight.mjs";
import { runProcess, sanitizedChildEnvironment } from "../../automation/ai-local/lib/process.mjs";
import { createRunId, initialRunRecord, updateRunRecord, writeRunRecord } from "../../automation/ai-local/lib/run-record.mjs";
import { resolveTaskFile, slugifyTitle } from "../../automation/ai-local/lib/task.mjs";
import { git, initRepository, tempDirectory } from "./support/helpers.mjs";

test("CLI accepts one task and optional dry run while rejecting unsupported shapes", () => {
  assert.deepEqual(parseCliArgs(["--task", "tasks/example.md"]), { help: false, taskPath: "tasks/example.md", dryRun: false });
  assert.deepEqual(parseCliArgs(["--task=tasks/example.md", "--dry-run"]), { help: false, taskPath: "tasks/example.md", dryRun: true });
  assert.equal(parseCliArgs(["--help"]).help, true);
  assert.throws(() => parseCliArgs([]), /Usage:/);
  assert.throws(() => parseCliArgs(["--task", "a.md", "--task", "b.md"]), /Usage:/);
  assert.throws(() => parseCliArgs(["--task", "a.md", "extra"]), /positional/i);
});

test("task intake derives bounded identity and rejects unsafe task files", async () => {
  const root = await tempDirectory();
  await mkdir(path.join(root, "tasks"));
  await writeFile(path.join(root, "tasks", "valid.md"), "# Add Better Search\n\nAcceptance criteria.\n");
  const task = await resolveTaskFile(root, "tasks/valid.md");
  assert.equal(task.changeName, "local-add-better-search");
  assert.equal(task.hash.length, 64);
  assert.equal(task.relativePath, "tasks/valid.md");
  assert.ok(`local-${slugifyTitle("x".repeat(200))}`.length <= 80);

  await writeFile(path.join(root, "tasks", "empty.md"), "");
  await writeFile(path.join(root, "tasks", "heading.md"), "Not a heading\n");
  await writeFile(path.join(root, "outside.md"), "# Outside\n");
  await symlink(path.join(root, "outside.md"), path.join(root, "tasks", "link.md"));
  await assert.rejects(() => resolveTaskFile(root, "tasks/empty.md"), /empty/);
  await assert.rejects(() => resolveTaskFile(root, "tasks/heading.md"), /first-level/);
  await assert.rejects(() => resolveTaskFile(root, "tasks/link.md"), /symbolic links/);
  await assert.rejects(() => resolveTaskFile(root, "../outside.md"), /inside the repository|does not exist/);
});

test("sanitizer and child environment redact secrets and omit GitHub credentials", () => {
  const secret = "sk-test-secret-1234567890";
  assert.doesNotMatch(sanitizeText(`api_key=${secret}`, [secret]), new RegExp(secret));
  const env = sanitizedChildEnvironment({
    PATH: "/bin",
    HOME: "/tmp/home",
    CODEX_API_KEY: secret,
    OPENAI_API_KEY: "must-not-pass",
    GITHUB_TOKEN: "must-not-pass",
    AI_PROJECT_TOKEN: "must-not-pass",
  });
  assert.equal(env.CODEX_API_KEY, secret);
  assert.equal(env.OPENAI_API_KEY, undefined);
  assert.equal(env.GITHUB_TOKEN, undefined);
  assert.equal(env.AI_PROJECT_TOKEN, undefined);
});

test("process execution reports non-zero exits, signals, and missing commands", async () => {
  await assert.rejects(() => runProcess(process.execPath, ["-e", "process.exit(7)"]), (error) => error.code === "COMMAND_FAILED");
  await assert.rejects(() => runProcess(process.execPath, ["-e", "process.kill(process.pid, 'SIGTERM')"]), (error) => error.code === "COMMAND_SIGNAL");
  await assert.rejects(() => runProcess("definitely-not-an-ai-local-command", []), (error) => error.code === "COMMAND_START");
});

test("agent result contracts reject malformed, extra, and phase-inconsistent output", () => {
  const valid = { version: 1, phase: "plan", outcome: "success", summary: "planned", verification: ["strict"] };
  assert.equal(parseAgentResult(JSON.stringify(valid), "plan").outcome, "success");
  assert.throws(() => parseAgentResult("not json", "plan"), /valid JSON/);
  assert.throws(() => parseAgentResult(JSON.stringify({ ...valid, command: "push" }), "plan"), /unexpected/);
  assert.throws(() => parseAgentResult(JSON.stringify({ ...valid, phase: "implementation" }), "plan"), /phase/);
  assert.throws(() => parseAgentResult(JSON.stringify({ ...valid, outcome: "clarification", verification: ["claimed"] }), "plan"), /cannot claim/);
  assert.throws(() => parseAgentResult(JSON.stringify({ ...valid, phase: "implementation", outcome: "clarification", verification: [] }), "implementation"), /outcome/);
});

test("Codex arguments are shell-free, ephemeral, workspace-write, structured, and non-dangerous", () => {
  const args = codexArguments({ worktree: "/tmp/work", schemaPath: "/repo/schema.json", resultPath: "/tmp/result.json" });
  assert.deepEqual(args.slice(0, 6), ["exec", "--ephemeral", "--ignore-user-config", "--sandbox", "workspace-write", "--cd"]);
  assert.ok(args.includes("--output-schema"));
  assert.ok(args.includes("--output-last-message"));
  assert.ok(args.includes("-"));
  assert.ok(!args.includes("danger-full-access"));
  assert.ok(!args.includes("--approve-for-me"));
});

test("run records are atomic allowlisted metadata without task bodies or credentials", async () => {
  const root = await tempDirectory();
  const task = { relativePath: "tasks/a.md", hash: "a".repeat(64), changeName: "local-a" };
  const runId = createRunId(new Date("2026-01-01T00:00:00Z"), task.hash);
  let record = initialRunRecord({ runId, task, baseSha: "b".repeat(40), branch: "main", tools: { node: "22", git: "git", openspec: "1.12.0", codex: "0.1" }, now: new Date("2026-01-01T00:00:00Z") });
  record = updateRunRecord(record, { outcome: "failure", error: "api_key=sk-test-123456789012345" });
  const relative = await writeRunRecord(root, record);
  const text = await readFile(path.join(root, relative), "utf8");
  assert.match(text, /local-a/);
  assert.doesNotMatch(text, /sk-test/);
  assert.doesNotMatch(text, /taskBody|environment|transcript/);
});

test("repository and tool preflight fail closed on dirty or incompatible state", async () => {
  const root = await initRepository();
  await writeFile(path.join(root, "dirty.txt"), "dirty\n");
  await assert.rejects(() => inspectRepository(root), /must be clean/);

  const detached = await initRepository();
  git(detached, ["switch", "--detach", "HEAD"]);
  await assert.rejects(() => inspectRepository(detached), (error) => error.code === "BRANCH_DETACHED");

  const fake = async (command, args) => {
    if (command === "openspec") return { stdout: "2.0.0\n", stderr: "" };
    if (command === "codex" && args[0] === "exec") return { stdout: "--ephemeral --sandbox --output-schema --output-last-message --ignore-user-config", stderr: "" };
    if (command === "codex" && args[0] === "login") return { stdout: "Logged in", stderr: "" };
    return { stdout: `${command} version\n`, stderr: "" };
  };
  await assert.rejects(() => inspectTools(root, fake, {}), /1\.12/);

  const flagsMissing = async (command, args) => {
    if (command === "openspec") return { stdout: "1.12.0\n", stderr: "" };
    if (command === "codex" && args[0] === "exec") return { stdout: "--ephemeral --sandbox", stderr: "" };
    if (command === "codex" && args[0] === "login") return { stdout: "Logged in", stderr: "" };
    return { stdout: `${command} version\n`, stderr: "" };
  };
  await assert.rejects(() => inspectTools(root, flagsMissing, {}), /required flag/);

  const authMissing = async (command, args) => {
    if (command === "openspec") return { stdout: "1.12.0\n", stderr: "" };
    if (command === "codex" && args[0] === "exec") return { stdout: "--ephemeral --sandbox --output-schema --output-last-message --ignore-user-config", stderr: "" };
    if (command === "codex" && args[0] === "login") return { stdout: "Not logged in", stderr: "" };
    return { stdout: `${command} version\n`, stderr: "" };
  };
  await assert.rejects(() => inspectTools(root, authMissing, {}), /not logged in/);
});

test("full preflight rejects an existing deterministic OpenSpec change before model use", async () => {
  const root = await initRepository();
  await mkdir(path.join(root, "tasks"));
  await writeFile(path.join(root, "tasks", "task.md"), "# Existing Change\n");
  await mkdir(path.join(root, "openspec", "changes", "local-existing-change"), { recursive: true });
  git(root, ["add", "."]);
  git(root, ["commit", "-m", "task and collision"]);
  await assert.rejects(() => preflight({ cwd: root, taskPath: "tasks/task.md" }), /already exists/);
});
