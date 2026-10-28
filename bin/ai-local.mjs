#!/usr/bin/env node

import { realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { parseCliArgs, USAGE } from "../automation/ai-local/lib/cli.mjs";
import { asLocalError, sanitizeText } from "../automation/ai-local/lib/errors.mjs";
import { createIo } from "../automation/ai-local/lib/output.mjs";
import { runLocalWorkflow } from "../automation/ai-local/lib/runner.mjs";

export async function main(args = process.argv.slice(2), options = {}) {
  const io = options.io || createIo();
  try {
    const parsed = parseCliArgs(args);
    if (parsed.help) {
      io.info(USAGE);
      return 0;
    }
    const controller = new AbortController();
    const abort = () => controller.abort();
    process.once("SIGINT", abort);
    process.once("SIGTERM", abort);
    try {
      await runLocalWorkflow({
        cwd: options.cwd || process.cwd(),
        taskPath: parsed.taskPath,
        dryRun: parsed.dryRun,
        io,
        signal: controller.signal,
        dependencies: options.dependencies,
      });
    } finally {
      process.off("SIGINT", abort);
      process.off("SIGTERM", abort);
    }
    return 0;
  } catch (error) {
    const localError = asLocalError(error);
    io.error(`[${localError.code}] ${sanitizeText(localError.message)}`);
    return localError.code === "PLAN_CLARIFICATION" ? 2 : 1;
  }
}

const invoked = process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
if (invoked) process.exitCode = await main();
