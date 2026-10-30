const SECRET_ENV_KEYS = [
  "AI_PROJECT_TOKEN",
  "CODEX_ACCESS_TOKEN",
  "CODEX_API_KEY",
  "GH_ENTERPRISE_TOKEN",
  "GH_TOKEN",
  "GITHUB_TOKEN",
  "OPENAI_API_KEY",
  "TEST_POSTGRES_DATABASE_URL",
];

export class LocalRunError extends Error {
  constructor(code, message, options = {}) {
    super(String(message), options);
    this.name = "LocalRunError";
    this.code = code;
  }
}

export function assertLocal(condition, code, message) {
  if (!condition) throw new LocalRunError(code, message);
}

export function secretValues(env = process.env) {
  return SECRET_ENV_KEYS.map((key) => env[key]).filter((value) => typeof value === "string" && value.length >= 4);
}

export function sanitizeText(value, secrets = secretValues()) {
  let text = String(value ?? "");
  for (const secret of secrets) text = text.split(secret).join("[REDACTED]");
  text = text
    .replace(/\b(?:sk|sess|pat|ghp|github_pat|codex)[-_][A-Za-z0-9_-]{12,}\b/gi, "[REDACTED]")
    .replace(/(authorization\s*:\s*(?:bearer|token)\s+)[^\s]+/gi, "$1[REDACTED]")
    .replace(/((?:api[-_ ]?key|access[-_ ]?token|password)\s*[=:]\s*)[^\s,;]+/gi, "$1[REDACTED]");
  return text.slice(0, 4000);
}

export function asLocalError(error, code = "LOCAL_RUN_FAILED") {
  if (error instanceof LocalRunError) return error;
  return new LocalRunError(code, sanitizeText(error?.message || error), { cause: error });
}
