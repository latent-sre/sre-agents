# SRE Agents

SRE Agents is a **Claude Code** fleet of **6 agents and 26 skills** for application engineering and
site reliability work. Everything lives under [`.claude/`](.claude/) as directly edited source —
there is no generator and no projection; the file you edit is the file the runtime loads.

## Layout

- [`.claude/agents/`](.claude/agents) — the six agent definitions (frontmatter carries the
  authority: `tools`, delegation grants, guard hooks).
- [`.claude/skills/`](.claude/skills) — the 26 Agent Skills with their `references/`, `assets/`,
  and `scripts/`.
- [`.claude/commands/adr.md`](.claude/commands/adr.md) — the manual ADR scaffold (`/adr`).
- [`scripts/`](scripts) — the structural gate (`gate_a.py`), the read-only allowlist guard
  (`readonly-guard.py` + launcher), and their tests.

Routing is native: agent descriptions select the lane; skills load by description match or `/name`.
The roster, enforcement model, and shared conventions are in [AGENTS.md](AGENTS.md).

## Fleet inventory

<!-- fleet-inventory:start -->
### Agents (6)

| Agent | Lane | Routing |
|---|---|---|
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer`; hands documentation to `sre-steward` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde`; terminal |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates steady-state work to `sre-steward`, fact checks to `researcher` |
| `sre-steward` | Steady state: observability as code + runbooks/postmortems (guarded Bash) | Hands active incidents to `sre`, automation to `sde`, lookups to `researcher` |
| `researcher` | Cited fact-finding and verification for any agent | Web + read only; returns to caller |
| `prompt-engineer` | The fleet's own files: agents, skills, descriptions, evals | Hands helper code to `sde`, injection review to `reviewer` |

### Skills (26)

| Skill | Purpose |
|---|---|
| `stack-profile` | Runtime, platform, and ownership boundaries |
| `root-cause` | Evidence-led debugging and causal analysis |
| `runbook` | Operational runbook method and template |
| `eng-ladder` | Engineering and incident-response altitude |
| `craft` | Language craft, testing, and safe refactoring |
| `backend-craft` | Backend API, persistence, auth, and background-work patterns |
| `frontend-craft` | Frontend architecture, data views, forms, and auth patterns |
| `ops-tooling` | Operations CLI and tool design |
| `pcf-ops` | Application-side PCF/TAS investigation |
| `pcf-deploy` | PCF deployment procedure |
| `database-reliability` | Database reliability investigation and design |
| `ci-actions` | GitHub Actions CI design and migration |
| `merge-gate` | Pre-merge quality checkpoint |
| `release-gate` | Release-readiness checkpoint |
| `production-change-gate` | Human authorization for production change |
| `incident-command` | Incident severity, roles, communications, and timeline |
| `postmortem` | Blameless post-incident learning |
| `service-onboarding` | Ordered service onboarding and audit |
| `agent-authoring` | Agent, skill, tool, prompt, and roster authoring |
| `agent-security` | Agentic threat modeling and boundary review |
| `obs-logs` | Log investigation and query design |
| `obs-metrics` | Metrics, SLIs, and query design |
| `obs-traces` | Distributed tracing and trace-query design |
| `obs-dashboards` | Dashboard design and provisioning |
| `obs-alerting` | Alerting, error budgets, and correlation |
| `obs-pipeline` | Telemetry collection and routing pipelines |
<!-- fleet-inventory:end -->

## Validate and evaluate

Run the single structural entrypoint (on Windows use `python` or `py -3`, never `python3` — the
Microsoft Store stub):

```powershell
py -3 scripts/gate_a.py
```

Gate A owns its step list; do not copy that list into documentation. Behavioral evaluations under
[`evals/`](evals) are intentionally manual and never run in CI. They execute only after source-trust and
disposable-harness requirements are satisfied.

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
