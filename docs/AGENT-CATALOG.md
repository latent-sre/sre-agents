# Agent catalog

Narrative descriptions of the 10 subagents in [`.claude/agents/`](../.claude/agents/) and the skills
each leans on. The terse roster table is in [`AGENTS.md`](../AGENTS.md); the collaboration map is in
[`HANDOFFS.md`](HANDOFFS.md); the *why* is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

> **Read-only agents** (no Edit/Write): `code-reviewer`, `security-reviewer`, `sre-engineer`,
> `researcher`. The three that keep `Bash` for observation are further constrained by
> `scripts/readonly-guard.py`, which blocks state-changing shell. The writers
> (`sde-engineer`, `test-engineer`, `database-reliability`, `sre-monitor`, `release-engineer`,
> `runbook-author`) edit files; prod-facing execution still needs human sign-off via the gates.
>
> **Routing and incident-command are *skills*, not agents** — `route-request` and `incident-severity`
> run in the main session (classic subagents can't dispatch; see [ARCHITECTURE.md](ARCHITECTURE.md) and
> [adr/0001](adr/0001-routing-and-incident-command-as-skills.md)).

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

### database-reliability · `opus` · writes migrations (prod gated)
The DBRE for our **on-prem databases**. Designs safe, reversible schema migrations and tunes query
performance; **writes** migration files and analysis but does **not** execute changes against a
production database — it hands the forward + rollback scripts to `release-engineer` to run under the
`production-change-gate`. Owns expand→contract migrations (loads `safe-refactor`), `EXPLAIN`/index/N+1
tuning, connection-pool/lock/replication-lag triage, and tested backups (RPO/RTO). Loads the
`database-reliability` skill for the engine-specific playbook; records engine/version specifics in
[`databases.md`](databases.md). Pairs with `sde-engineer` on query/ORM usage and `sre-engineer` on
DB-driven incidents.

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
> the main session — there is no `incident-commander` agent (it could only emit a plan it can't dispatch).

---

## Ship & docs lane

### release-engineer · `sonnet` · writes CI/infra (prod gated)
CI/CD, builds, deploys, rollbacks on our stack: GitHub Actions pipelines, Bamboo→Actions migration,
versioning/changelogs, PCF deploys via `cf` CLI (blue-green/rolling/canary), feature flags, and
rollbacks. **Executes** deploy/release actions — anything irreversible or prod-facing needs explicit
human confirmation (`release-gate` → `production-change-gate`). The hand-off target for fast incident
mitigation. Skills: `github-actions-ci`, `pcf-deploy`, `bamboo-to-actions-migration`,
`rollback-mitigation`, `release-gate`.

### runbook-author · `sonnet` · writes docs
Creates/updates operational runbooks — the step-by-step procedures on-call follows for an alert or
failure mode. Produces precise, copy-pasteable, verified procedures and keeps existing runbooks current.
Consumes findings from `sre-engineer` and `release-engineer`. Skills: `runbook-template`,
`blameless-postmortem`.

---

## Support

> **Routing is a skill, not an agent.** Multi-step/ambiguous requests are planned in the main session via
> `route-request` (with `parallelization` for what to fan out vs. keep sequential) — there is no
> `coordinator` agent (see [adr/0001](adr/0001-routing-and-incident-command-as-skills.md)).

### researcher · `sonnet` · read-only (no Bash)
Evidence-first fact-finding: official docs, specs/RFCs, vendor APIs, library behavior, version
differences, error-code meanings, and "how does X work / where is it" in-repo questions. Returns
concise **cited** answers, labels uncertainty, and **hands back** — it never edits code or systems.
Loads `context-engineering` — it's the fleet's context-offload, returning a brief instead of a transcript.

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
> *(Database depth, by contrast, earned its own agent — `database-reliability` — because DBRE work is a
> recurring, separable responsibility, not just an altitude.)*
