import { spawn } from "node:child_process";

import { LocalRunError, sanitizeText, secretValues } from "./errors.mjs";

const PASSTHROUGH_ENV = [
  "CODEX_ACCESS_TOKEN",
  "CODEX_API_KEY",
  "CODEX_HOME",
  "HOME",
  "HTTPS_PROXY",
  "HTTP_PROXY",
  "LANG",
  "LC_ALL",
  "LOGNAME",
  "NODE_EXTRA_CA_CERTS",
  "NO_COLOR",
  "NO_PROXY",
  "PATH",
  "SHELL",
  "SSL_CERT_DIR",
  "SSL_CERT_FILE",
  "TERM",
  "TMPDIR",
  "USER",
];

export function sanitizedChildEnvironment(source = process.env) {
  return Object.fromEntries(PASSTHROUGH_ENV.filter((key) => source[key] !== undefined).map((key) => [key, source[key]]));
}

export function runProcess(command, args = [], options = {}) {
  const {
    cwd = process.cwd(),
    env = sanitizedChildEnvironment(),
    stdin = null,
    signal,
    onStdout,
    onStderr,
    allowExitCodes = [0],
  } = options;
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawn(command, args, { cwd, env, shell: false, stdio: ["pipe", "pipe", "pipe"], signal });
    } catch (error) {
      reject(new LocalRunError("COMMAND_START", `Could not start ${command}: ${sanitizeText(error.message)}`));
      return;
    }
    const chunks = { stdout: [], stderr: [] };
    child.stdout.on("data", (chunk) => {
      chunks.stdout.push(chunk);
      onStdout?.(chunk.toString("utf8"));
    });
    child.stderr.on("data", (chunk) => {
      chunks.stderr.push(chunk);
      onStderr?.(chunk.toString("utf8"));
    });
    child.on("error", (error) => {
      const code = error.name === "AbortError" ? "COMMAND_ABORTED" : "COMMAND_START";
      reject(new LocalRunError(code, `${command} could not run: ${sanitizeText(error.message)}`));
    });
    child.on("close", (exitCode, exitSignal) => {
      const stdout = Buffer.concat(chunks.stdout).toString("utf8");
      const stderr = Buffer.concat(chunks.stderr).toString("utf8");
      if (allowExitCodes.includes(exitCode)) {
        resolve({ exitCode, signal: exitSignal, stdout, stderr });
        return;
      }
      const detail = sanitizeText(stderr || stdout, secretValues(env));
      reject(new LocalRunError(
        exitSignal ? "COMMAND_SIGNAL" : "COMMAND_FAILED",
        `${command} ${args.join(" ")} ${exitSignal ? `stopped by ${exitSignal}` : `failed (${exitCode})`}${detail ? `: ${detail}` : ""}`,
      ));
    });
    if (stdin === null || stdin === undefined) child.stdin.end();
    else child.stdin.end(stdin);
  });
}
