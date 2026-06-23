# CLAUDE.md — Claude Code entrypoint

This repo's full guide lives in [AGENTS.md](AGENTS.md) (the cross-tool source of truth). Read it.

@AGENTS.md

## Claude Code specifics

- **Agents** (`.claude/agents/`) auto-route by their `description`. For multi-step/ambiguous work, invoke
  `/route-request` first; or summon an agent explicitly — *"use the sre-engineer to triage this"*.
- **Skills** (`.claude/skills/`) auto-load when a task matches their `description`; you can also invoke
  one directly: `/pcf-ops`, `/release-gate`, `/merge-gate`, etc. The **ladder skills** set altitude —
  `sde-engineer` and `sre-engineer` pick `sde-ladder`/`sre-ladder` by task complexity.
- **Seniority/experience = skills, not agents.** One `sde-engineer` + one `sre-engineer`; the
  Senior/Principal/Distinguished and Responder/Investigator/Elite levels are the `sde-ladder`/`sre-ladder` skills.
- **Gates** (`merge-gate`, `release-gate`, `production-change-gate`) are pass/fail checklists. **The real
  enforcement for prod changes is GitHub branch protection + protected environments** (our own
  `github-actions-ci` pattern: required reviews, required status checks, environment reviewers) — that is
  the security boundary. As an *auditable speed-bump* in Claude Code, `release-engineer` also runs a
  `PreToolUse` hook ([scripts/production-change-guard.py](scripts/production-change-guard.py)) that blocks
  state-changing `cf` commands unless the gate sentinel (`PCF_GATE_CLEARED=1` or a `.gate-cleared` file)
  is set. Treat that hook as a checklist-forcing convenience for a cooperative agent, **not** a security
  control — a determined path around a local denylist exists; branch protection + environments do not
  depend on the agent cooperating.
- **Subagent dispatch:** classic subagents don't spawn other subagents, so an orchestration *agent* could
  only emit a *plan* the main session re-runs — pure overhead. Routing and incident-command therefore live
  as **skills** (`route-request`, `incident-severity`) that run in the main session, not as agents. (Newer
  "agent teams" can dispatch directly; if you adopt one, re-promoting them may pay — see
  [`docs/adr/0001-routing-and-incident-command-as-skills.md`](docs/adr/0001-routing-and-incident-command-as-skills.md).)

### Model policy (the `model:` frontmatter)

Model choice follows the **nature of the work, not the seniority of the role** (seniority is the ladder
skills). The rule: **`opus` for open-ended reasoning under ambiguity where a wrong call is expensive and
hard to catch; `sonnet` for structured work that follows a defined method, checklist, or template.**

- **`opus` (5):** `sde-engineer` (design/write code), `code-reviewer` (find the bug that has no test),
  `security-reviewer` (adversarial threat reasoning), `sre-engineer` (hypothesis-driven RCA),
  `database-reliability` (schema-safety judgment on irreversible data). These hinge on getting an
  open-ended judgment *right*.
- **`sonnet` (5):** `release-engineer`, `researcher`, `runbook-author`, `sre-monitor`, `test-engineer`.
  Each runs a **defined procedure** — a deploy/rollback playbook, a source-and-cite loop, a runbook
  template, alert/SLO config, or a test plan. (Routing and the incident lifecycle are now the
  `sonnet`-class skills `route-request` / `incident-severity`, run in the main session.)
- **Why `release-engineer` is `sonnet` despite prod stakes:** the *safety control is the gate, not the
  model* — prod actions run only through `release-gate` + `production-change-gate` with explicit human
  sign-off, and it executes *pre-approved plans* rather than inventing them. Bump it to `opus` if your team
  wants extra reasoning headroom on rollback-under-pressure calls; it's a one-line frontmatter change, not
  an architectural one.
- **Tuning:** `model:` is Claude-specific frontmatter. Change it per agent freely; Copilot ignores it and
  uses its own model selection. Keep this policy in sync when you do.

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is. For Copilot-native
`.github/agents/*.agent.md` (translated tool scoping) + `.github/skills/`, run
`pwsh scripts/sync-copilot.ps1` (or `bash scripts/sync-copilot.sh`). Those outputs are generated —
edit definitions under `.claude/` and re-run; don't hand-edit `.github/`.
