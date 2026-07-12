# SRE + SDE Agent Fleet

A portable fleet of **AI agents** and **Agent Skills** for application software development and site
reliability work — authored once and runnable in **both Claude Code and VS Code / GitHub Copilot**.

Shipped with a default **stack profile** for an **application-operations** team on **on-prem servers +
PCF (Tanzu Application Service)**, no Kubernetes, working primarily in **Python, Bash, and PowerShell**,
with **Splunk, Grafana, Wavefront, Moogsoft, ThousandEyes**, deploying via **GitHub Actions** (migrating
off Bamboo). The whole fleet is written to that one profile — **retarget it for your team by editing the
single [Stack profile](AGENTS.md#stack-profile--the-one-block-to-edit-when-you-retarget-the-fleet) block
in AGENTS.md**, then rewriting the stack-specific skills (`pcf-*`, `splunk-*`, `wavefront-*`, `grafana-*`,
`moogsoft-*`, `thousandeyes-*`, `*-deploy`) that name those tools by hand.

> Full design + conventions: **[AGENTS.md](AGENTS.md)**. Claude Code entrypoint: **[CLAUDE.md](CLAUDE.md)**.

## Why this works in both tools

The portability is real, not aspirational — it rides two current open standards:

- **Agent Skills (`SKILL.md`)** — an open standard ([agentskills.io](https://agentskills.io), published
  by Anthropic Dec 2025, adopted by 30+ tools). Both VS Code/Copilot and Claude Code read skills from
  `.claude/skills/` directly.
- **Agents** — VS Code/Copilot custom agents and Claude Code both read `.claude/agents/` directly.

So a single source under `.claude/` is read natively by both, with no build step. `AGENTS.md` is the
cross-tool project guide.

## Quick start

**Claude Code** — open the repo. Describe a task; it routes by each agent's `description`. Or be explicit:
- *"Use the sre-engineer to triage this alert."*  ·  invoke `/route-request` to plan a multi-step task.
- Invoke a skill directly: `/release-gate`, `/pcf-ops`, `/merge-gate`.

**VS Code / GitHub Copilot** — open the repo; pick a custom agent from the Chat agents dropdown (skills
load automatically or via `/`). Both tools read `.claude/` directly — no build step.

**Vendor it into an existing repo** — to embed the fleet as a subdirectory of another project (rather than
using it standalone), see **[docs/INTEGRATION.md](docs/INTEGRATION.md)**: the scripts are location-robust,
but `.claude/`, `CLAUDE.md`, and `AGENTS.md` must be surfaced at the host repo's root.

## Layout

```
AGENTS.md                  what an agent needs while working (stack profile, roster, conventions, routing/gates)
CLAUDE.md                  Claude Code entrypoint (imports AGENTS.md + Claude specifics)
.claude/
  agents/                  the agent roster — read by Claude Code AND VS Code/Copilot
  skills/                  the skills (SKILL.md open standard) — read by both tools
                           some bundle scripts/ (pcf-ops Bash/PowerShell, slo-error-budget) and references/ fill-ins
evals/                     behavioral evals (scenarios + graders) — routing, gates, security; run locally
docs/                       INTEGRATION (vendor into another repo) · RESEARCH (sources)
scripts/
  validate_fleet.py        validate all skills/agents against the Agent Skills spec (pure stdlib)
  readonly-guard.py        PreToolUse hook: blocks state-changing + data-egress shell commands for read-only agents
```

## The fleet

**Agents (who):** `sde-engineer` · `code-reviewer` · `security-reviewer` · `test-engineer` ·
`sre-engineer` · `sre-monitor` · `runbook-author` · `researcher` · `prompt-engineer`. (Routing and
incident-command are **skills** — `route-request`, `incident-severity` — not agents.)

**Seniority/experience is carried by skills, not separate agents** — one `sde-engineer` and one
`sre-engineer` scale altitude by loading a ladder skill (one skill per track, three tier files):
- SDE — `sde-ladder`: senior → principal → distinguished
- SRE — `sre-ladder`: responder (new hire) → investigator (experienced) → elite

**Skills (how):**
- *Ladders* (2) · *Craft* (`craft` — one skill, six language files: Python/Bash/PowerShell/Go/TypeScript/React;
  plus `tdd-workflow`, `safe-refactor`, `debug-rca`, `self-improve-loop`) · *Data* (`database-reliability`)
- *Build ops tooling*: `ops-cli`, `api-design`, `spa-architecture`, `ops-stack-integration`
- *Agent-system methods (Anthropic patterns)*: `agent-authoring` (one skill, two tiers: artifact ·
  roster) · `context-engineering` · `tool-design` · `agent-security`
- *Observe/investigate (your stack)*: `pcf-ops`, `splunk-triage`,
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
`.claude/agents/<name>.md` with `name`, `description`, and `tools` (no `model:` — agents inherit the
session's model). Then run
`python3 scripts/validate_fleet.py` to check it (or the upstream
[`skills-ref`](https://github.com/agentskills/agentskills) validator).

**Agent or skill?** An **agent** exists when it needs a distinct tool-scope, a distinct guard posture, or
is a recurring, separable domain lane with its own handoff edges. Everything else — altitude, method,
checklist, playbook — is a **skill**. The full decision rule (and the roster-design method around it)
lives in the [`agent-authoring`](.claude/skills/agent-authoring/SKILL.md) skill, roster tier.

**The `skills:` frontmatter convention.** Only some agents declare a `skills:` block, and that is **by
design**. When present it names the agent's *single primary* skill to **preload**: Claude Code injects
that skill's **full content** (not just its description) into the agent up front — an always-on token
cost — so an agent names only the one skill it always needs (`code-reviewer → merge-gate`,
`test-engineer → tdd-workflow`). Every *other* skill loads **on demand** via the `Skill` tool, so an
absent or single-entry block is expected, not a gap. Note `skills:` preloads content; it does **not**
grant invocation — that's the `Skill` tool in `tools:`. (Claude-only field.)

**The one non-portable seam** is the agent `tools:` field: Claude uses `Read, Grep`; Copilot expects
arrays like `['edit','search/codebase']`. Claude-only `PreToolUse` hooks don't cross to Copilot either.
Behavioral guardrails are written in each agent body and honored by both tools.

**Read-only enforcement:** Claude agents that keep `Bash` but must not change state wire
[scripts/readonly-guard-hook.sh](scripts/readonly-guard-hook.sh) as a `PreToolUse` hook in their
frontmatter; it launches [scripts/readonly-guard.py](scripts/readonly-guard.py). Under Copilot, where
Claude hooks don't apply, enforce the same read-only posture via the agent's `tools` scoping instead.

> **The guard was silently dead on Windows (fixed 2026-07-11).** The hook used to be an inline
> `"$(command -v python3 || command -v python)" -c …`. On Windows `command -v python3` **succeeds** —
> it resolves the **Microsoft Store alias stub** (on by default in Win 10/11) — so the `|| python`
> fallback never fired, the stub exited non-zero, the guard never ran, **no decision was emitted, and
> Claude Code let the command through.** Read-only agents had **no guard**, silently. The launcher now
> picks an interpreter that *works* (not one that merely *resolves*) and **fails CLOSED** — if it can't
> start, it denies. `scripts/test_readonly_guard.py` exercises the **launcher**, not just the script
> (3 cases: deny / allow / fail-closed), because testing the script never tested the wiring — that is
> precisely how this shipped. Note the guard is a *cooperative speed-bump*: the load-bearing controls
> are OS-level least-privilege credentials + branch protection / protected environments.

## Validate & operate

- **Validate the fleet:** `python3 scripts/validate_fleet.py` (pure stdlib) checks every skill/agent
  against the Agent Skills spec (names, descriptions, referenced files) and enforces roster-doc
  coverage. Run it before committing.
- **Evals:** [`evals/`](evals/) holds scenario + grader pairs that check the fleet *behaves* (routing
  lands right, gates block, agents treat untrusted input as data). The **structural** checks run locally
  and offline — `run_evals.py --validate`, `discovery_probe.py --validate`, the read-only-guard tests,
  and the grader/probe unit tests. The **behavioral** runs (`run_evals.py --run`/`--ab`, discovery
  probing) need a Claude-enabled runner and are executed manually or on a schedule. This fleet ships no
  CI workflow. Add a scenario when you add or change a skill **whose outcome is gradeable** (a gate that
  must block, a guard that must deny, a routing/refusal decision) — grade the outcome, not the path. For
  prose-quality skills a keyword grader can't judge quality, so don't write a tautological eval to
  satisfy a rule.
- **Delegation canary:** `AGENTS.md` and agent `description`s are delegation-load-bearing. After editing
  either, re-run `python evals/discovery_probe.py --run --agents --match sre-engineer` in a throwaway
  worktree. The 2026-07 AGENTS.md trim dropped incident delegation from 9/9 to 3/9 *[unverified: manual
  A/B run, n=9; no committed transcript/seed/model-id]* while every structural check stayed green — only
  this probe caught it.
- **Some skills bundle helpers:** `pcf-ops/scripts/triage.sh` / `triage.ps1` (read-only triage),
  `slo-error-budget/scripts/error_budget.py` (budget/burn calculator), starter templates under each
  skill's `assets/` (`api-design`, `ops-cli`, `pcf-deploy`, `github-actions-ci`), and `references/`
  fill-in files (`pcf-ops`, `splunk-triage`, `wavefront-queries`, `grafana-dashboards`,
  `moogsoft-correlation`, `thousandeyes-network`) for your concrete index/metric/foundation values.

## Built from (current as of mid-2026)

- Claude Code [subagents](https://code.claude.com/docs/en/sub-agents) & [skills](https://code.claude.com/docs/en/skills)
- [Agent Skills open standard](https://agentskills.io/specification)
- VS Code [custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) & [agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [AGENTS.md](https://agents.md) cross-tool standard
- Patterns from `anthropics/anthropic-cookbook`, `ComposioHQ/awesome-claude-skills`, `affaan-m/ecc`
