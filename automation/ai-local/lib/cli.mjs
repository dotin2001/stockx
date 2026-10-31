import { parseArgs } from "node:util";

import { assertLocal, LocalRunError } from "./errors.mjs";

export const USAGE = `Usage:
  npm run ai:local -- --task <repository-relative.md> [--dry-run]
  npm run ai:local -- --project-owner <login> --project-number <number> [--status-field Status] [--status-value Todo] [--done-status Done] [--blocked-status Blocked] [--issue <owner/repo#number>] [--dry-run]
  npm run ai:local -- --apply <change-name> [--dry-run]
  npm run ai:local -- --sync-status <change-name>

Task and Project intake create and validate an OpenSpec plan, leave only that
plan unstaged for review, and stop. --apply explicitly approves one reviewed
plan and runs implementation. For a GitHub-backed plan, a successful apply
moves only the selected Project item to Done and a structured task blocker
moves it to Blocked. --sync-status first retries a recorded pending update;
otherwise it verifies a completed unstaged $openspec-apply-change implementation
against its successful GitHub-backed plan and moves the recorded item to Done.`;

const OPTION_NAMES = [
  "task", "project-owner", "project-number", "status-field", "status-value", "done-status",
  "blocked-status", "issue", "apply", "sync-status", "dry-run", "help",
];

function flagCount(args, name) {
  const long = `--${name}`;
  return args.filter((value) => value === long || value.startsWith(`${long}=`)).length;
}

function fail(message = USAGE) {
  throw new LocalRunError("CLI_ARGUMENT", message === USAGE ? USAGE : `${message}\n${USAGE}`);
}

function parseChangeName(value, option) {
  const name = value?.trim();
  if (!name) fail(`${option} requires a change name.`);
  assertLocal(name.length <= 80 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name), "CLI_ARGUMENT", `${option} must be a safe kebab-case change name.\n${USAGE}`);
  return name;
}

export function parseCliArgs(args, { isTTY = Boolean(process.stdin.isTTY) } = {}) {
  if (args.length === 1 && (args[0] === "--help" || args[0] === "-h")) {
    return { help: true, mode: null, taskPath: null, project: null, changeName: null, dryRun: false };
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
        "done-status": { type: "string" },
        "blocked-status": { type: "string" },
        issue: { type: "string" },
        apply: { type: "string" },
        "sync-status": { type: "string" },
        "dry-run": { type: "boolean", default: false },
        help: { type: "boolean", short: "h", default: false },
      },
    });
  } catch (error) {
    fail(error.message);
  }

  if (parsed.values.help) return { help: true, mode: null, taskPath: null, project: null, changeName: null, dryRun: false };

  const applyValue = parsed.values.apply;
  const syncValue = parsed.values["sync-status"];
  const intakeValues = [
    parsed.values.task, parsed.values["project-owner"], parsed.values["project-number"],
    parsed.values["status-field"], parsed.values["status-value"], parsed.values["done-status"],
    parsed.values["blocked-status"], parsed.values.issue,
  ];
  const hasIntake = intakeValues.some((value) => value !== undefined);
  if (applyValue !== undefined || syncValue !== undefined) {
    if (hasIntake || (applyValue !== undefined && syncValue !== undefined)) fail("Plan intake, --apply, and --sync-status are mutually exclusive.");
    if (syncValue !== undefined && parsed.values["dry-run"]) fail("--sync-status does not accept --dry-run.");
    const mode = applyValue !== undefined ? "apply" : "sync-status";
    return {
      help: false,
      mode,
      taskPath: null,
      project: null,
      changeName: parseChangeName(applyValue ?? syncValue, mode === "apply" ? "--apply" : "--sync-status"),
      dryRun: parsed.values["dry-run"],
    };
  }

  const taskPath = parsed.values.task?.trim();
  const owner = parsed.values["project-owner"]?.trim();
  const projectNumberText = parsed.values["project-number"]?.trim();
  const hasProjectOption = intakeValues.slice(1).some((value) => value !== undefined);
  if (taskPath && hasProjectOption) fail("Markdown and GitHub Project intake options are mutually exclusive.");
  if (taskPath) return { help: false, mode: "plan", taskPath, project: null, changeName: null, dryRun: parsed.values["dry-run"] };

  if (!owner || !projectNumberText) fail("Project mode requires both --project-owner and --project-number.");
  assertLocal(/^\d+$/.test(projectNumberText) && Number(projectNumberText) > 0, "CLI_ARGUMENT", `Project number must be a positive integer.\n${USAGE}`);
  const values = {
    statusField: parsed.values["status-field"]?.trim() || "Status",
    statusValue: parsed.values["status-value"]?.trim() || "Todo",
    doneStatus: parsed.values["done-status"]?.trim() || "Done",
    blockedStatus: parsed.values["blocked-status"]?.trim() || "Blocked",
    issueSelector: parsed.values.issue?.trim() || null,
  };
  for (const [option, raw] of [["status-field", parsed.values["status-field"]], ["status-value", parsed.values["status-value"]], ["done-status", parsed.values["done-status"]], ["blocked-status", parsed.values["blocked-status"]]]) {
    if (raw !== undefined && !raw.trim()) fail(`--${option} cannot be empty.`);
  }
  if (parsed.values.issue !== undefined && !parsed.values.issue.trim()) fail("Issue selector cannot be empty.");
  if (new Set([values.statusValue, values.doneStatus, values.blockedStatus]).size !== 3) fail("Todo, Done, and Blocked status values must be distinct.");
  if (!isTTY && !values.issueSelector) fail("Non-interactive Project mode requires --issue <owner/repo#number>.");

  return {
    help: false,
    mode: "plan",
    taskPath: null,
    project: Object.freeze({ owner, number: Number(projectNumberText), ...values, isTTY }),
    changeName: null,
    dryRun: parsed.values["dry-run"],
  };
}
