## 1. Ignore Rule Update

- [x] 1.1 Reorganize the root `.gitignore` into clear sections for OS/editor files, Python/backend artifacts, Node/frontend dependencies, build output, logs, coverage, caches, and local environment files; verify `.gitignore` remains the only ignore file in the repository.
- [x] 1.2 Add targeted frontend ignore rules for Next.js output, static export output, TypeScript build info, frontend env files, package-manager byproducts, logs, coverage, and common tool caches; verify `apps/web` source and config files are not matched by the new patterns.

## 2. Verification

- [x] 2.1 Run `git status --ignored --short apps/web .gitignore package.json package-lock.json` and verify generated/frontend-local artifacts are ignored while package manifests, lockfiles, and source files remain visible for tracking.
- [x] 2.2 Review the final `.gitignore` diff and verify it does not ignore broad source directories such as `apps/web/`, `css/`, or `js/`.
