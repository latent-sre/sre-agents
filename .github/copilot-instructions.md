# Copilot instructions — SRE + SDE Agent Fleet

This repo ships a portable fleet of custom agents (`.claude/agents/`) and Agent Skills
(`.claude/skills/`) that VS Code / GitHub Copilot reads natively. Full guide: [AGENTS.md](../AGENTS.md);
design rationale in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Scope & stack (apply to every suggestion)
- Application-operations team: **on-prem servers + PCF / Tanzu Application Service** (`cf` CLI). **No Kubernetes.**
- Primary languages: **Python, Bash, PowerShell**.
- Monitoring: Splunk, Grafana, Wavefront (Aria Operations for Applications), Moogsoft (Dell APEX AIOps), ThousandEyes.
- CI/CD: GitHub Actions; migrating off Bamboo.
- Don't propose Kubernetes or cloud-managed infra; hand platform-internal problems to the platform team.

## Using the fleet
- Pick a custom agent from the Chat agents dropdown; skills load automatically or via `/`.
- For stricter read-only tool scoping, generate and use `.github/agents/*.agent.md`; generated read-only
  agents do not receive terminal access because Claude hooks are not portable to Copilot.
- Seniority/experience is carried by **ladder skills** (`sde-ladder-*`, `sre-ladder-*`), not separate agents.
- Gates: clear `merge-gate` before merge; `release-gate` + `production-change-gate` before any prod change.

## Conventions
- Read-only agents recommend and never mutate prod; prod-facing actions need explicit human confirmation + the gate.
- **Evidence over assertion** — cite `file:line` or command output; never fabricate output or system state.
- Lead with the conclusion, then evidence, then hand-offs. Blameless language for incidents.

For Copilot-native `.github/agents/*.agent.md` + `.github/skills/`, run `scripts/sync-copilot.ps1` (or `.sh`).
