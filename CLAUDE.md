# CLAUDE.md — Claude Code entrypoint

This repo's full guide lives in [AGENTS.md](AGENTS.md) (the cross-tool source of truth). Read it.

@AGENTS.md

## Claude Code specifics

- **Agents** (`.claude/agents/`) auto-route by their `description`. For multi-step/ambiguous work, ask
  *"use the coordinator"* first; or summon one explicitly — *"use the sre-engineer to triage this"*.
- **Skills** (`.claude/skills/`) auto-load when a task matches their `description`; you can also invoke
  one directly: `/pcf-ops`, `/release-gate`, `/merge-gate`, etc. The **ladder skills** set altitude —
  `sde-engineer` and `sre-engineer` pick `*-ladder-*` by task complexity.
- **Seniority/experience = skills, not agents.** One `sde-engineer` + one `sre-engineer`; the
  Senior/Principal/Distinguished and Responder/Investigator/Elite levels are the `*-ladder-*` skills.
- **Gates** (`merge-gate`, `release-gate`, `production-change-gate`) are pass/fail checklists. To make
  them *hard* in Claude Code, add a [hook](https://code.claude.com/docs/en/hooks) in
  `.claude/settings.json` (e.g. a `PreToolUse` matcher that blocks the deploy until the gate is cleared)
  — optional, Claude-only. In GitHub, back them with branch protection + environment reviewers instead.
- **Subagent dispatch:** classic subagents don't spawn other subagents, so `coordinator` and
  `incident-commander` produce *plans* the main session executes. (Newer "agent teams" can dispatch
  directly; keep the plan-output behavior for portability with Copilot.)

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is. For Copilot-native
`.github/agents/*.agent.md` (translated tool scoping) + `.github/skills/`, run
`pwsh scripts/sync-copilot.ps1` (or `bash scripts/sync-copilot.sh`). Those outputs are generated —
edit definitions under `.claude/` and re-run; don't hand-edit `.github/`.
