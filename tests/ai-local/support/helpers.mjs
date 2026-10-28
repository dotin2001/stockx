import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

export function command(cwd, executable, args, options = {}) {
  const result = spawnSync(executable, args, { cwd, encoding: "utf8", ...options });
  if (!options.allowFailure && result.status !== 0) throw new Error(`${executable} ${args.join(" ")} failed\n${result.stdout}\n${result.stderr}`);
  return result;
}

export function git(cwd, args, options) {
  return command(cwd, "git", args, options);
}

export async function tempDirectory(prefix = "ai-local-test-") {
  return mkdtemp(path.join(os.tmpdir(), prefix));
}

export async function initRepository() {
  const root = await tempDirectory();
  git(root, ["init", "-b", "main"]);
  git(root, ["config", "user.name", "AI Local Test"]);
  git(root, ["config", "user.email", "ai-local@example.test"]);
  await writeFile(path.join(root, ".gitignore"), ".ai-local/\n");
  await writeFile(path.join(root, "README.md"), "# Test\n");
  git(root, ["add", "."]);
  git(root, ["commit", "-m", "initial"]);
  return root;
}

export function memoryIo() {
  let stdout = "";
  let stderr = "";
  return {
    io: {
      info(value = "") { stdout += `${value}\n`; },
      error(value = "") { stderr += `${value}\n`; },
      phase(name, detail = "") { stdout += `[${name}] ${detail}\n`; },
    },
    read() { return { stdout, stderr }; },
  };
}
