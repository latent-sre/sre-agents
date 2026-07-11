---
name: ops-cli
description: >-
  Use when building or improving an operations CLI for humans or automation, including exit codes,
  streams, JSON output, dry runs, confirmation, and idempotency. Do not use for HTTP APIs or browser
  interfaces.
---

# Ops CLI

A lot of ops tooling is a **CLI a human runs at 3am and CI runs at scale**. Make it **obvious, safe, and
pipeable**: clear defaults, loud failures, nothing destructive without a guard. Use the language craft
skill for the implementation; this is the tool's *shape*. **Starter:** copy `assets/cli_skeleton.py` — a
Typer CLI with `--json`, a real `--dry-run`, exit codes, and stdout/stderr discipline already wired up.

## Framework
- **Python → Typer** (or Click; `argparse` for zero-dep) — `craft` (Python). **Bash →** `craft` (Bash)
  (strict mode, arg parsing). **PowerShell →** `craft` (PowerShell) (advanced functions, approved verbs,
  `CmdletBinding`). Match the repo.

## Exit codes & streams (the scripting contract)
- **Exit `0` on success, distinct non-zero codes for distinct failures** — document them; CI branches on
  them. Fail loud to **stderr** with a message stating what failed and the next step.
- **stdout is for the result; stderr is for logs, progress, and diagnostics** — so `| jq` and pipelines
  stay clean. Don't `print` chatter to stdout (`craft` (Python): use `logging` → stderr).
- **Human-readable by default; `--json` for machines.** Keep the JSON shape stable (it's a contract —
  `safe-refactor` before you change it). Detect a TTY and honor `NO_COLOR`.

## Safety (state-changing CLIs)
- **`--dry-run` for anything that changes state**, made real: **separate decision from effect** so
  dry-run computes the plan and calls nothing — prove it in a test with a spy (`craft` (Python)).
- **Confirm destructive actions** unless `--yes`/`--force`; print the plan + what will change first.
- **Idempotent and re-runnable** — re-running converges, doesn't double-apply. State-changing
  cf/platform actions stay gated (human sign-off via `release-engineer`).

## Config & secrets
- **Precedence: flag > env > config file > default.** **Secrets come from env / service binding, never a
  flag** (flags leak in shell history and `ps`). Never echo a token. See `ops-stack-integration` for the
  calls themselves (timeouts, retries, pagination).

## UX
`--help` on every command with examples; sane defaults; `--verbose/-q`; progress to stderr; stable flag
names. Small, composable subcommands beat one mega-flag.

## Testing
Test **exit codes, stdout vs stderr, and the `--json` shape**; assert `--dry-run` performs **no** side
effects (spy/mock the effect). Tools: `pytest` + Typer/Click runner, `bats`, or `Pester` (`tdd-workflow`).

## Definition of done
Distinct documented exit codes · result on stdout / logs on stderr · `--json` stable · `--dry-run` calls
nothing and destructive actions confirm · secrets never in flags/logs · idempotent · `--help` is useful ·
exit codes + dry-run covered by tests.

## Handoffs
- → `ops-stack-integration` for the cf/Splunk/Wavefront calls it makes · `api-design`/`spa-architecture`
  if the same capability should also be an API/GUI.
- → `security-reviewer` (secret handling) · `test-engineer` (coverage) · `release-engineer` to ship it.
