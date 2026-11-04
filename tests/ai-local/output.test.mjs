import assert from "node:assert/strict";
import test from "node:test";

import { formatStatusSync } from "../../automation/ai-local/lib/output.mjs";
import { sanitizeHostChecks } from "../../automation/ai-local/lib/review.mjs";

function check(result, secret) {
  return {
    source: "check",
    id: `check:${result.toLowerCase()}`,
    label: `${result.toLowerCase()} check`,
    result,
    evidence: [`result contained ${secret}`],
    remainingWork: result === "PASS" ? [] : [`resolve ${secret}`],
  };
}

for (const scenario of [
  { result: "PASS", derivedTarget: "done", status: "Done" },
  { result: "FAIL", derivedTarget: "review", status: "Review" },
  { result: "BLOCKED", derivedTarget: "blocked", status: "Blocked" },
]) {
  test(`status-sync output reports bounded sanitized ${scenario.result} host evidence`, () => {
    const secret = "sentinel-output-secret";
    const hostChecks = sanitizeHostChecks([check(scenario.result, secret)], [secret]);
    const output = formatStatusSync({
      changeName: "local-pilot",
      status: scenario.status,
      recordPath: ".ai-local/runs/run.json",
      completionBasis: "trusted-host-verification",
      hostChecks,
      derivedTarget: scenario.derivedTarget,
      effectiveTarget: scenario.derivedTarget,
    });
    assert.match(output, /Completion basis: trusted-host-verification/);
    assert.match(output, new RegExp(`\\[${scenario.result}\\]`));
    assert.doesNotMatch(output, /Requirement results|Review summary|sentinel-output-secret/);
    if (scenario.result !== "PASS") assert.match(output, /Remaining: resolve \[REDACTED\]/);
    assert.ok(output.length < 4000);
  });
}
