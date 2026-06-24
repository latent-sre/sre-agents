---
name: craft
description: >-
  Idiomatic, production-grade coding conventions for this team's languages — load the file for the
  language you're writing or reviewing. Use whenever writing, reviewing, or refactoring code in Python,
  Bash, PowerShell, Go, TypeScript, or React: typing/linting/testing, error handling, operational
  safety, concurrency, and the per-language pitfalls a reviewer would flag. Read the one language file
  you need; match the repo's existing tooling first.
---

# Craft — pick the language

Match the repo's existing tooling first; the per-language defaults apply when none is set. Load **only**
the file for the language you're touching.

- **Python** — typing, `ruff`/`uv`, `pytest`, exceptions, subprocess/HTTP safety, secrets-safe logging.
  → [`references/python.md`](references/python.md)
- **Bash** — strict mode, quoting, `[[ ]]`, `shellcheck`, traps/`mktemp`, word-splitting pitfalls.
  → [`references/bash.md`](references/bash.md)
- **PowerShell** — approved verbs, advanced functions, object-pipeline output, `5.1` vs `7+`, `Pester`.
  → [`references/powershell.md`](references/powershell.md)
- **Go** — `gofmt`/`go vet`/`golangci-lint`, error wrapping with `%w`, table tests with `-race`,
  context/goroutine-leak safety. → [`references/go.md`](references/go.md)
- **TypeScript** — strict `tsconfig`, `unknown` over `any`, `satisfies`, discriminated unions, Vitest.
  → [`references/typescript.md`](references/typescript.md)
- **React** — Rules of Hooks, "you might not need an Effect", Server Components, React 19 Actions, RTL.
  → [`references/react.md`](references/react.md)
