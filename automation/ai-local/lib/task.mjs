import { createHash } from "node:crypto";
import { lstat, readFile, realpath } from "node:fs/promises";
import path from "node:path";

import { assertLocal, LocalRunError } from "./errors.mjs";

const MAX_CHANGE_LENGTH = 80;

export function slugifyTitle(title, maxLength = MAX_CHANGE_LENGTH - "local-".length) {
  const slug = String(title)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, maxLength)
    .replace(/-+$/g, "");
  assertLocal(slug.length > 0, "TASK_TITLE", "Task heading must contain letters or numbers");
  return slug;
}

export function firstHeading(markdown) {
  const match = /^#\s+(.+?)\s*$/m.exec(markdown);
  assertLocal(match, "TASK_HEADING", "Task file must contain a first-level Markdown heading");
  return match[1].trim();
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative);
}

export async function resolveTaskFile(repositoryRoot, taskArgument, { access = { lstat, readFile, realpath } } = {}) {
  assertLocal(typeof taskArgument === "string" && taskArgument.trim(), "TASK_ARGUMENT", "Exactly one --task Markdown path is required");
  const root = await access.realpath(repositoryRoot);
  const requested = path.resolve(root, taskArgument);
  let resolved;
  try {
    resolved = await access.realpath(requested);
  } catch {
    throw new LocalRunError("TASK_MISSING", "Task file does not exist or is unreadable");
  }
  assertLocal(resolved === requested, "TASK_SYMLINK", "Task path may not contain symbolic links");
  assertLocal(isInside(root, resolved), "TASK_SCOPE", "Task file must be inside the repository");
  const stat = await access.lstat(resolved);
  assertLocal(stat.isFile() && !stat.isSymbolicLink(), "TASK_TYPE", "Task path must be a regular non-symbolic-link file");
  assertLocal(path.extname(resolved).toLowerCase() === ".md", "TASK_FORMAT", "Task file must use the .md extension");
  const body = await access.readFile(resolved, "utf8");
  assertLocal(body.trim().length > 0, "TASK_EMPTY", "Task file must not be empty");
  const title = firstHeading(body);
  const changeName = `local-${slugifyTitle(title)}`;
  const relativePath = path.relative(root, resolved).split(path.sep).join("/");
  return Object.freeze({
    path: resolved,
    relativePath,
    title,
    body,
    hash: createHash("sha256").update(body).digest("hex"),
    changeName,
  });
}
