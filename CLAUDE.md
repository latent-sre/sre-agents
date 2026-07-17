# CLAUDE.md — Claude Code entrypoint

The fleet guide is [AGENTS.md](AGENTS.md).

@AGENTS.md

## Claude Code specifics

- Agents live in `.claude/agents/`, skills in `.claude/skills/`, the `adr` scaffold in
  `.claude/commands/`. Everything is directly edited source — there is no generator.
- `sre` and `sre-steward` run Bash under `scripts/readonly-guard.py` (allowlist, fail-closed).
  A denied command is a finding, not an obstacle: fix the allowlist by PR if a legitimate read
  is blocked.
- Structural checks: `python scripts/gate_a.py` (on Windows use `python` or `py -3` — `python3`
  is the Microsoft Store stub on this machine).
