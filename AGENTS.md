# SRE + SDE Agent Fleet

A portable roster of **AI agents and Agent Skills** for application software development and site
reliability work. The definitions live once under [`.claude/`](.claude/) and are read **natively by
both Claude Code and VS Code / GitHub Copilot**. [CLAUDE.md](CLAUDE.md) imports this file for Claude Code.

**Route work to the fleet — don't do it all in the main session.** Describe the task and it routes based on
each agent's `description`; for multi-step or ambiguous work invoke `/route-request` first to produce a
delegation plan. A production incident goes to `sre-engineer`, a diff to `code-reviewer`, code to
`sde-engineer` — delegate to the specialist rather than answering inline. Invoke a skill directly with
`/skill-name`.

This file is loaded into every session and carries the stack profile, the roster, routing/gates, and the
shared conventions. Repo mechanics (portability, validation, evals, how to add an agent or skill) live in
[README.md](README.md).

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
to its lane on demand. Each agent's own file is the detail — lane, tools, and the handoff targets it
routes to when work leaves its lane. Agents are not pinned to a model; they inherit the session's.

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
| [`prompt-engineer`](.claude/agents/prompt-engineer.md) | Author/optimize LLM-facing artifacts — agent definitions, skills, prompts, tool descriptions, evals (incl. this fleet) | prompt artifacts | `agent-authoring`, `tool-design`, `agent-security` |

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
> durable reason is **cost, not capability**: routing is a *low-context* task, so a coordinator *subagent*
> would only add a round-trip — the main session pays to spin one up, waits, then acts on its answer — for
> a decision it can make inline. (Not context-loss: routing needs little context, so that's not the
> disqualifier — the extra hop is.) True even now that Claude Code supports nested subagent dispatch.

> **Seniority/experience is carried by skills, not separate agents.** There is *one* `sde-engineer`
> and *one* `sre-engineer`. They scale altitude by loading a **ladder skill** — pick the tier that
> matches the task's ambiguity and blast radius.

## Skills

A skill is a folder under [`.claude/skills/`](.claude/skills/) with a `SKILL.md` (open
[Agent Skills](https://agentskills.io) standard). Each skill's *what + when* is its frontmatter
`description`. Match the task against the skill listing and load the one you need with the **`Skill`
tool**; you can also invoke one directly as `/skill-name`. The `sde-ladder`/`sre-ladder` skills set
your **altitude**: load the tier that matches the task's ambiguity and blast radius. (The roster of
skills by category is in [README.md](README.md#the-fleet).)

> **If you have no `Skill` tool, you will also have no skill listing** — you'd see skill *names* here
> with no trigger descriptions. In that case read the skill directly: `.claude/skills/<name>/SKILL.md`.
> Do **not** proceed from body prose alone; the skill carries the lane rules and safe-command lists.

## Routing & gates (selectors that control the workflow)

**Selectors** decide *who/what runs next*:
- the `route-request` skill (loaded by the main session) classifies a request → an ordered delegation plan
  (which agent, what context to pass, success criteria, sequencing).

**Gates** are checkpoints that must pass *before work advances* — they protect quality and prod:
- `merge-gate` — before a change merges: review clean, tests green, security reviewed if sensitive.
- `release-gate` — before a release/deploy: change record, rollback plan, health checks, comms ready.
- `production-change-gate` — change-management checkpoint for prod-facing actions: approval, blast
  radius, backout plan, comms. Maps to our (non-Google) ops/change-management reality.

Gates are checklists an agent runs; the load-bearing enforcement for prod is GitHub branch protection +
protected environments, not the checklist.

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

---

*Working on the fleet itself rather than with it? Portability, validation, evals, and how to add an
agent or skill are in [README.md](README.md).*
