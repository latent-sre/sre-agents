---
name: craft
description: >-
  Write, review, test, debug, or safely refactor Python, Bash, PowerShell, and Go using
  language-specific conventions plus the bundled tests-first and behavior-preserving-refactoring
  processes. Triggers: 'write this in Python', 'review this Bash script', 'refactor this Go code'.
  Ownership map only—not a load: backend-craft owns API/resiliency design and frontend-craft owns
  TypeScript/React UI design.
---

# Craft — pick the language

Match the repo's existing tooling first; the per-language defaults apply when none is set. Load **only**
the file for the language you're touching.

- **Python** — typing, `ruff`/`uv`, `pytest`, exceptions, subprocess/HTTP safety, secrets-safe logging.
  → [`references/python.md`](./references/python.md)
- **Bash** — strict mode, quoting, `[[ ]]`, `shellcheck`, traps/`mktemp`, word-splitting pitfalls.
  → [`references/bash.md`](./references/bash.md)
- **PowerShell** — approved verbs, advanced functions, object-pipeline output, `5.1` vs `7+`, `Pester`.
  → [`references/powershell.md`](./references/powershell.md)
- **Go** — `gofmt`/`go vet`/`golangci-lint`, error wrapping with `%w`, table tests with `-race`,
  context/goroutine-leak safety. → [`references/go.md`](./references/go.md)
- **Writing tests first / after any bug fix** — use the regression-first method before implementation.
  → [tests first](./references/tdd.md)
- **A behavior-preserving refactor** — pin behavior, map consumers, and work in reversible steps.
  → [safe refactoring](./references/safe-refactor.md)
