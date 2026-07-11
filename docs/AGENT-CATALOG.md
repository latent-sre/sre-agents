# Agent catalog

Narrative descriptions of the subagents in [`.claude/agents/`](../.claude/agents/) and the skills
each leans on. The terse roster table is in [`AGENTS.md`](../AGENTS.md); the collaboration map is in
[`HANDOFFS.md`](HANDOFFS.md); the *why* is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

> **Read-only agents** (no Edit/Write): `code-reviewer`, `security-reviewer`, `sre-engineer`,
> `researcher`. The three that keep `Bash` for observation are further constrained by
> `scripts/readonly-guard.py`, which blocks state-changing shell. The writers
> (`sde-engineer`, `test-engineer`, `sre-monitor`, `runbook-author`, `prompt-engineer`) edit files;
> prod-facing execution still needs human sign-off via the gates.
>
> **Routing and incident-command are *skills*, not agents** — `route-request` and `incident-severity`
> run in the main session (a coordinator subagent would double-pay the routing round-trip and discard
> the main session's live context — cost, not a capability limit; see [ARCHITECTURE.md](ARCHITECTURE.md)).

---

## SDE lane

### sde-engineer · `opus` · writes code
The team's software engineer (Python/Bash/PowerShell, and Go/TypeScript/React when a repo uses them).
Reads existing code first, matches conventions, writes tests, ships clean reviewable diffs. **Scales
altitude by loading the `sde-ladder` skill at the matching tier** — senior (scoped work), principal
(cross-cutting design & migrations), distinguished (org-wide/high-ambiguity architecture).
Loads the language `craft` skill for what it touches, `database-reliability` for schema/DB work,
`tdd-workflow` for test-first, `safe-refactor` and `debug-rca` as needed, `self-improve-loop` to
iterate against measurable criteria, and `tool-design` when building a tool/MCP integration. For the
growing mandate to **build the ops side's tooling as software**, picks the shape — `ops-cli` (CLI),
`api-design` (the contract-first HTTP layer), `spa-architecture` (the SPA GUI over it) — and loads
`ops-stack-integration` for the hard part: calling cf/Splunk/Wavefront/Moogsoft safely. Hands off
to `code-reviewer` before "done."

### code-reviewer · `opus` · read-only (guarded)
Rigorous correctness/quality review of a diff before merge. Hunts real bugs, edge cases, contract
breaks, and missing tests; ranks findings by severity and confidence; suggests fixes but **does not edit
code**. Backs the `merge-gate`. Hands security-deep concerns to `security-reviewer`.

### security-reviewer · `opus` · read-only (guarded)
Security-focused review: authn/authz, injection (SQLi/XSS/command/path/SSRF), secrets, crypto,
deserialization, dependency/supply-chain risk, PII exposure. Reports vulnerabilities with severity and
remediation; **read-only**. Loads `agent-security` when the change is an agent definition, a tool/MCP
integration, or a flow that ingests untrusted content (prompt injection, the lethal trifecta). The
hand-off target from `code-reviewer` when depth is needed.

### test-engineer · `sonnet` · writes tests
Designs and writes tests that actually catch bugs, raising meaningful coverage across Python, Bash,
PowerShell, TypeScript/React, and Go. Tests behavior and contracts, not internals. Loads `tdd-workflow`
and the language `craft` skills. Edits **test code only** — hands real fixes to `sde-engineer`.

> **Database reliability is a *skill*, not an agent.** DBRE work — safe, reversible schema migrations,
> `EXPLAIN`/index/N+1 tuning, connection-pool/lock/replication-lag triage, tested backups (RPO/RTO) — is
> carried by the `database-reliability` skill, loaded by `sde-engineer` (schema/query work) and
> `sre-engineer` (DB-driven incidents). Migration scripts still hand off forward + rollback to a human
> release owner under the `production-change-gate`.

---

## SRE lane

### sre-engineer · `opus` · read-only (guarded)
Detection-signal interpretation, triage/severity, and structured root-cause investigation when
something is wrong in prod/staging. Forms and tests hypotheses against Splunk, Wavefront/Grafana,
events, ThousandEyes, and recent changes. **Scales by the `sre-ladder` skill** — responder (first
response), investigator (hypothesis-driven RCA), elite (systemic/distributed
failure). Loads `triage-golden-signals`, the stack skills (`pcf-ops`, `splunk-triage`,
`wavefront-queries`, `moogsoft-correlation`, `thousandeyes-network`), and `database-reliability` for
DB-driven incidents. **Recommends mitigation; does not change prod.**

### sre-monitor · `sonnet` · writes obs-as-code
Steady-state observability: Grafana dashboards, Wavefront/Splunk alert tuning, SLIs/SLOs and error
budgets, Moogsoft correlation to cut noise, ThousandEyes synthetics. Owns alert rules, dashboard JSON,
and SLO configs. Skills: `slo-error-budget`, `wavefront-queries`, `grafana-dashboards`,
`moogsoft-correlation`. The agent that **closes detection gaps** after an incident.

> **Running a live incident is a skill, not an agent.** `incident-severity` (SEV1–4 rubric, comms
> cadence, roles, the live timeline, drive-to-mitigation) is loaded by `sre-engineer` or a human IC in
> the main session — there is no `incident-commander` agent (isolating it from the investigation would
> double-pay the round-trip and strand it from the live incident context it needs).

---

## Docs lane

> **Ship/deploy is skill-driven, not an agent.** With no `release-engineer` agent, CI/CD and PCF
> deploys/rollbacks are human-run using the kept playbooks — `github-actions-ci`, `pcf-deploy`,
> `bamboo-to-actions-migration`, `rollback-mitigation`, `release-gate` — gated by `production-change-gate`
> and the `production-change-guard.py` hook wired onto whatever runs `cf`.

### runbook-author · `sonnet` · writes docs
Creates/updates operational runbooks — the step-by-step procedures on-call follows for an alert or
failure mode. Produces precise, copy-pasteable, verified procedures and keeps existing runbooks current.
Consumes findings from `sre-engineer`. Skills: `runbook-template`, `blameless-postmortem`.

---

## Support

> **Routing is a skill, not an agent.** Multi-step/ambiguous requests are planned in the main session via
> `route-request` (with `parallelization` for what to fan out vs. keep sequential) — there is no
> `coordinator` agent (see [ARCHITECTURE.md](ARCHITECTURE.md)).

### researcher · `sonnet` · read-only (no Bash)
Evidence-first fact-finding: official docs, specs/RFCs, vendor APIs, library behavior, version
differences, error-code meanings, and "how does X work / where is it" in-repo questions. Returns
concise **cited** answers, labels uncertainty, and **hands back** — it never edits code or systems.
Loads `context-engineering` — it's the fleet's context-offload, returning a brief instead of a transcript.

### prompt-engineer · `opus` · writes prompt artifacts
Owns the artifacts other agents run on: agent definitions, SKILL.md files, system prompts, tool
descriptions, and eval/grader prompts — including this fleet's own files and any LLM-facing text in
the ops tooling the team builds. Treats a prompt as a spec: reproduce the failure, diagnose its form
(trigger / shape / omission / pressure-violation), make the minimal edit, retest fresh. **Scales by
skill, not clones**: `prompt-craft` for a single artifact, `agent-architecture` for roster/orchestration
design; also loads `tool-design`, `context-engineering`, `agent-security`, and `self-improve-loop` as
the failure demands. Hands helper code to `sde-engineer`, gate/guard wording changes to `code-reviewer`,
and injection surfaces to `security-reviewer`.

> **Why it's an agent (the `agent-architecture` test):** a recurring, *separable* lane with its own
> handoff edges (← any agent reporting a misbehaving artifact; → `security-reviewer` / `sde-engineer` /
> `code-reviewer`) — the fleet's own maintenance is a domain, not an altitude. Its two skills stay
> skills because they're methods, not lanes.

---

## Recommended future agents (not yet built)

Tailored to a pragmatic, on-prem/PCF, ops-heavy team — listed by value. Add one only when a recurring,
*separable* responsibility justifies the context isolation.

1. **On-call / alert front-end** — first-pass noise suppression and cross-source correlation
   (Splunk/Grafana/Wavefront/Moogsoft/ThousandEyes), enriching pages with context before a human reads
   them. Detection is where most incidents are won or lost; today this is split across `sre-monitor` +
   the `moogsoft-correlation` skill.
2. **Performance / capacity engineer** — reads Wavefront/Grafana history to forecast saturation and
   right-size PCF foundations/cells and self-hosted runners (no elastic autoscaling to lean on).
   Currently the tail end of `sre-monitor`'s lane.
3. **Documentation / knowledge agent** — keeps `AGENTS.md`, `CLAUDE.md`, runbooks, and these docs
   current; the natural consumer of every other agent's output. Today this is `runbook-author` plus
   manual upkeep.

> **Deliberately *not* separate agents:** seniority tiers — they're `sde-ladder`/`sre-ladder` skills loaded by the
> single `sde-engineer`/`sre-engineer`, not cloned junior/senior/principal agents (see [ARCHITECTURE.md](ARCHITECTURE.md) → *Design principles* #2).
