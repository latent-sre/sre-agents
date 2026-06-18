# SRE + SDE Agent Fleet

A portable fleet of **AI agents** and **Agent Skills** for application software development and site
reliability work — authored once and runnable in **both Claude Code and VS Code / GitHub Copilot**.

Built for an **application-operations** team on **on-prem servers + PCF (Tanzu Application Service)**,
no Kubernetes, working primarily in **Python, Bash, and PowerShell**, with **Splunk, Grafana,
Wavefront, Moogsoft, ThousandEyes**, deploying via **GitHub Actions** (migrating off Bamboo).

> Full design + conventions: **[AGENTS.md](AGENTS.md)**. Claude Code entrypoint: **[CLAUDE.md](CLAUDE.md)**.

## Why this works in both tools

The portability is real, not aspirational — it rides two current open standards:

- **Agent Skills (`SKILL.md`)** — an open standard ([agentskills.io](https://agentskills.io), published
  by Anthropic Dec 2025, adopted by 30+ tools). VS Code/Copilot reads skills from `.claude/skills/` **and**
  `.github/skills/`; Claude Code reads `.claude/skills/`.
- **Agents** — VS Code/Copilot custom agents read `.claude/agents/` **and** `.github/agents/*.agent.md`;
  Claude Code reads `.claude/agents/`.

So a single source under `.claude/` is read natively by both. An optional generator emits Copilot-native
`.github/` files for hard tool-scoping. `AGENTS.md` is the cross-tool project guide.

## Quick start

**Claude Code** — open the repo. Describe a task; it routes by each agent's `description`. Or be explicit:
- *"Use the coordinator to plan this."*  ·  *"Use the sre-engineer to triage this alert."*
- Invoke a skill directly: `/release-gate`, `/pcf-ops`, `/merge-gate`.

**VS Code / GitHub Copilot** — open the repo; pick a custom agent from the Chat agents dropdown (skills
load automatically or via `/`). For Copilot-native files:
```bash
pwsh scripts/sync-copilot.ps1     # Windows / PowerShell
bash scripts/sync-copilot.sh      # macOS / Linux
```

## Layout

```
AGENTS.md                  cross-tool source of truth (roster, conventions, routing, portability)
CLAUDE.md                  Claude Code entrypoint (imports AGENTS.md + Claude specifics)
.claude/
  agents/                  12 agents — read by Claude Code AND VS Code/Copilot
  skills/                  38 skills (SKILL.md open standard) — read by both tools
                           some bundle scripts/ (pcf-ops Bash/PowerShell, slo-error-budget) and references/ fill-ins
runbooks/                  starter on-call runbooks (PCF OOM, 5xx-after-deploy, dependency timeout)
docs/                       ARCHITECTURE (why) · AGENT-CATALOG (per-agent roster) · HANDOFFS (collab map) · BRANCH-REVIEW
scripts/
  sync-copilot.ps1 / .sh   generate .github/agents + .github/skills for Copilot-native tooling
  validate-fleet.ps1       validate all skills/agents against the Agent Skills spec (CI-friendly)
  readonly-guard.py        PreToolUse hook: blocks state-changing shell commands for read-only agents
.github/
  agents/  skills/         GENERATED (gitignored) — do not hand-edit; edit .claude/ and re-run sync
```

## The fleet

**Agents (who):** `coordinator` · `sde-engineer` · `code-reviewer` · `security-reviewer` ·
`test-engineer` · `sre-engineer` · `sre-monitor` · `incident-commander` · `release-engineer` ·
`runbook-author` · `database-reliability` · `researcher`.

**Seniority/experience is carried by skills, not separate agents** — one `sde-engineer` and one
`sre-engineer` scale altitude by loading a ladder skill:
- SDE: `sde-ladder-senior` → `sde-ladder-principal` → `sde-ladder-distinguished`
- SRE: `sre-ladder-responder` (new hire) → `sre-ladder-investigator` (experienced) → `sre-ladder-elite`

**Skills (how) — 38 total:**
- *Ladders* (6) · *Craft* (`python-craft`, `bash-craft`, `powershell-craft`, `go-craft`,
  `typescript-craft`, `react-craft`, `tdd-workflow`, `safe-refactor`, `debug-rca`) · *Data* (`database-reliability`)
- *Observe/investigate (your stack)*: `triage-golden-signals`, `pcf-ops`, `splunk-triage`,
  `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation`, `thousandeyes-network`, `slo-error-budget`,
  `instrument-service`
- *Ship (your stack)*: `github-actions-ci`, `bamboo-to-actions-migration`, `pcf-deploy`, `rollback-mitigation`
- *Selectors & gates*: `route-request`, `merge-gate`, `release-gate`, `production-change-gate`
- *Incident process*: `incident-severity`, `blameless-postmortem`
- *Docs & conventions*: `runbook-template`, `blameless-postmortem`, `handoff-protocol`, `adr-template`

## Routing & gates

`coordinator` + the `route-request` skill turn a request into an ordered delegation plan. **Gates** are
pass/fail checkpoints that protect quality and prod: `merge-gate` before merge; `release-gate` +
`production-change-gate` before any prod deploy. Portable as checklists; hardenable via GitHub branch
protection / environment reviewers, or Claude Code hooks.

## Extending

Agents and skills are plain Markdown. Add a skill: create `.claude/skills/<name>/SKILL.md` (lowercase-
hyphen `name` ≤64 chars matching the dir, `description` ≤1024 chars saying *what + when*). Add an agent:
`.claude/agents/<name>.md` with `name`, `description`, `tools`, `model`. Re-run the sync script for
Copilot, then `pwsh scripts/validate-fleet.ps1` to check it (or the upstream
[`skills-ref`](https://github.com/agentskills/agentskills) validator).

**Read-only enforcement:** Claude agents that keep `Bash` but must not change state wire
[scripts/readonly-guard.py](scripts/readonly-guard.py) as a `PreToolUse` hook in their frontmatter.
The Copilot generator strips Claude-only hooks and withholds `runCommands` from generated read-only
agents, so use `.github/agents/*.agent.md` when you want hard Copilot tool scoping. Verify the hook fires
in your Claude Code environment (the one piece that can't be unit-tested offline); on systems where the
interpreter is `python3`, adjust the hook command in the agent frontmatter.

## Built from (current as of mid-2026)

- Claude Code [subagents](https://code.claude.com/docs/en/sub-agents) & [skills](https://code.claude.com/docs/en/skills)
- [Agent Skills open standard](https://agentskills.io/specification)
- VS Code [custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) & [agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [AGENTS.md](https://agents.md) cross-tool standard
- Patterns from `anthropics/anthropic-cookbook`, `ComposioHQ/awesome-claude-skills`, `affaan-m/ecc`
