---
name: craft
description: >-
  Use when writing, reviewing, or refactoring Python, Bash, PowerShell, Go, TypeScript, or React code
  and language-specific conventions are needed. Do not use for general engineering process or
  architecture decisions.
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
