# Runbook: PCF app instances crashing / restarting (OOM)

> **Owner:** `<team>`  ·  **Last reviewed:** `<YYYY-MM-DD>`  ·  **Severity:** page if user-impacting

## Purpose & scope
Handles a PCF/TAS app whose instances are crashing or restart-looping, typically from **out-of-memory**.
**Out of scope:** platform/cell-wide outages (→ platform team), and errors without restarts (those are
not OOM — see [high-5xx-after-deploy.md](high-5xx-after-deploy.md) or escalate to `sre-engineer`).

## Trigger
Moogsoft incident or alert: app instance count below desired / repeated crashes; or `cf app <APP>`
shows instances cycling. Dashboard: `<grafana/wavefront link>`.

## Prerequisites
- `cf` CLI v8, logged in and targeted (`cf target`) — see `pcf-ops` → references/foundations.md.
- Access to Wavefront and Splunk for `<APP>`.

## Triage / first checks (read-only)
1. One-shot summary: `.claude/skills/pcf-ops/scripts/triage.sh <APP>`
2. Confirm OOM specifically:
   ```bash
   cf events <APP> | head -n 25      # look for: crashed ... reason: "OOMKilled" / exit status
   cf app <APP>                      # memory column near 100% of limit on the cycling instances?
   ```
3. Memory trend (is it a leak — steady climb — or a spike?):
   ```
   ts(<app.container.memory.usage>, app="<APP>") / ts(<app.container.memory.limit>, app="<APP>") * 100
   ```
4. Decide path:
   - **OOM confirmed + recent deploy** → likely a regression → go to Procedure step 1 (rollback path).
   - **OOM confirmed, no recent change** → leak or load growth → step 2 (stabilize) then investigate.
   - **Not OOM** (crashes for another reason) → escalate to `sre-engineer` (`sre-ladder-investigator`).

## Procedure
> All state changes below are **recommend-only**; hand to `release-engineer`, clear
> `production-change-gate`, and confirm before executing.
1. **If a recent deploy caused it — roll back** (fastest, reversible). Blue-green route remap to the
   previous app, or `cf rollback <APP> --version <n>` if revisions are enabled
   (see `rollback-mitigation`). This stops the bleeding; root-cause after.
2. **If no recent change — stabilize.** Either bump memory to restore service while you investigate:
   `cf scale <APP> -m <larger>` (restarts instances), or `cf restart-app-instance <APP> <i>` to recover
   a single wedged instance. **A restart that "fixes" a leak only resets the clock — keep investigating.**
3. **Find the cause** (`sde-engineer` for a code fix): heap growth over time = leak; OOM only under load
   = under-provisioned or missing backpressure; OOM right after deploy = regression (new dependency,
   bigger cache, changed JVM/runtime opts).

## Verification
- `cf app <APP>` shows all instances `running` and stable for ≥10 min; memory back below ~70% of limit.
- Error/restart rate back to baseline in Wavefront/Grafana; Moogsoft incident clears.

## Rollback / cleanup
- If you scaled memory as a stopgap, record it and open a follow-up to right-size or fix the leak (don't
  leave silent over-provisioning).
- If you rolled back a deploy, the bad version stays out until `sde-engineer` ships a fix.

## Escalation
- Not OOM, or cause unclear after 15 min → `sre-engineer`. User-impacting + needs coordination →
  `incident-commander`. Suspected platform/cell issue → platform team.

## References
- Skills: `pcf-ops`, `rollback-mitigation`, `triage-golden-signals`, `wavefront-queries`
- Dashboards: `<links>`  ·  Related: [high-5xx-after-deploy.md](high-5xx-after-deploy.md)
