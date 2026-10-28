import { createInterface } from "node:readline/promises";

import { assertLocal, LocalRunError } from "./errors.mjs";
import { runProcess } from "./process.mjs";
import { createGitHubIssueTask } from "./task.mjs";

const GITHUB_ENV_KEYS = [
  "GH_CONFIG_DIR", "GH_HOST", "HOME", "HTTPS_PROXY", "HTTP_PROXY", "LANG", "LC_ALL", "LOGNAME",
  "NODE_EXTRA_CA_CERTS", "NO_COLOR", "NO_PROXY", "PATH", "SHELL", "SSL_CERT_DIR", "SSL_CERT_FILE",
  "TERM", "TMPDIR", "USER",
];

const PROJECT_ITEMS_QUERY = `query($project: ID!, $cursor: String, $statusField: String!) {
  node(id: $project) {
    ... on ProjectV2 {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          fieldValueByName(name: $statusField) {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
          content {
            __typename
            ... on Issue {
              id
              number
              title
              url
              repository { nameWithOwner }
            }
          }
        }
      }
    }
  }
}`;

const PROJECT_ITEM_QUERY = `query($item: ID!, $statusField: String!) {
  node(id: $item) {
    ... on ProjectV2Item {
      id
      fieldValueByName(name: $statusField) {
        ... on ProjectV2ItemFieldSingleSelectValue { name }
      }
      content {
        __typename
        ... on Issue {
          id
          number
          title
          body
          url
          repository { nameWithOwner }
        }
      }
    }
  }
}`;

export function githubEnvironment(source = process.env) {
  return Object.fromEntries(GITHUB_ENV_KEYS.filter((key) => source[key] !== undefined).map((key) => [key, source[key]]));
}

async function github(commandRunner, root, args, signal) {
  return commandRunner("gh", args, { cwd: root, env: githubEnvironment(), signal });
}

function parseJson(text, code, message) {
  try { return JSON.parse(text); } catch { throw new LocalRunError(code, message); }
}

export async function resolveGitHubProject({ root, owner, number, commandRunner = runProcess, signal }) {
  try {
    await github(commandRunner, root, ["--version"], signal);
  } catch (error) {
    if (error?.code === "COMMAND_START") throw new LocalRunError("GITHUB_CLI", "GitHub CLI is required for Project mode; install `gh`, then run `gh auth login`");
    throw new LocalRunError("GITHUB_CLI", "GitHub CLI could not be executed");
  }
  try {
    await github(commandRunner, root, ["auth", "status"], signal);
  } catch {
    throw new LocalRunError("GITHUB_AUTH", "GitHub CLI is not authenticated; run `gh auth login` and grant Project read access");
  }
  let result;
  try {
    result = await github(commandRunner, root, ["project", "view", String(number), "--owner", owner, "--format", "json"], signal);
  } catch {
    throw new LocalRunError("GITHUB_PROJECT_ACCESS", `Cannot read GitHub Project ${owner}/${number}; verify the owner, number, and Project read scope`);
  }
  const value = parseJson(result.stdout, "GITHUB_PROJECT_RESPONSE", "GitHub Project metadata was not valid JSON");
  assertLocal(value && typeof value === "object" && typeof value.id === "string" && value.id.length > 0, "GITHUB_PROJECT_RESPONSE", "GitHub Project metadata is missing its node ID");
  return Object.freeze({ id: value.id, owner, number, title: typeof value.title === "string" ? value.title : "" });
}

function graphqlArgs(query, variables) {
  const args = ["api", "graphql", "-f", `query=${query}`];
  for (const [key, value] of Object.entries(variables)) {
    if (value !== null && value !== undefined) args.push("-f", `${key}=${value}`);
  }
  return args;
}

async function graphql({ root, query, variables, commandRunner, signal }) {
  let result;
  try {
    result = await github(commandRunner, root, graphqlArgs(query, variables), signal);
  } catch (error) {
    if (error?.code === "COMMAND_ABORTED") throw error;
    throw new LocalRunError("GITHUB_PROJECT_READ", "GitHub Project data could not be read; verify authentication and Project read access");
  }
  const value = parseJson(result.stdout, "GITHUB_PROJECT_RESPONSE", "GitHub Project API returned invalid JSON");
  assertLocal(!Array.isArray(value?.errors) || value.errors.length === 0, "GITHUB_PROJECT_READ", "GitHub Project API returned an incomplete response");
  return value;
}

function issueFromNode(node, statusValue) {
  if (!node || typeof node !== "object" || node.fieldValueByName?.name !== statusValue) return null;
  const content = node.content;
  if (content?.__typename !== "Issue") return null;
  const repository = content.repository?.nameWithOwner;
  const number = Number(content.number);
  const title = typeof content.title === "string" ? content.title.replace(/[\r\n]+/g, " ").trim() : "";
  if (typeof node.id !== "string" || !/^[^/\s]+\/[^/\s]+$/.test(repository || "") || !Number.isInteger(number) || number <= 0 || !title || typeof content.url !== "string") return null;
  return Object.freeze({ itemId: node.id, repository, number, title, url: content.url });
}

export async function listTodoIssues({ root, projectId, statusField = "Status", statusValue = "Todo", commandRunner = runProcess, signal }) {
  const issues = [];
  let cursor = null;
  const seenCursors = new Set();
  do {
    const response = await graphql({
      root,
      query: PROJECT_ITEMS_QUERY,
      variables: { project: projectId, cursor, statusField },
      commandRunner,
      signal,
    });
    const connection = response?.data?.node?.items;
    assertLocal(connection && Array.isArray(connection.nodes) && connection.pageInfo && typeof connection.pageInfo.hasNextPage === "boolean", "GITHUB_PROJECT_RESPONSE", "GitHub Project item response is malformed");
    for (const node of connection.nodes) {
      const issue = issueFromNode(node, statusValue);
      if (issue) issues.push(issue);
    }
    if (!connection.pageInfo.hasNextPage) break;
    const next = connection.pageInfo.endCursor;
    assertLocal(typeof next === "string" && next.length > 0 && !seenCursors.has(next), "GITHUB_PROJECT_RESPONSE", "GitHub Project pagination cursor is invalid");
    seenCursors.add(next);
    cursor = next;
  } while (true);
  return Object.freeze(issues.sort((left, right) => left.repository.localeCompare(right.repository) || left.number - right.number));
}

export function parseIssueSelector(value) {
  const match = /^([^/\s]+\/[^/#\s]+)#([1-9]\d*)$/.exec(String(value || "").trim());
  assertLocal(match, "GITHUB_ISSUE_SELECTOR", "Issue selector must use owner/repo#number");
  return { repository: match[1], number: Number(match[2]) };
}

async function defaultPrompt(question, { input = process.stdin, output = process.stdout } = {}) {
  const terminal = createInterface({ input, output });
  try { return await terminal.question(question); } catch { return null; } finally { terminal.close(); }
}

export async function selectProjectIssue(items, options = {}) {
  const { selector = null, isTTY = Boolean(process.stdin.isTTY), writeLine = () => {}, prompt = defaultPrompt } = options;
  assertLocal(Array.isArray(items) && items.length > 0, "GITHUB_INBOX_EMPTY", "No eligible GitHub Project issues match the configured Todo status");
  if (selector) {
    const expected = parseIssueSelector(selector);
    const matches = items.filter((item) => item.repository.toLowerCase() === expected.repository.toLowerCase() && item.number === expected.number);
    assertLocal(matches.length === 1, "GITHUB_ISSUE_SELECTOR", "Selected issue does not resolve to exactly one eligible Project item");
    return matches[0];
  }
  assertLocal(isTTY, "GITHUB_ISSUE_SELECTOR", "Non-interactive Project mode requires --issue <owner/repo#number>");
  writeLine("Eligible GitHub Project issues:");
  items.forEach((item, index) => writeLine(`  ${index + 1}. ${item.repository}#${item.number} ${item.title}`));
  while (true) {
    const answer = await prompt("Choose one issue number, or q to cancel: ");
    if (answer === null || /^\s*(?:q|quit|cancel)?\s*$/i.test(String(answer))) throw new LocalRunError("GITHUB_SELECTION_CANCELLED", "GitHub Project issue selection was cancelled");
    if (/^\d+$/.test(String(answer).trim())) {
      const selected = items[Number(answer) - 1];
      if (selected) return selected;
    }
    writeLine(`Enter a number from 1 to ${items.length}, or q to cancel.`);
  }
}

export async function refreshSelectedIssue({ root, selected, project, statusField = "Status", statusValue = "Todo", commandRunner = runProcess, signal }) {
  const response = await graphql({
    root,
    query: PROJECT_ITEM_QUERY,
    variables: { item: selected.itemId, statusField },
    commandRunner,
    signal,
  });
  const node = response?.data?.node;
  assertLocal(node && node.id === selected.itemId, "GITHUB_ISSUE_STALE", "Selected Project item is no longer available; refresh the inbox");
  assertLocal(node.fieldValueByName?.name === statusValue, "GITHUB_ISSUE_STALE", "Selected issue is no longer in the configured Todo status; refresh the inbox");
  const content = node.content;
  const repository = content?.repository?.nameWithOwner;
  assertLocal(content?.__typename === "Issue" && repository === selected.repository && Number(content.number) === selected.number, "GITHUB_ISSUE_STALE", "Selected issue identity changed; refresh the inbox");
  return createGitHubIssueTask({
    projectOwner: project.owner,
    projectNumber: project.number,
    itemId: node.id,
    repository,
    number: Number(content.number),
    title: content.title,
    body: typeof content.body === "string" ? content.body : "",
    url: content.url,
  });
}

export async function loadGitHubProjectTask({ root, project: options, io, commandRunner = runProcess, prompt, signal }) {
  const project = await resolveGitHubProject({ root, owner: options.owner, number: options.number, commandRunner, signal });
  const issues = await listTodoIssues({ root, projectId: project.id, statusField: options.statusField, statusValue: options.statusValue, commandRunner, signal });
  const selected = await selectProjectIssue(issues, {
    selector: options.issueSelector,
    isTTY: options.isTTY,
    writeLine: (line) => io?.info(line),
    prompt,
  });
  return refreshSelectedIssue({ root, selected, project, statusField: options.statusField, statusValue: options.statusValue, commandRunner, signal });
}
