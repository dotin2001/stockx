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
