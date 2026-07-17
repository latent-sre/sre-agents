# SRE Agents

SRE Agents is a canonical fleet of **5 agents and 26 skills** for application engineering and site
reliability work. The repository authors one fleet and deterministically projects VS Code / GitHub
Copilot and Claude Code runtime definitions, placing the Copilot agents, prompts, and skills where
VS Code natively discovers them under `.github/`.

The canonical content is complete. Distribution, protected promotion, and pilot work are later phases
of the redesign and are not implied by this checkout. Generated projections are never hand-edited;
skills are the one runtime tree that is hand-authored — at its native `.github/skills/` discovery
path — because Agent Skills carry no per-runtime transform, so there is nothing to project.

## Authoring model

- [`canonical/fleet.json`](canonical/fleet.json) is the metadata, capability, dependency, and routing source.
- [`canonical/agents/`](canonical/agents) contains the five shared agent bodies.
- [`.github/skills/`](.github/skills) contains the 26 Agent Skills (references, assets, scripts),
  hand-authored at the VS Code native discovery path.
- [`.github/agents/`](.github/agents) and [`.github/prompts/`](.github/prompts) are generated Copilot
  projections (VS Code native discovery). [`generated/claude/`](generated/claude) holds the Claude
  projections and [`generated/copilot/commands/`](generated/copilot/commands) the Copilot CLI command
  form. Root and runtime manifests are generated too; do not edit any of them directly.
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
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
