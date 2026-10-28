import { parseArgs } from "node:util";

import { assertLocal, LocalRunError } from "./errors.mjs";

export const USAGE = `Usage:
  npm run ai:local -- --task <repository-relative.md> [--dry-run]
  npm run ai:local -- --project-owner <login> --project-number <number> [--status-field Status] [--status-value Todo] [--issue <owner/repo#number>] [--dry-run]

Runs local OpenSpec planning and implementation in an isolated worktree and
leaves a validated, unstaged diff for human review. Project mode reads GitHub
only; it never changes Project or issue state and never publishes changes.`;

const OPTION_NAMES = [
  "task", "project-owner", "project-number", "status-field", "status-value", "issue", "dry-run", "help",
];

function flagCount(args, name) {
  const long = `--${name}`;
  return args.filter((value) => value === long || value.startsWith(`${long}=`)).length;
}

function fail(message = USAGE) {
  throw new LocalRunError("CLI_ARGUMENT", message === USAGE ? USAGE : `${message}\n${USAGE}`);
}

export function parseCliArgs(args, { isTTY = Boolean(process.stdin.isTTY) } = {}) {
  if (args.length === 1 && (args[0] === "--help" || args[0] === "-h")) {
    return { help: true, mode: null, taskPath: null, project: null, dryRun: false };
  }
  for (const name of OPTION_NAMES) {
    if (flagCount(args, name) > 1) fail(`Option --${name} may be supplied only once.`);
  }

  let parsed;
  try {
    parsed = parseArgs({
      args,
      strict: true,
      allowPositionals: false,
      options: {
        task: { type: "string" },
        "project-owner": { type: "string" },
        "project-number": { type: "string" },
        "status-field": { type: "string" },
        "status-value": { type: "string" },
        issue: { type: "string" },
        "dry-run": { type: "boolean", default: false },
        help: { type: "boolean", short: "h", default: false },
      },
    });
  } catch (error) {
    fail(error.message);
  }

  if (parsed.values.help) return { help: true, mode: null, taskPath: null, project: null, dryRun: false };
  const taskPath = parsed.values.task?.trim();
  const owner = parsed.values["project-owner"]?.trim();
  const projectNumberText = parsed.values["project-number"]?.trim();
  const hasProjectOption = [owner, projectNumberText, parsed.values["status-field"], parsed.values["status-value"], parsed.values.issue]
    .some((value) => value !== undefined);

  if (taskPath && hasProjectOption) fail("Markdown and GitHub Project intake options are mutually exclusive.");
  if (taskPath) {
    return { help: false, mode: "task", taskPath, project: null, dryRun: parsed.values["dry-run"] };
  }

  if (!owner || !projectNumberText) fail("Project mode requires both --project-owner and --project-number.");
  assertLocal(/^\d+$/.test(projectNumberText) && Number(projectNumberText) > 0, "CLI_ARGUMENT", `Project number must be a positive integer.\n${USAGE}`);
  const rawStatusField = parsed.values["status-field"];
  const rawStatusValue = parsed.values["status-value"];
  const rawIssueSelector = parsed.values.issue;
  if (rawStatusField !== undefined && !rawStatusField.trim()) fail("Status field and value cannot be empty.");
  if (rawStatusValue !== undefined && !rawStatusValue.trim()) fail("Status field and value cannot be empty.");
  if (rawIssueSelector !== undefined && !rawIssueSelector.trim()) fail("Issue selector cannot be empty.");
  const statusField = rawStatusField?.trim() || "Status";
  const statusValue = rawStatusValue?.trim() || "Todo";
  const issueSelector = rawIssueSelector?.trim() || null;
  if (!isTTY && !issueSelector) fail("Non-interactive Project mode requires --issue <owner/repo#number>.");

  return {
    help: false,
    mode: "project",
    taskPath: null,
    project: Object.freeze({ owner, number: Number(projectNumberText), statusField, statusValue, issueSelector, isTTY }),
    dryRun: parsed.values["dry-run"],
  };
}
