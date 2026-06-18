# Runbooks

Starter operational runbooks for on-call, authored with the [`runbook-template`](../.claude/skills/runbook-template/)
skill. Fill the placeholders before treating one as live. Each is trigger-anchored and ends at "resolved or escalate." Mitigations that change prod are
**recommend-only here** — execute them through `release-engineer` after clearing the
[`production-change-gate`](../.claude/skills/production-change-gate/).

| Runbook | Trigger |
|---|---|
| [pcf-app-oom-restarts.md](pcf-app-oom-restarts.md) | PCF app instances crashing / restarting (OOM) |
| [high-5xx-after-deploy.md](high-5xx-after-deploy.md) | Error-rate / SLO-burn spike shortly after a release |
| [dependency-timeout.md](dependency-timeout.md) | Latency + upstream-timeout errors from a downstream dependency |

> Replace `<APP>`, `<INDEX>`, `<DEP>`, and metric/route names with your real values (see each skill's
> `references/` file). Keep these current — a wrong runbook is worse than none.
