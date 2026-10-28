import { readFile } from "node:fs/promises";

import { assertLocal, LocalRunError } from "./errors.mjs";

const EXACT_KEYS = ["version", "phase", "outcome", "summary", "verification"];

function validateResult(value, expectedPhase) {
  assertLocal(value && typeof value === "object" && !Array.isArray(value), "RESULT_FORMAT", "Agent result must be a JSON object");
  const keys = Object.keys(value).sort();
  assertLocal(keys.length === EXACT_KEYS.length && keys.every((key, index) => key === [...EXACT_KEYS].sort()[index]), "RESULT_AUTHORITY", "Agent result contains missing or unexpected fields");
  assertLocal(value.version === 1, "RESULT_VERSION", "Agent result version is unsupported");
  assertLocal(value.phase === expectedPhase, "RESULT_PHASE", `Agent result phase must be ${expectedPhase}`);
  const outcomes = expectedPhase === "plan" ? ["success", "clarification", "failure"] : ["success", "failure"];
  assertLocal(outcomes.includes(value.outcome), "RESULT_OUTCOME", `Invalid ${expectedPhase} outcome`);
  assertLocal(typeof value.summary === "string" && value.summary.trim().length > 0 && value.summary.length <= 2000, "RESULT_SUMMARY", "Agent result summary is invalid");
  assertLocal(Array.isArray(value.verification) && value.verification.length <= 20, "RESULT_VERIFICATION", "Agent result verification must be an array");
  assertLocal(value.verification.every((item) => typeof item === "string" && item.length > 0 && item.length <= 500), "RESULT_VERIFICATION", "Agent verification entries are invalid");
  if (value.outcome !== "success") assertLocal(value.verification.length === 0, "RESULT_VERIFICATION", "Non-success result cannot claim verification");
  return Object.freeze({ ...value, verification: Object.freeze([...value.verification]) });
}

export function parseAgentResult(text, expectedPhase) {
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw new LocalRunError("RESULT_JSON", "Agent final response is not valid JSON");
  }
  return validateResult(value, expectedPhase);
}

export async function readAgentResult(filePath, expectedPhase) {
  return parseAgentResult(await readFile(filePath, "utf8"), expectedPhase);
}
