# Developer Workflow

## Lazy Push

The repository provides a dependency-free `lazy` CLI for the common guarded Git publish flow.

```bash
lazy push "my commit text"
```

The command checks the Git working tree before it stages anything. It stops when it finds unresolved merge conflicts, a detached HEAD, a branch without an upstream remote, or Git-visible local-only files such as `.env` files, dependency installs, build output, caches, logs, coverage, or virtual environments.

When checks pass, it runs:

```bash
git add .
git commit -m "my commit text"
git push
```

The `lazy` executable is exposed through the root package `bin` metadata. If your shell does not already resolve package bins as commands, run it through npm:

```bash
npm exec -- lazy push "my commit text"
```

For a direct `lazy push ...` command in your shell, link the package bin from this repository:

```bash
npm link
lazy push "my commit text"
```

Use a disposable repository when smoke-testing the command. The command intentionally performs a real `git push` after a successful commit.
