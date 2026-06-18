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

### Model policy (the `model:` frontmatter)

Model choice follows the **nature of the work, not the seniority of the role** (seniority is the ladder
skills). The rule: **`opus` for open-ended reasoning under ambiguity where a wrong call is expensive and
hard to catch; `sonnet` for structured work that follows a defined method, checklist, or template.**

- **`opus` (5):** `sde-engineer` (design/write code), `code-reviewer` (find the bug that has no test),
  `security-reviewer` (adversarial threat reasoning), `sre-engineer` (hypothesis-driven RCA),
  `database-reliability` (schema-safety judgment on irreversible data). These hinge on getting an
  open-ended judgment *right*.
- **`sonnet` (7):** `coordinator`, `incident-commander`, `release-engineer`, `researcher`,
  `runbook-author`, `sre-monitor`, `test-engineer`. Each runs a **defined procedure** — a routing table,
  the incident lifecycle, a deploy/rollback playbook, a source-and-cite loop, a runbook template, alert/
  SLO config, or a test plan.
- **Why `release-engineer`/`incident-commander` are `sonnet` despite prod stakes:** the *safety control
  is the gate, not the model* — prod actions run only through `release-gate` + `production-change-gate`
  with explicit human sign-off, and these agents execute *pre-approved plans* rather than invent them.
  Bump either to `opus` if your team wants extra reasoning headroom on rollback-under-pressure calls;
  it's a one-line frontmatter change, not an architectural one.
- **Tuning:** `model:` is Claude-specific frontmatter. Change it per agent freely; Copilot ignores it and
  uses its own model selection. Keep this policy in sync when you do.

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is. For Copilot-native
`.github/agents/*.agent.md` (translated tool scoping) + `.github/skills/`, run
`pwsh scripts/sync-copilot.ps1` (or `bash scripts/sync-copilot.sh`). Those outputs are generated —
edit definitions under `.claude/` and re-run; don't hand-edit `.github/`.
