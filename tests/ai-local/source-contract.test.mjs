import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("local runner permits one narrow Project status mutation but no publication or unsafe Codex authority", async () => {
  const [entry, runner, codex, processSource, githubSource] = await Promise.all([
    readFile("bin/ai-local.mjs", "utf8"),
    readFile("automation/ai-local/lib/runner.mjs", "utf8"),
    readFile("automation/ai-local/lib/codex.mjs", "utf8"),
    readFile("automation/ai-local/lib/process.mjs", "utf8"),
    readFile("automation/ai-local/lib/github-project.mjs", "utf8"),
  ]);
  const executable = `${entry}\n${runner}\n${codex}\n${githubSource}`;
  assert.match(githubSource, /"project", "view"/);
  assert.match(githubSource, /"api", "graphql"/);
  assert.match(githubSource, /"project", "item-edit"/);
  assert.match(githubSource, /--single-select-option-id/);
  assert.doesNotMatch(executable, /gh\s+pr|githubRest|graphqlRequest|AI_PROJECT_TOKEN|GITHUB_TOKEN|git", \["(?:commit|push)/);
  assert.doesNotMatch(githubSource, /"project",\s*"(?:item-(?:delete|create)|close|copy|edit|delete)"/);
  assert.doesNotMatch(githubSource, /"issue",\s*"(?:edit|comment|close|reopen|delete|create)"/);
  assert.doesNotMatch(githubSource, /"pr",\s*"(?:create|merge|review|close|edit)"/);
  assert.doesNotMatch(githubSource, /"workflow",\s*"run"|\.github\/workflows/);
  assert.doesNotMatch(codex, /danger-full-access|approve-for-me|bypass-approvals/);
  assert.match(codex, /workspace-write/);
  assert.match(codex, /--ephemeral/);
  assert.match(codex, /--model/);
  assert.match(codex, /CODEX_MODEL = "gpt-5\.6-sol"/);
  assert.match(processSource, /CODEX_API_KEY/);
  assert.doesNotMatch(processSource.match(/const PASSTHROUGH_ENV = \[[\s\S]*?\];/)?.[0] || "", /GITHUB_TOKEN|AI_PROJECT_TOKEN|OPENAI_API_KEY/);
  assert.doesNotMatch(githubSource.match(/const GITHUB_ENV_KEYS = \[[\s\S]*?\];/)?.[0] || "", /GITHUB_TOKEN|GH_TOKEN|AI_PROJECT_TOKEN|CODEX_API_KEY|CODEX_ACCESS_TOKEN/);
});

test("trusted prompts preserve plan/apply separation and forbid publication", async () => {
  const [plan, implementation] = await Promise.all([
    readFile("automation/ai-local/prompts/plan.md", "utf8"),
    readFile("automation/ai-local/prompts/implementation.md", "utf8"),
  ]);
  for (const required of ["AGENTS.md", "openspec-propose", "{{CHANGE_NAME}}", "untrusted", "--strict", "outside"]) assert.match(plan, new RegExp(required.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));
  for (const required of ["AGENTS.md", "openspec-apply-change", "source of truth", "truthful", "Do not", "push", "GitHub"]) assert.match(implementation, new RegExp(required, "i"));
});

test("package scripts expose the local runner as the only AI delivery command", async () => {
  const pkg = JSON.parse(await readFile("package.json", "utf8"));
  assert.equal(pkg.scripts["ai:local"], "node ./bin/ai-local.mjs");
  assert.equal(pkg.scripts["ai:local:test"], "node --test tests/ai-local/*.test.mjs");
  assert.equal(pkg.scripts["ai:workflow:test"], undefined);
  assert.ok(pkg.scripts.test.includes("tests/ai-local/*.test.mjs"));
  assert.ok(!pkg.scripts.test.includes("tests/ai-workflow"));
  assert.equal(pkg.bin["ai-local"], "./bin/ai-local.mjs");
});

test("operator documentation matches the two-stage CLI contract", async () => {
  const [cli, guide, agents] = await Promise.all([
    readFile("automation/ai-local/lib/cli.mjs", "utf8"),
    readFile("docs/ai-local-openspec.md", "utf8"),
    readFile("AGENTS.md", "utf8"),
  ]);
  for (const command of ["--apply <change-name>", "--sync-status <change-name>"]) {
    assert.match(cli, new RegExp(command.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.match(guide, new RegExp(command.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.match(agents, new RegExp(command.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(guide, /Implementation did not run|does not run implementation/i);
  assert.match(guide, /technical failures leave/i);
  assert.doesNotMatch(guide, /Project mode is read-only|operator updates Project status manually/i);
});
