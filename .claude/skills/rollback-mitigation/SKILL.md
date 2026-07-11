---
name: rollback-mitigation
description: >-
  The fast, safe mitigation playbook for a production incident on PCF — stop user pain first, before
  root cause. Use when an incident needs immediate mitigation: pick the fastest reversible action
  (route remap, revision rollback, restart, scale, flag flip) for the situation. State-changing: all of
  these require human confirmation; sre-engineer recommends, a human release owner executes.
---

# Rollback & mitigation playbook (PCF)

**Mitigate before you fully understand.** Stopping user pain comes before root cause. Pick the
**fastest safe, reversible** action. `sre-engineer` recommends; a human release owner executes with human
sign-off; in a major incident the incident commander (on-call lead running `incident-severity`) owns the decision.

## Choose the mitigation (fastest-safe-first)
| Situation | Mitigation | Command (confirm first) |
|---|---|---|
| **Bad deploy** (errors start at deploy time), previous app still exists | **Blue-green rollback** — remap prod route to the previously-live app | `cf map-route <previous-app> <domain> --hostname <app>` then `cf unmap-route <current-app> …` (blue/green are *roles*, not fixed names — colors alternate each deploy; confirm which is live with `cf apps` first) |
| Bad deploy, revisions enabled | **Revision rollback** | `cf revisions <app>` (find last good `<n>`) → `cf rollback <app> --version <n>` |
| Rolling/canary deploy in flight going wrong | **Abort the deploy** | `cf cancel-deployment <app>` — **in-progress only**; once the deploy has completed it **errors** ("No active deployment found"), so use **revision rollback** (`cf rollback <app> --version <n>`) instead |
| Instances hung / wedged / leaking, no recent change | **Restart** (buys time; doesn't fix cause) | `cf restart <app>` or `cf restart-app-instance <app> <i>` |
| Bad config/env change | Revert env + restage | `cf set-env <app> KEY <old>` → `cf restage <app>` |
| Load/capacity-driven saturation | **Scale out** | `cf scale <app> -i <more>` |
| Feature-flag-gated bad behavior | **Disable the flag** (often fastest of all) | flag system — no deploy needed |
| Downstream dependency failing | Fail over / degrade gracefully / shed load | per dependency runbook |

## Rules
1. **Reversible first.** Prefer an action you can undo in seconds (route remap, flag flip) over one you
   can't. Blue-green route remap is the gold standard — instant and reversible.
2. **One change at a time**, then observe. Watch the golden signals (`triage-golden-signals`) for 1–2
   minutes before the next action — so you know what worked.
3. **Restart is a stopgap, not a fix.** If a restart "fixes" it, the cause is still there (leak, poison
   input, dependency) — capture `cf events`/logs first, then keep investigating (`sre-ladder`, investigator tier).
4. **Record everything** (UTC) for the timeline and `blameless-postmortem`: what you changed, when, the effect.
5. **Confirm before executing.** Every command here changes prod — show the command + rollback, get
   human sign-off (`production-change-gate`), then run.

## After mitigation
User pain stopped ≠ incident over. Hand to `sre-engineer` for root cause and a human release owner for the
fix forward; capture the procedure with `runbook-author`.
