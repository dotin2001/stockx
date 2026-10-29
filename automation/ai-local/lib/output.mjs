export function createIo(stdout = process.stdout, stderr = process.stderr) {
  return {
    info(message = "") { stdout.write(`${message}\n`); },
    error(message = "") { stderr.write(`${message}\n`); },
    phase(name, detail = "") { stdout.write(`\n[ai-local:${name}]${detail ? ` ${detail}` : ""}\n`); },
  };
}

export function formatSuccess({ changeName, sourceLabel, paths, verification, recordPath }) {
  return [
    `Local OpenSpec run complete: ${changeName}`,
    `Source: ${sourceLabel}`,
    `Changed paths (${paths.length}):`,
    ...paths.map((filePath) => `  - ${filePath}`),
    `Verification: ${verification.length ? verification.join(", ") : "strict OpenSpec validation"}`,
    `Run record: ${recordPath}`,
    "Review with `git diff` and rerun the reported checks before committing or discarding these unstaged changes.",
  ].join("\n");
}

export function formatPlanReady({ changeName, sourceLabel, paths, recordPath }) {
  return [
    `OpenSpec plan ready for review: ${changeName}`,
    `Source: ${sourceLabel}`,
    `Planning paths (${paths.length}):`,
    ...paths.map((filePath) => `  - ${filePath}`),
    "Implementation did not run. GitHub Project status did not change.",
    `Approve and apply with: npm run ai:local -- --apply ${changeName}`,
    `Run record: ${recordPath}`,
  ].join("\n");
}

export function formatApplySuccess({ changeName, sourceLabel, paths, verification, recordPath, projectStatus = null }) {
  return [
    `Approved OpenSpec implementation complete: ${changeName}`,
    `Source: ${sourceLabel}`,
    `Changed paths (${paths.length}):`,
    ...paths.map((filePath) => `  - ${filePath}`),
    `Verification: ${verification.join(", ")}`,
    ...(projectStatus ? [`GitHub Project status: ${projectStatus}`] : []),
    `Run record: ${recordPath}`,
    "Review the unstaged implementation with `git diff` before committing.",
  ].join("\n");
}

export function formatBlocked({ changeName, sourceLabel, summary, recordPath, projectStatus = null }) {
  return [
    `OpenSpec implementation blocked: ${changeName}`,
    `Source: ${sourceLabel}`,
    `Blocker: ${summary}`,
    ...(projectStatus ? [`GitHub Project status: ${projectStatus}`] : []),
    "No implementation patch was applied.",
    `Run record: ${recordPath}`,
  ].join("\n");
}

export function formatStatusSync({ changeName, status, recordPath }) {
  return [`GitHub Project status synchronized: ${changeName} -> ${status}`, `Run record: ${recordPath}`].join("\n");
}
