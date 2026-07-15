# SRE Agents

SRE Agents is a canonical fleet of **5 agents and 26 skills** for application engineering and site
reliability work. The repository authors one fleet and deterministically projects separate VS Code /
GitHub Copilot and Claude Code runtime definitions.

The canonical content is complete. Distribution, protected promotion, and pilot work are later phases
of the redesign and are not implied by this checkout. Never register a mutable authoring tree as a
runtime source.

## Authoring model

- [`canonical/fleet.json`](canonical/fleet.json) is the metadata, capability, dependency, and routing source.
- [`canonical/agents/`](canonical/agents) contains the five shared agent bodies.
- [`skills/`](skills) contains shared Agent Skills and their registered references, assets, and scripts.
- [`generated/copilot/`](generated/copilot) and [`generated/claude/`](generated/claude) are generated,
  runtime-specific projections. Root and runtime manifests are generated too; do not edit them directly.
- [`scripts/generate_fleet.py`](scripts/generate_fleet.py) generates and checks projections.

Runtime routing is native: agent descriptions select a lane, canonical `delegates_to` edges project each
runtime's delegation metadata, and canonical `handoffs` become explicit actions where supported. Claude
currently ignores a nested delegator's target list; compatibility records that degradation, while
terminal agents remain terminal by omitting `Agent` entirely.

## Fleet inventory

<!-- fleet-inventory:start -->
### Agents (5)

| Agent | Lane | Canonical routing |
|---|---|---|
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde` |
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer`; can hand documentation to `scribe` |
| `sre` | Investigate active production or staging failures | Delegates signal work to `observer` and incident documentation to `scribe` |
| `observer` | Build steady-state observability as code | Hands active incidents to `sre` and runbook work to `scribe` |
| `scribe` | Write runbooks and postmortems without executing commands | Hands automation requests to `sde` |

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

Run the single structural entrypoint from Windows:

```powershell
py -3 scripts/gate_a.py
```

Gate A owns its step list; do not copy that list into documentation. Behavioral evaluations under
[`evals/`](evals) are intentionally manual and never run in CI. They execute only after source-trust and
disposable-harness requirements are satisfied.

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The approved [design](docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md)
and [implementation plan](docs/superpowers/plans/2026-07-13-copilot-fleet-redesign.md) are the decision record.
