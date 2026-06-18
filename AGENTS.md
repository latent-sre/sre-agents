# SRE + SDE Agent Fleet

A portable roster of **AI agents and Agent Skills** for application software development and site
reliability work. The definitions live once under [`.claude/`](.claude/) and are read **natively by
both Claude Code and VS Code / GitHub Copilot** (see [Portability](#portability)). This file
(`AGENTS.md`) is the cross-tool source of truth; [CLAUDE.md](CLAUDE.md) imports it for Claude Code.

> **Scope:** We work on the **application operations** side — not infrastructure/platform internals.
> Our runtime is **on-prem servers + PCF (VMware Tanzu Application Service)**. **No Kubernetes.**
> Primary languages: **Python, Bash, PowerShell**. We optimize for *operations* maturity, pragmatic
> over aspirational; we are deliberately not modeling Google-scale SRE.

## Environment (bake this into every recommendation)

| Concern | What we use | Current product name to cite |
|---|---|---|
| Runtime / deploy target | **PCF** | VMware Tanzu Application Service (TAS); `cf` CLI v8 (CAPI V3) |
| Logs / SIEM | **Splunk** | Splunk (Cisco); SPL |
| Dashboards | **Grafana** | Grafana |
| Metrics / observability | **Wavefront** | VMware Aria Operations for Applications (WQL, `ts()`) |
| Event correlation / AIOps | **Moogsoft** | Dell APEX AIOps Incident Management (on-prem v9.x) |
| Network / synthetics | **ThousandEyes** | Cisco ThousandEyes |
| CI/CD | **GitHub + GitHub Actions** | migrating **off Bamboo** → Actions |

Do **not** suggest Kubernetes, cloud-managed services, or infra-layer fixes. Stay in the app/ops lane;
hand platform-internal problems to the platform team.

## The roster (agents)

Agents are **who** does the work; [skills](#skills) are **how**. Each agent loads the skills relevant
to its lane on demand.

| Agent | Lane | Writes? | Leans on (skills) |
|---|---|---|---|
| [`coordinator`](.claude/agents/coordinator.md) | Route a request → delegation plan | no | `route-request` |
| [`sde-engineer`](.claude/agents/sde-engineer.md) | Design/write/refactor/fix code (Py/Bash/PS/Go/TS) | code | `sde-ladder-*`, `*-craft`, `database-reliability`, `tdd-workflow`, `safe-refactor`, `debug-rca` |
| [`code-reviewer`](.claude/agents/code-reviewer.md) | Correctness/quality review of a diff | no | `merge-gate` |
| [`security-reviewer`](.claude/agents/security-reviewer.md) | Security review (authz, injection, secrets, supply chain) | no | — |
| [`test-engineer`](.claude/agents/test-engineer.md) | Author tests, raise meaningful coverage | tests | `tdd-workflow` |
| [`database-reliability`](.claude/agents/database-reliability.md) | Safe schema migrations, query perf, durability (on-prem DBs) | code (migrations) | `database-reliability`, `safe-refactor`, `production-change-gate` |
| [`sre-engineer`](.claude/agents/sre-engineer.md) | Detection, triage, root-cause investigation | no | `sre-ladder-*`, `triage-golden-signals`, `database-reliability`, stack skills |
| [`sre-monitor`](.claude/agents/sre-monitor.md) | Dashboards, SLOs, alert hygiene (steady state) | obs-as-code | `slo-error-budget`, `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation` |
| [`incident-commander`](.claude/agents/incident-commander.md) | Run the *process* of a live incident | no | `incident-severity`, `blameless-postmortem` |
| [`release-engineer`](.claude/agents/release-engineer.md) | CI/CD, deploys, rollbacks (Actions + PCF) | infra/CI | `github-actions-ci`, `pcf-deploy`, `bamboo-to-actions-migration`, `rollback-mitigation`, `release-gate` |
| [`runbook-author`](.claude/agents/runbook-author.md) | Create/update operational runbooks | docs | `runbook-template`, `blameless-postmortem` |
| [`researcher`](.claude/agents/researcher.md) | Cited fact-finding & synthesis for any agent | no | — |

**Read-only agents** (no Edit/Write): `coordinator`, `code-reviewer`, `security-reviewer`,
`sre-engineer`, `incident-commander`, `researcher`. They report, recommend, and hand off. The four that
keep `Bash` for observation (`code-reviewer`, `security-reviewer`, `sre-engineer`, `incident-commander`)
are further constrained by a `PreToolUse` guard ([scripts/readonly-guard.py](scripts/readonly-guard.py))
that **blocks state-changing shell commands** — so "read-only" is enforced, not just promised.

> **Seniority/experience is carried by skills, not separate agents.** There is *one* `sde-engineer`
> and *one* `sre-engineer`. They scale altitude by loading a **ladder skill** — pick the tier that
> matches the task's ambiguity and blast radius.

## Skills

A skill is a folder under [`.claude/skills/`](.claude/skills/) with a `SKILL.md` (open
[Agent Skills](https://agentskills.io) standard). Both tools auto-load a skill when a task matches its
`description`; you can also invoke one directly as `/skill-name`.

**Ladders — pick the altitude (SDE):**
- `sde-ladder-senior` — scoped, well-defined changes inside one component; match patterns, test, ship.
- `sde-ladder-principal` — cross-cutting design, blast-radius & call-site analysis, expand/contract migrations, API contracts.
- `sde-ladder-distinguished` — org-wide technical strategy, build-vs-buy, standards, high-ambiguity multi-system architecture.

**Ladders — pick the altitude (SRE):**
- `sre-ladder-responder` *(new hire)* — golden-signals triage, safe read-only checks, work the runbook, escalate well.
- `sre-ladder-investigator` *(experienced)* — hypothesis-driven RCA, "what changed" correlation, test hypotheses against evidence.
- `sre-ladder-elite` — systemic failure analysis, distributed-failure modes, resilience & detection-gap strategy.

**Craft:** `python-craft` · `bash-craft` · `powershell-craft` · `go-craft` · `typescript-craft` ·
`react-craft` · `tdd-workflow` · `safe-refactor` · `debug-rca`

**Data:** `database-reliability` — safe (online/reversible, expand→contract) schema migrations, query/
index tuning, connection-pool/lock/replication-lag triage, and tested backups (RPO/RTO).

**Observe & investigate (your stack):** `triage-golden-signals` · `pcf-ops` · `splunk-triage` ·
`wavefront-queries` · `grafana-dashboards` · `moogsoft-correlation` · `thousandeyes-network` ·
`slo-error-budget` · `instrument-service` *(emit telemetry: RED/USE, OTel, cardinality)*

**Ship (your stack):** `github-actions-ci` · `bamboo-to-actions-migration` · `pcf-deploy` · `rollback-mitigation`

**Selectors & gates:** `route-request` · `merge-gate` · `release-gate` · `production-change-gate`

**Incident process:** `incident-severity` *(SEV1–4 rubric + comms cadence)* · `blameless-postmortem`

**Docs & conventions:** `runbook-template` · `blameless-postmortem` · `handoff-protocol` · `adr-template` *(ADR/RFC decision capture)*

## Routing & gates (selectors that control the workflow)

**Selectors** decide *who/what runs next*:
- `coordinator` agent + `route-request` skill classify a request → an ordered delegation plan
  (which agent, what context to pass, success criteria, sequencing).

**Gates** are checkpoints that must pass *before work advances* — they protect quality and prod:
- `merge-gate` — before a change merges: review clean, tests green, security reviewed if sensitive.
- `release-gate` — before a release/deploy: change record, rollback plan, health checks, comms ready.
- `production-change-gate` — change-management checkpoint for prod-facing actions: approval, blast
  radius, backout plan, comms. Maps to our (non-Google) ops/change-management reality.

Gates are portable Markdown checklists by default. In Claude Code they can be **hardened with hooks**
(e.g. block the `pcf-deploy` skill unless `release-gate` passed) — see
[`scripts/`](scripts/) and CLAUDE.md. Copilot enforcement is via the agent body + generated tool scoping
(read-only generated agents do not receive terminal access).

### Typical flows
- **Ship a feature:** `sde-engineer` → `code-reviewer` (+`security-reviewer` if sensitive) →
  `test-engineer` → `merge-gate` → `release-engineer` (`release-gate` → `pcf-deploy`) →
  `runbook-author` if new ops steps.
- **Production incident:** `sre-engineer` (triage + RCA) ⇄ `incident-commander` (process/comms);
  `release-engineer` executes mitigation (`rollback-mitigation`); `sde-engineer` fixes root cause;
  `runbook-author` captures it; `sre-monitor` closes the detection gap.
- **Reliability hardening:** `sre-monitor` defines SLOs/alerts → `runbook-author` links runbooks.

## Shared conventions (every agent follows)

- **Single responsibility & least privilege.** Each agent owns one lane; read-only agents get no write
  tools. Widen tool lists only with reason.
- **Hand off, don't sprawl.** When work leaves your lane, name the target agent and package the context
  they need to start cold (intent, what's done, what you found). See `handoff-protocol`.
- **Evidence over assertion.** Cite `file:line` or a command's output for load-bearing claims; label
  anything unverified. Never fabricate test results, citations, query output, or system state.
- **Report your verification, uniformly.** When you produce a result, state *what you actually ran or
  checked*, the outcome, and *what you could not verify* — don't make the reader infer it. Label
  load-bearing claims `[verified]` (you ran/observed it — show the command/output), `[sourced]`
  (a citation: `file:line`, URL, query), or `[unverified]` (assumption/couldn't check — never upgrade
  these to fact). "Couldn't verify" is a required, explicit part of every result, even if it's "nothing
  material." `researcher`'s output contract is the model; the gates and `handoff-protocol` carry this
  evidence forward so it doesn't evaporate between agents.
- **Safety first.** Destructive or prod-facing actions (deploys, deletes, traffic cuts, `cf` writes)
  require explicit human confirmation; show the plan + rollback before acting.
- **Lead with the conclusion**, then evidence, then next steps / recommended hand-offs.
- **Blameless** language for all incident/operations work.

## Portability

Authored once under `.claude/`, consumed by both tools:

| Artifact | Claude Code reads | VS Code / Copilot reads |
|---|---|---|
| Agents | `.claude/agents/*.md` | `.claude/agents/` **and** `.github/agents/*.agent.md` |
| Skills | `.claude/skills/*/SKILL.md` | `.claude/skills/`, `.github/skills/`, `.agents/skills/` |
| Project guide | `CLAUDE.md` (imports this file) | `AGENTS.md` |
| Copilot conventions | (see AGENTS.md) | [`.github/copilot-instructions.md`](.github/copilot-instructions.md) |

Both tools read `.claude/` directly, so the fleet works in Copilot with **zero extra steps**. For
Copilot-native tool scoping (`.agent.md` arrays, `handoffs`, `target`) run the generator:

```bash
# from repo root — emits .github/agents/*.agent.md and mirrors skills to .github/skills/
pwsh scripts/sync-copilot.ps1      # Windows / PowerShell
bash scripts/sync-copilot.sh       # macOS / Linux
```

The only non-portable seam is the agent `tools:` field (Claude uses `Read, Grep`; Copilot uses arrays
like `['edit','search/codebase']`). Behavioral guardrails are written in each agent body (honored by
both); the generator translates `tools` for Copilot and removes terminal access from read-only agents
because Claude hooks are not portable.

## Validate & operate

- **Validate the fleet:** `pwsh scripts/validate-fleet.ps1` checks every skill/agent against the
  Agent Skills spec (names, descriptions, referenced files). Run it before committing or in CI.
- **Starter runbooks** live in [`runbooks/`](runbooks/) (PCF OOM, 5xx-after-deploy, dependency
  timeout), authored with the `runbook-template` skill; fill placeholders before treating them as live.
- **Some skills bundle helpers:** `pcf-ops/scripts/triage.sh` / `triage.ps1` (read-only triage),
  `slo-error-budget/scripts/error_budget.py` (budget/burn calculator), and `references/` fill-in files
  (`pcf-ops`, `splunk-triage`, `wavefront-queries`) for your concrete index/metric/foundation values.

## Using it

- **Claude Code:** describe the task; it routes via each agent's `description`. For multi-step or
  ambiguous work, ask it to *"use the coordinator"* first. Invoke a skill directly with `/skill-name`.
- **VS Code / Copilot:** pick a custom agent from the Chat agents dropdown (or `/agents`); skills load
  automatically or via `/` in chat. Run the generator first if you want `.github/agents` wrappers.
- Agents and skills are plain Markdown — edit frontmatter (`tools`, `model`, `description`) or the body
  to tune behavior. Drop project-specific commands/links into the relevant skill.
