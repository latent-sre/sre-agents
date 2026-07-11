# SRE + SDE Agent Fleet

A portable fleet of **AI agents** and **Agent Skills** for application software development and site
reliability work — authored once and runnable in **both Claude Code and VS Code / GitHub Copilot**.

Shipped with a default **stack profile** for an **application-operations** team on **on-prem servers +
PCF (Tanzu Application Service)**, no Kubernetes, working primarily in **Python, Bash, and PowerShell**,
with **Splunk, Grafana, Wavefront, Moogsoft, ThousandEyes**, deploying via **GitHub Actions** (migrating
off Bamboo). The whole fleet is written to that one profile — **retarget it for your team by editing the
single [Stack profile](AGENTS.md#stack-profile--the-one-block-to-edit-when-you-retarget-the-fleet) block
in AGENTS.md**, then follow **[docs/CURATION.md](docs/CURATION.md)** for which skills are universal vs.
stack-specific.

> Full design + conventions: **[AGENTS.md](AGENTS.md)**. Claude Code entrypoint: **[CLAUDE.md](CLAUDE.md)**.

## Why this works in both tools

The portability is real, not aspirational — it rides two current open standards:

- **Agent Skills (`SKILL.md`)** — an open standard ([agentskills.io](https://agentskills.io), published
  by Anthropic Dec 2025, adopted by 30+ tools). Both VS Code/Copilot and Claude Code read skills from
  `.claude/skills/` directly.
- **Agents** — VS Code/Copilot custom agents read `.claude/agents/` **and** `.github/agents/*.agent.md`;
  Claude Code reads `.claude/agents/`.

So a single source under `.claude/` is read natively by both. An optional generator emits Copilot-native
`.github/` files for hard tool-scoping. `AGENTS.md` is the cross-tool project guide.

## Quick start

**Claude Code** — open the repo. Describe a task; it routes by each agent's `description`. Or be explicit:
- *"Use the sre-engineer to triage this alert."*  ·  invoke `/route-request` to plan a multi-step task.
- Invoke a skill directly: `/release-gate`, `/pcf-ops`, `/merge-gate`.

**VS Code / GitHub Copilot** — open the repo; pick a custom agent from the Chat agents dropdown (skills
load automatically or via `/`). For Copilot-native files:
```bash
bash scripts/sync-copilot.sh      # macOS / Linux / Windows (Git Bash)
```

**Vendor it into an existing repo** — to embed the fleet as a subdirectory of another project (rather than
using it standalone), see **[docs/INTEGRATION.md](docs/INTEGRATION.md)**: the scripts are location-robust,
but `.claude/`, `CLAUDE.md`, `AGENTS.md`, and `.github/` must be surfaced at the host repo's root.
For **what to keep, genericize, or drop** when adapting the fleet to a different team or stack, see
**[docs/CURATION.md](docs/CURATION.md)** (it doubles as the review checklist for an LLM adaptation pass).

## Layout

```
AGENTS.md                  cross-tool source of truth (roster, conventions, routing, portability)
CLAUDE.md                  Claude Code entrypoint (imports AGENTS.md + Claude specifics)
.claude/
  agents/                  the agent roster — read by Claude Code AND VS Code/Copilot
  skills/                  the skills (SKILL.md open standard) — read by both tools
                           some bundle scripts/ (pcf-ops Bash/PowerShell, slo-error-budget) and references/ fill-ins
runbooks/                  starter on-call runbooks (PCF OOM, 5xx-after-deploy, dependency timeout)
evals/                     behavioral evals (scenarios + graders) — routing, gates, security; --validate runs in CI
docs/                       ARCHITECTURE (why) · AGENT-CATALOG (roster) · HANDOFFS (collab map) · ADOPTION · INTEGRATION (vendor into another repo) · CURATION (keep/genericize/drop) · adr/ · FOLLOWUPS
scripts/
  sync-copilot.sh          generate .github/agents wrappers (committed, drift-gated)
  validate_fleet.py        validate all skills/agents against the Agent Skills spec (the CI gate; pure stdlib)
  readonly-guard.py        PreToolUse hook: blocks state-changing + data-egress shell commands for read-only agents
.github/
  agents/                  GENERATED but COMMITTED + drift-gated in CI — edit .claude/ and re-run sync
```

## The fleet

**Agents (who):** `sde-engineer` · `code-reviewer` · `security-reviewer` · `test-engineer` ·
`sre-engineer` · `sre-monitor` · `release-engineer` · `runbook-author` · `database-reliability` ·
`researcher` · `prompt-engineer`. (Routing and incident-command are **skills** — `route-request`,
`incident-severity` — not agents.)

**Seniority/experience is carried by skills, not separate agents** — one `sde-engineer` and one
`sre-engineer` scale altitude by loading a ladder skill (one skill per track, three tier files):
- SDE — `sde-ladder`: senior → principal → distinguished
- SRE — `sre-ladder`: responder (new hire) → investigator (experienced) → elite

**Skills (how):**
- *Ladders* (2) · *Craft* (`craft` — one skill, six language files: Python/Bash/PowerShell/Go/TypeScript/React;
  plus `tdd-workflow`, `safe-refactor`, `debug-rca`, `self-improve-loop`) · *Data* (`database-reliability`)
- *Build ops tooling*: `ops-cli`, `api-design`, `spa-architecture`, `ops-stack-integration`
- *Agent-system methods (Anthropic patterns)*: `context-engineering`, `parallelization`, `tool-design`,
  `agent-security`, `prompt-craft`, `agent-architecture`
- *Observe/investigate (your stack)*: `triage-golden-signals`, `pcf-ops`, `splunk-triage`,
  `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation`, `thousandeyes-network`, `slo-error-budget`,
  `instrument-service`
- *Ship (your stack)*: `github-actions-ci`, `bamboo-to-actions-migration`, `pcf-deploy`, `rollback-mitigation`
- *Selectors & gates*: `route-request`, `merge-gate`, `release-gate`, `production-change-gate`
- *Incident process*: `incident-severity`, `blameless-postmortem`
- *Docs & conventions*: `runbook-template`, `blameless-postmortem`, `handoff-protocol`, `adr-template`

## Routing & gates

The `route-request` skill turns a request into an ordered delegation plan (run in the main session).
**Gates** are
pass/fail checkpoints that protect quality and prod: `merge-gate` before merge; `release-gate` +
`production-change-gate` before any prod deploy. Portable as checklists; hardenable via GitHub branch
protection / environment reviewers, or Claude Code hooks.

## Extending

Agents and skills are plain Markdown. Add a skill: create `.claude/skills/<name>/SKILL.md` (lowercase-
hyphen `name` ≤64 chars matching the dir, `description` ≤1024 chars saying *what + when*). Add an agent:
`.claude/agents/<name>.md` with `name`, `description`, `tools`, `model`. Re-run the sync script for
Copilot, then `python3 scripts/validate_fleet.py` to check it (or the upstream
[`skills-ref`](https://github.com/agentskills/agentskills) validator).

**Read-only enforcement:** Claude agents that keep `Bash` but must not change state wire
[scripts/readonly-guard.py](scripts/readonly-guard.py) as a `PreToolUse` hook in their frontmatter.
The Copilot generator strips Claude-only hooks and withholds `runCommands` from generated read-only
agents, so use `.github/agents/*.agent.md` when you want hard Copilot tool scoping. Verify the hook fires
in your Claude Code environment (the one piece that can't be unit-tested offline).

> **Hook shell:** the hook `command` (`"$(command -v python3 || command -v python)" -c …`) is **POSIX-shell
> syntax** — it assumes Claude Code runs hooks through `bash`/`sh` (our Linux + on-prem reality; CI is
> Linux-only). On a **Windows** checkout where Claude Code would invoke the hook via PowerShell, that
> command does not parse — adjust the frontmatter to a PowerShell-equivalent (or a small wrapper) for that
> environment. This only affects the *cooperative speed-bump*; the load-bearing controls (OS-level
> least-privilege creds + branch protection / protected environments) do not depend on the hook shell.

## Built from (current as of mid-2026)

- Claude Code [subagents](https://code.claude.com/docs/en/sub-agents) & [skills](https://code.claude.com/docs/en/skills)
- [Agent Skills open standard](https://agentskills.io/specification)
- VS Code [custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) & [agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [AGENTS.md](https://agents.md) cross-tool standard
- Patterns from `anthropics/anthropic-cookbook`, `ComposioHQ/awesome-claude-skills`, `affaan-m/ecc`
