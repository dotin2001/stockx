import { mkdir, mkdtemp, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import assert from "node:assert/strict";

import { runLazy } from "../bin/lazy.mjs";

function git(cwd, args, options = {}) {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    ...options
  });
  if (options.allowFailure !== true && result.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed\n${result.stdout}\n${result.stderr}`);
  }
  return result;
}

function createIo() {
  let stdout = "";
  let stderr = "";
  return {
    io: {
      stdout: (message) => {
        stdout += message;
      },
      stderr: (message) => {
        stderr += message;
      }
    },
    output: () => ({ stdout, stderr })
  };
}

async function makeTempDir() {
  return mkdtemp(path.join(tmpdir(), "lazy-cli-"));
}

async function initRepo({ withRemote = true } = {}) {
  const repo = await makeTempDir();
  git(repo, ["init", "-b", "main"]);
  git(repo, ["config", "user.email", "test@example.local"]);
  git(repo, ["config", "user.name", "Lazy Test"]);
  await writeFile(path.join(repo, "README.md"), "initial\n");
  git(repo, ["add", "."]);
  git(repo, ["commit", "-m", "initial"]);

  let remote = null;
  if (withRemote) {
    remote = await makeTempDir();
    git(remote, ["init", "--bare"]);
    git(repo, ["remote", "add", "origin", remote]);
    git(repo, ["push", "-u", "origin", "main"]);
  }

  return { repo, remote };
}

function run(args, cwd) {
  const captured = createIo();
  const code = runLazy(args, { cwd, io: captured.io });
  return { code, ...captured.output() };
}

test("prints usage for unsupported commands", async () => {
  const cwd = await makeTempDir();

  const result = run(["nope"], cwd);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Usage:/);
  assert.match(result.stderr, /lazy push/);
});

test("runs when invoked through a package-bin style symlink", async () => {
  const cwd = await makeTempDir();
  const binDir = path.join(cwd, "bin");
  await mkdir(binDir);
  const linkPath = path.join(binDir, "lazy");
  await symlink(path.resolve("bin/lazy.mjs"), linkPath);

  const result = spawnSync(linkPath, ["nope"], {
    cwd,
    encoding: "utf8"
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /Usage:/);
  assert.match(result.stderr, /lazy push/);
});

test("rejects missing commit messages before Git inspection", async () => {
  const cwd = await makeTempDir();

  const result = run(["push", "   "], cwd);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Commit message is required/);
});

test("rejects non-Git directories", async () => {
  const cwd = await makeTempDir();

  const result = run(["push", "message"], cwd);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /outside a Git working tree/);
});

test("rejects detached HEAD before staging", async () => {
  const { repo } = await initRepo();
  git(repo, ["checkout", "--detach", "HEAD"]);
  await writeFile(path.join(repo, "change.txt"), "change\n");

  const result = run(["push", "message"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /detached HEAD/);
  assert.equal(git(repo, ["diff", "--cached", "--name-only"]).stdout.trim(), "");
});

test("rejects branches without an upstream before staging", async () => {
  const { repo } = await initRepo({ withRemote: false });
  await writeFile(path.join(repo, "change.txt"), "change\n");

  const result = run(["push", "message"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /no upstream remote/);
  assert.equal(git(repo, ["diff", "--cached", "--name-only"]).stdout.trim(), "");
});

test("rejects unresolved merge conflicts before staging", async () => {
  const { repo } = await initRepo();
  await writeFile(path.join(repo, "conflict.txt"), "base\n");
  git(repo, ["add", "."]);
  git(repo, ["commit", "-m", "base conflict file"]);
  git(repo, ["push"]);

  git(repo, ["checkout", "-b", "side"]);
  await writeFile(path.join(repo, "conflict.txt"), "side\n");
  git(repo, ["commit", "-am", "side change"]);

  git(repo, ["checkout", "main"]);
  await writeFile(path.join(repo, "conflict.txt"), "main\n");
  git(repo, ["commit", "-am", "main change"]);
  git(repo, ["merge", "side"], { allowFailure: true });

  const result = run(["push", "message"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /blocking file changes/);
  assert.match(result.stderr, /conflict.txt/);
});

test("rejects Git-visible local-only artifacts before staging", async () => {
  const { repo } = await initRepo();
  await writeFile(path.join(repo, ".env"), "SECRET=yes\n");

  const result = run(["push", "message"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /blocking file changes/);
  assert.match(result.stderr, /\.env \(environment file\)/);
  assert.equal(git(repo, ["diff", "--cached", "--name-only"]).stdout.trim(), "");
});

test("ignored local artifacts do not block valid changes", async () => {
  const { repo } = await initRepo();
  await writeFile(path.join(repo, ".gitignore"), "*.log\n");
  await writeFile(path.join(repo, "debug.log"), "ignored\n");
  await writeFile(path.join(repo, "feature.txt"), "feature\n");

  const result = run(["push", "message with spaces"], repo);

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Candidate Git-visible changes/);
  assert.doesNotMatch(result.stdout, /debug\.log/);
  assert.equal(git(repo, ["log", "-1", "--pretty=%B"]).stdout.trim(), "message with spaces");
});

test("reports nothing to commit after staging", async () => {
  const { repo } = await initRepo();

  const result = run(["push", "empty"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stdout, /No Git-visible changes found/);
  assert.match(result.stderr, /Nothing to commit/);
});

test("commits and pushes valid changes", async () => {
  const { repo, remote } = await initRepo();
  await mkdir(path.join(repo, "src"));
  await writeFile(path.join(repo, "src", "feature.txt"), "feature\n");

  const result = run(["push", "add feature"], repo);

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Candidate Git-visible changes/);
  assert.match(result.stdout, /Lazy push complete:/);
  assert.match(result.stdout, /origin\/main/);
  assert.equal(git(repo, ["log", "-1", "--pretty=%B"]).stdout.trim(), "add feature");
  assert.equal(git(remote, ["log", "-1", "--pretty=%B"]).stdout.trim(), "add feature");
});

test("preserves Git diagnostics when push fails", async () => {
  const { repo, remote } = await initRepo();
  git(repo, ["remote", "set-url", "origin", path.join(remote, "missing.git")]);
  await writeFile(path.join(repo, "change.txt"), "change\n");

  const result = run(["push", "commit before failed push"], repo);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Git step failed: git push/);
  assert.match(result.stderr, /does not appear to be a git repository|Could not read from remote repository/);
  assert.equal(git(repo, ["log", "-1", "--pretty=%B"]).stdout.trim(), "commit before failed push");
});
