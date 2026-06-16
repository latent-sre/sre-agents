---
name: bash-craft
description: >-
  Safe, robust Bash scripting conventions for this team — strict mode, quoting, structure, cleanup, and
  portability. Use whenever writing, reviewing, or refactoring shell scripts for automation, CI, or ops
  glue. Covers set -euo pipefail, quoting, [[ ]] tests, shellcheck, traps/mktemp, and avoiding common
  word-splitting and parsing pitfalls.
metadata:
  domain: language
  language: bash
---

# Bash craft

Shell is for glue and orchestration. If a script grows real logic/data structures, recommend Python
(`python-craft`) instead.

## Always start with
```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```
- `-e` exit on error, `-u` error on unset var, `-o pipefail` catch failures mid-pipe.
- Trap cleanup: `tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT`.

## Quoting & tests (the #1 source of bugs)
- **Quote every expansion:** `"$var"`, `"${arr[@]}"`, `"$(cmd)"`. Unquoted = word-splitting + globbing bugs.
- Use `[[ ... ]]` not `[ ... ]`; `[[ -z "$x" ]]`, `[[ "$a" == "$b" ]]`, `[[ "$s" =~ regex ]]`.
- Arithmetic in `(( ... ))`; integer compare with `-eq`/`-lt` inside `[[ ]]`.
- **Never parse `ls`**; use globs or `find -print0 | while IFS= read -r -d ''`.

## Structure
- Functions + a `main "$@"`; `local` for function vars. Put `main` call at the bottom.
- Validate inputs early; print usage on bad args. Errors → stderr: `echo "msg" >&2`.
- Meaningful exit codes; check command success explicitly where `-e` isn't enough.
- `readonly`/`declare -r` for constants; prefer `$(...)` over backticks.

## Quality gate
- **Pass `shellcheck`** with no warnings (or justified `# shellcheck disable=` with a reason).
- POSIX-portable (`#!/bin/sh`) only if it must run on non-bash; otherwise bash is fine — state which.
- Make it idempotent; guard destructive actions (`rm`, overwrites) behind a confirm flag or dry-run.

## Tests
- `bats` (or an assert harness): check exit codes, stdout/stderr, and idempotency. See `tdd-workflow`.
