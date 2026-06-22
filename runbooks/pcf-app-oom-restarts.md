# Runbook: PCF app instances crashing / restarting (OOM)

> ⚠️ **TEMPLATE — not yet live.** Replace `<APP>`, `<team>`, `<YYYY-MM-DD>`, `<grafana/wavefront link>`, `<links>`, `<i>`, and `<larger>` with your real values before using in a real incident.

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
1. One-shot summary: `.claude/skills/pcf-ops/scripts/triage.sh <APP>` or
   `pwsh .claude/skills/pcf-ops/scripts/triage.ps1 -App <APP>`
2. Confirm OOM specifically. PCF/CF reports OOM as **`Exited with status 137`** (128 + SIGKILL) —
   there is **no `OOMKilled` string** (that's Kubernetes). The crash reason lives in `cf app`/`cf logs`,
   not `cf events`:
   ```bash
   cf app <APP>                      # primary: instance state + memory column near 100% of limit on cycling instances
   cf logs <APP> --recent            # look for: "Exited with status 137" on the crashing instance
   cf events <APP> | head -n 25      # correlation only: recent deploy/restage/scale + who (audit.app.*) — not crash reason
   ```
3. Memory trend (is it a leak — steady climb — or a spike?):
   ```
   ts(<app.container.memory.usage>, app="<APP>") / ts(<app.container.memory.limit>, app="<APP>") * 100
   ```
4. Decide path:
   - **OOM confirmed + recent deploy** → likely a regression → go to Procedure step 1 (rollback path).
   - **OOM confirmed, no recent change** → leak or load growth → step 2 (stabilize) then investigate.
   - **Not OOM** (crashes for another reason) → escalate to `sre-engineer` using `sre-ladder` investigator tier.

## Procedure
> All state changes below are **recommend-only**; hand to `release-engineer`, clear
> `production-change-gate`, and confirm before executing.
1. **If a recent deploy caused it — roll back** (fastest, reversible). Pick by what's available:
   - **Named blue-green** and the previous app still exists → remap the prod route back to it (instant,
     reversible). Not available for `--strategy rolling` / same-name deploys — use revision rollback.
   - **Revisions enabled** → `cf revisions <APP>` to find the last good `<n>`, then
     `cf rollback <APP> --version <n>`.
   See `rollback-mitigation`. This stops the bleeding; root-cause after.
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
  declare an incident (`incident-severity`). Suspected platform/cell issue → platform team.

## References
- Skills: `pcf-ops`, `rollback-mitigation`, `triage-golden-signals`, `wavefront-queries`
- Dashboards: `<links>`  ·  Related: [high-5xx-after-deploy.md](high-5xx-after-deploy.md)
