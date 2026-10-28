import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("local runner has no GitHub publication or unsafe Codex authority", async () => {
  const [entry, runner, codex, processSource] = await Promise.all([
    readFile("bin/ai-local.mjs", "utf8"),
    readFile("automation/ai-local/lib/runner.mjs", "utf8"),
    readFile("automation/ai-local/lib/codex.mjs", "utf8"),
    readFile("automation/ai-local/lib/process.mjs", "utf8"),
  ]);
  const executable = `${entry}\n${runner}\n${codex}`;
  assert.doesNotMatch(executable, /gh\s+pr|githubRest|graphqlRequest|AI_PROJECT_TOKEN|GITHUB_TOKEN|git", \["(?:commit|push)/);
  assert.doesNotMatch(codex, /danger-full-access|approve-for-me|bypass-approvals/);
  assert.match(codex, /workspace-write/);
  assert.match(codex, /--ephemeral/);
  assert.match(processSource, /CODEX_API_KEY/);
  assert.doesNotMatch(processSource.match(/const PASSTHROUGH_ENV = \[[\s\S]*?\];/)?.[0] || "", /GITHUB_TOKEN|AI_PROJECT_TOKEN|OPENAI_API_KEY/);
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
