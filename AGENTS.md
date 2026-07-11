# SRE + SDE Agent Fleet

A portable roster of **AI agents and Agent Skills** for application software development and site
reliability work. The definitions live once under [`.claude/`](.claude/) and are read **natively by
both Claude Code and VS Code / GitHub Copilot** (see [Portability](#portability)). This file
(`AGENTS.md`) is the cross-tool source of truth; [CLAUDE.md](CLAUDE.md) imports it for Claude Code.

## Stack profile — *the one block to edit when you retarget the fleet*

> **This section is the fleet's single stack-definition point.** Every agent and skill is written to
> the profile below; to adapt the fleet to a different team, edit **here** (and the per-skill
> `references/` fill-in files), not each agent body. The default profile is an on-prem PCF shop —
> retargeting it means rewriting this block, then the stack-specific skills (`pcf-*`, `splunk-*`,
> `wavefront-*`, `grafana-*`, `moogsoft-*`, `thousandeyes-*`, `*-deploy`) that name those tools.

**Default profile — scope:** We work on the **application operations** side — not infrastructure/platform
internals. Our runtime is **on-prem servers + PCF (VMware Tanzu Application Service)**. **No Kubernetes.**
Primary languages: **Python, Bash, PowerShell**. We optimize for *operations* maturity, pragmatic over
aspirational; we are deliberately not modeling Google-scale SRE.

**Default profile — tooling** (bake the active profile into every recommendation):

| Concern | What we use | Current product name to cite |
|---|---|---|
| Runtime / deploy target | **PCF** | VMware Tanzu Application Service (TAS); `cf` CLI v8 (CAPI V3) |
| Logs / SIEM | **Splunk** | Splunk (Cisco); SPL |
| Dashboards | **Grafana** | Grafana |
| Metrics / observability | **Wavefront** | VMware Aria Operations for Applications (WQL, `ts()`) |
| Event correlation / AIOps | **Moogsoft** | Dell APEX AIOps Incident Management (on-prem v9.x) |
| Network / synthetics | **ThousandEyes** | Cisco ThousandEyes |
| CI/CD | **GitHub + GitHub Actions** | migrating **off Bamboo** → Actions |

**Default profile — stay-in-lane rule:** Do **not** suggest Kubernetes, cloud-managed services, or
infra-layer fixes. Stay in the app/ops lane; hand platform-internal problems to the platform team.
*(A team on a different runtime edits this rule to match — e.g. a Kubernetes shop would invert it.)*

**Default profile — know the boundary.** We own our apps up to the platform edge; we do **not** operate
the platform itself — **BOSH, Ops Manager, Diego cells, Gorouter, CredHub/UAA, and foundation upgrades**
belong to the platform/infrastructure team. When a problem is platform-side (e.g. many apps failing at
once, failing cells, Gorouter-wide 5xx), our job is to **recognize it and escalate with evidence** —
timestamps, blast radius, and `cf` output showing our app is healthy — not to operate BOSH ourselves.
*(The boundary is the principle; the named components are this profile's — restate them for your platform.)*

## The roster (agents)

Agents are **who** does the work; [skills](#skills) are **how**. Each agent loads the skills relevant
to its lane on demand. Each agent's own file is the detail (lane · `model:` · tools · skills); for
who-hands-off-to-whom see [`docs/HANDOFFS.md`](docs/HANDOFFS.md).

| Agent | Lane | Writes? | Leans on (skills) |
|---|---|---|---|
| [`sde-engineer`](.claude/agents/sde-engineer.md) | Design/write/refactor/fix code (Py/Bash/PS/Go/TS); build ops tools (CLIs, API layers & SPA GUIs) | code | `sde-ladder`, `craft`, `ops-cli`, `api-design`, `spa-architecture`, `ops-stack-integration`, `database-reliability`, `tdd-workflow`, `safe-refactor`, `debug-rca`, `self-improve-loop`, `tool-design`, `adr-template` |
| [`code-reviewer`](.claude/agents/code-reviewer.md) | Correctness/quality review of a diff | no | `merge-gate` |
| [`security-reviewer`](.claude/agents/security-reviewer.md) | Security review (authz, injection, secrets, supply chain) | no | `agent-security` |
| [`test-engineer`](.claude/agents/test-engineer.md) | Author tests, raise meaningful coverage | tests | `tdd-workflow` |
| [`sre-engineer`](.claude/agents/sre-engineer.md) | Detection, triage, root-cause investigation | no | `sre-ladder`, `database-reliability`, stack skills |
| [`sre-monitor`](.claude/agents/sre-monitor.md) | Dashboards, SLOs, alert hygiene (steady state) | obs-as-code | `slo-error-budget`, `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation` |
| [`runbook-author`](.claude/agents/runbook-author.md) | Create/update operational runbooks | docs | `runbook-template`, `blameless-postmortem` |
| [`researcher`](.claude/agents/researcher.md) | Cited fact-finding & synthesis for any agent | no | `context-engineering` |
| [`prompt-engineer`](.claude/agents/prompt-engineer.md) | Author/optimize LLM-facing artifacts — agent definitions, skills, prompts, tool descriptions, evals (incl. this fleet) | prompt artifacts | `prompt-craft`, `agent-architecture`, `tool-design`, `agent-security` |

**Read-only agents** (no Edit/Write): `code-reviewer`, `security-reviewer`, `sre-engineer`, `researcher`.
They report, recommend, and hand off. The three that keep `Bash` for observation (`code-reviewer`,
`security-reviewer`, `sre-engineer`) run a `PreToolUse` guard
([scripts/readonly-guard.py](scripts/readonly-guard.py)) that **blocks common state-changing and egress
verbs** for a *cooperative* agent. This is **defense-in-depth, not a sandbox**: it raises the bar and
leaves an audit trail, but a determined or novel command can evade a denylist. The load-bearing control
is **OS-level least-privilege credentials + an outbound allowlist** at the host/network layer — the guard
is a fast speed-bump on top of that, not a substitute for it.

> **Routing and incident-command are *skills*, not agents.** `route-request` (planning a multi-step
> request) and `incident-severity` (running a live incident) run in the **main session's** context. The
> durable reason is cost, not capability: a coordinator *subagent* would double-pay the routing
> round-trip and discard the main session's live context that the work actually needs — true even now
> that Claude Code supports nested subagent dispatch.

> **Seniority/experience is carried by skills, not separate agents.** There is *one* `sde-engineer`
> and *one* `sre-engineer`. They scale altitude by loading a **ladder skill** — pick the tier that
> matches the task's ambiguity and blast radius.

### When is something an agent vs. a skill?

**Decision rule:** an **agent** exists when it needs a **distinct tool-scope**, a **distinct guard
posture**, **OR** is a **recurring, separable domain lane with its own handoff edges**; everything else
is a **skill**. The first two are mechanical (the harness enforces them); the third is editorial — a lane
worth routing to on its own. `prompt-engineer` is the lane case: its `tools:` overlap `sde-engineer`'s and
it carries no read-only guard, but fleet maintenance is a recurring, separable domain with its own handoff
edges. Seniority tiers, by contrast, share their agent's tool-scope *and* its lane, so they are ladder
*skills*, not cloned agents. A method that is not a separable lane — e.g. `database-reliability` — stays a
**skill** loaded by whichever agent needs it.

### The `skills:` frontmatter convention

Only some agents declare a `skills:` block, and that is **by design**. When present, it names the agent's
**single primary skill** for discoverability (`code-reviewer → merge-gate`, `test-engineer → tdd-workflow`).
It is **not** an exhaustive preload list — agents pick up the rest via description-based auto-load at
runtime, so an absent or single-entry `skills:` block is expected, not a gap. (Claude-only field.)

## Skills

A skill is a folder under [`.claude/skills/`](.claude/skills/) with a `SKILL.md` (open
[Agent Skills](https://agentskills.io) standard). Both tools auto-load a skill when a task matches its
`description`; you can also invoke one directly as `/skill-name`.

**`sde-ladder` — pick the SDE altitude (one skill, three tier files):**
- *senior* — scoped, well-defined changes inside one component; match patterns, test, ship.
- *principal* — cross-cutting design, blast-radius & call-site analysis, expand/contract migrations, API contracts.
- *distinguished* — org-wide technical strategy, build-vs-buy, standards, high-ambiguity multi-system architecture.

**`sre-ladder` — pick the SRE altitude (one skill, three tier files):**
- *responder* *(new hire)* — golden-signals triage, safe read-only checks, work the runbook, escalate well.
- *investigator* *(experienced)* — hypothesis-driven RCA, "what changed" correlation, test hypotheses against evidence.
- *elite* — systemic failure analysis, distributed-failure modes, resilience & detection-gap strategy.

Each skill's *what + when* lives in its frontmatter `description` — the listing every session already
loads — so the categories below carry **names only**. To read a skill, open its `SKILL.md`.

**Craft:** `craft` *(one skill, six language files: Python · Bash · PowerShell · Go · TypeScript · React)* ·
`tdd-workflow` · `safe-refactor` · `debug-rca` · `self-improve-loop`

**Build the ops side's tooling (pick the shape — CLI, HTTP API, and/or SPA GUI — then wire it to the
stack):** `ops-cli` · `api-design` · `spa-architecture` · `ops-stack-integration`. These turn the
fleet's read-only/automation capabilities into usable software; pair with the language `craft` skills.

**Agent-system methods (Anthropic agent patterns):** `context-engineering` · `parallelization` ·
`tool-design` · `agent-security` · `prompt-craft` · `agent-architecture`. Pairs with `self-improve-loop`.

**Data:** `database-reliability`

**Observe & investigate (your stack):** `pcf-ops` · `splunk-triage` ·
`wavefront-queries` · `grafana-dashboards` · `moogsoft-correlation` · `thousandeyes-network` ·
`slo-error-budget` · `instrument-service`

**Ship (your stack):** `github-actions-ci` · `bamboo-to-actions-migration` · `pcf-deploy` · `rollback-mitigation`

**Selectors & gates:** `route-request` · `merge-gate` · `release-gate` · `production-change-gate`

**Incident process:** `incident-severity` · `blameless-postmortem`

**Docs & conventions:** `runbook-template` · `blameless-postmortem` · `handoff-protocol` · `adr-template`

## Routing & gates (selectors that control the workflow)

**Selectors** decide *who/what runs next*:
- the `route-request` skill (loaded by the main session) classifies a request → an ordered delegation plan
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
  `test-engineer` → `merge-gate`, then a human release owner runs `release-gate` → `pcf-deploy` →
  `runbook-author` if new ops steps.
- **Production incident:** `sre-engineer` (triage + RCA) + `incident-severity` (severity, roles, comms, timeline);
  a human release owner executes mitigation (`rollback-mitigation`); `sde-engineer` fixes root cause;
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

Authored once under `.claude/`, consumed by both tools with **zero extra steps** — Claude Code and
VS Code / Copilot both read `.claude/agents/` and `.claude/skills/` directly:

| Artifact | Read by both tools |
|---|---|
| Agents | `.claude/agents/*.md` |
| Skills | `.claude/skills/*/SKILL.md` |
| Project guide | `CLAUDE.md` (Claude Code, imports this file) · `AGENTS.md` (other tools) |

The one non-portable seam is the agent `tools:` field (Claude uses `Read, Grep`; Copilot expects arrays
like `['edit','search/codebase']`), plus Claude-only `PreToolUse` hooks that don't cross to Copilot — so
a read-only agent's guard is enforced by hooks under Claude Code and must be enforced by tool scoping
under Copilot. Behavioral guardrails are written in each agent body and honored by both tools.

## Validate & operate

- **Validate the fleet:** `python3 scripts/validate_fleet.py` (pure stdlib) checks every skill/agent against the
  Agent Skills spec (names, descriptions, referenced files). Run it before committing.
- **Behavioral evals:** [`evals/`](evals/) holds scenario + grader pairs that check the fleet *behaves*
  (routing lands right, gates block, agents treat untrusted input as data). **Structural vs. behavioral:**
  the structural checks — `python evals/run_evals.py --validate` and
  `python evals/discovery_probe.py --validate` (suite lint), plus the read-only-guard tests and the
  grader/probe unit tests — run locally (this fleet ships no CI
  workflow). The **behavioral** runs (`run_evals.py --run`/`--ab`, discovery probing) need a
  Claude-enabled runner and are executed **manually or on a schedule.** Add a scenario when you add/change a skill
  **whose outcome is gradeable** (a gate that must block, a guard that must deny, a routing/refusal
  decision); grade the outcome, not the path. For prose-quality skills a keyword grader can't judge
  quality, so a scenario is optional there — don't write a tautological eval to satisfy a rule.
- **Starter runbooks** live in [`runbooks/`](runbooks/) (PCF OOM, 5xx-after-deploy, dependency
  timeout), authored with the `runbook-template` skill; fill placeholders before treating them as live.
- **Some skills bundle helpers:** `pcf-ops/scripts/triage.sh` / `triage.ps1` (read-only triage),
  `slo-error-budget/scripts/error_budget.py` (budget/burn calculator), starter templates under each
  skill's `assets/` (`api-design`, `ops-cli`, `pcf-deploy`, `github-actions-ci`), and `references/` fill-in files
  (`pcf-ops`, `splunk-triage`, `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation`,
  `thousandeyes-network`) for your concrete index/metric/foundation/dashboard/test values.

## Using it

- **Claude Code:** describe the task; it routes via each agent's `description`. For multi-step or
  ambiguous work, invoke `/route-request` first (or let it route). Invoke a skill directly with `/skill-name`.
- **VS Code / Copilot:** pick a custom agent from the Chat agents dropdown (or `/agents`); skills load
  automatically or via `/` in chat (both read `.claude/` directly).
- Agents and skills are plain Markdown — edit frontmatter (`tools`, `model`, `description`) or the body
  to tune behavior. Drop project-specific commands/links into the relevant skill.
