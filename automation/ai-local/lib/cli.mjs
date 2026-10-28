import { parseArgs } from "node:util";

import { LocalRunError } from "./errors.mjs";

export const USAGE = `Usage:
  npm run ai:local -- --task <repository-relative.md>
  npm run ai:local -- --task <repository-relative.md> --dry-run

Runs local OpenSpec planning and implementation in an isolated worktree and
leaves a validated, unstaged diff for human review. It never publishes to GitHub.`;

export function parseCliArgs(args) {
  if (args.length === 1 && (args[0] === "--help" || args[0] === "-h")) return { help: true, taskPath: null, dryRun: false };
  const taskFlags = args.filter((value) => value === "--task" || value.startsWith("--task=")).length;
  const dryFlags = args.filter((value) => value === "--dry-run").length;
  if (taskFlags !== 1 || dryFlags > 1) throw new LocalRunError("CLI_ARGUMENT", USAGE);
  let parsed;
  try {
    parsed = parseArgs({
      args,
      strict: true,
      allowPositionals: false,
      options: {
        task: { type: "string" },
        "dry-run": { type: "boolean", default: false },
        help: { type: "boolean", short: "h", default: false },
      },
    });
  } catch (error) {
    throw new LocalRunError("CLI_ARGUMENT", `${error.message}\n${USAGE}`);
  }
  if (parsed.values.help) return { help: true, taskPath: null, dryRun: false };
  if (!parsed.values.task?.trim()) throw new LocalRunError("CLI_ARGUMENT", USAGE);
  return { help: false, taskPath: parsed.values.task, dryRun: parsed.values["dry-run"] };
}
