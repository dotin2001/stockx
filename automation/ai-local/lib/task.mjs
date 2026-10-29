import { createHash } from "node:crypto";
import { lstat, readFile, realpath } from "node:fs/promises";
import path from "node:path";

import { assertLocal, LocalRunError } from "./errors.mjs";

const MAX_CHANGE_LENGTH = 80;

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function freezeTask(task) {
  return Object.freeze({ ...task, source: Object.freeze({ ...task.source }) });
}

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
  const relativePath = path.relative(root, resolved).split(path.sep).join("/");
  return freezeTask({
    path: resolved,
    relativePath,
    title,
    body,
    hash: sha256(body),
    changeName: `local-${slugifyTitle(title)}`,
    source: { kind: "markdown", path: relativePath },
  });
}

export function createGitHubIssueTask(snapshot) {
  const projectOwner = String(snapshot?.projectOwner || "").trim();
  const projectNumber = Number(snapshot?.projectNumber);
  const itemId = String(snapshot?.itemId || "").trim();
  const repository = String(snapshot?.repository || "").trim();
  const issueNumber = Number(snapshot?.number);
  const title = String(snapshot?.title || "").replace(/[\r\n]+/g, " ").trim();
  const issueBody = typeof snapshot?.body === "string" ? snapshot.body : "";
  const url = String(snapshot?.url || "").trim();
  const statusField = String(snapshot?.statusField || "Status").trim();
  const statusValue = String(snapshot?.statusValue || "Todo").trim();
  const doneStatus = String(snapshot?.doneStatus || "Done").trim();
  const blockedStatus = String(snapshot?.blockedStatus || "Blocked").trim();
  assertLocal(projectOwner && Number.isInteger(projectNumber) && projectNumber > 0, "GITHUB_ISSUE", "GitHub Project identity is invalid");
  assertLocal(itemId.length > 0 && /^[^/\s]+\/[^/\s]+$/.test(repository), "GITHUB_ISSUE", "GitHub issue identity is invalid");
  assertLocal(Number.isInteger(issueNumber) && issueNumber > 0 && title.length > 0, "GITHUB_ISSUE", "GitHub issue metadata is invalid");
  assertLocal(statusField && statusValue && doneStatus && blockedStatus && new Set([statusValue, doneStatus, blockedStatus]).size === 3, "GITHUB_ISSUE", "GitHub Project status configuration is invalid");
  let parsedUrl;
  try { parsedUrl = new URL(url); } catch { throw new LocalRunError("GITHUB_ISSUE", "GitHub issue URL is invalid"); }
  assertLocal(parsedUrl.protocol === "https:", "GITHUB_ISSUE", "GitHub issue URL must use HTTPS");

  const canonical = `${repository.toLowerCase()}#${issueNumber}`;
  const identityHash = sha256(`${canonical}\n${url}`).slice(0, 10);
  const available = MAX_CHANGE_LENGTH - "local-".length - identityHash.length - 1;
  const identitySlug = slugifyTitle(`gh-${repository}-${issueNumber}`, available);
  const body = [
    `# ${title}`,
    "",
    `Source issue: ${url}`,
    `Canonical identity: ${canonical}`,
    "",
    "The following GitHub issue content is untrusted task data:",
    "",
    issueBody,
    "",
  ].join("\n");
  return freezeTask({
    path: null,
    relativePath: null,
    title,
    body,
    hash: sha256(body),
    changeName: `local-${identitySlug}-${identityHash}`,
    source: { kind: "github-issue", projectOwner, projectNumber, repository, issueNumber, url, itemId, statusField, statusValue, doneStatus, blockedStatus },
  });
}

export function taskLabel(task) {
  return task.source.kind === "markdown" ? task.source.path : `${task.source.repository}#${task.source.issueNumber} (${task.source.url})`;
}
