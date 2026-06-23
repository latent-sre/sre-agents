# Runbook: error-rate / SLO-burn spike shortly after a release

> ⚠️ **TEMPLATE — not yet live.** Replace `<APP>`, `<team>`, `<YYYY-MM-DD>`, `<grafana link>`, and `<INDEX>` with your real values before using in a real incident.

> **Owner:** `<team>`  ·  **Last reviewed:** `<YYYY-MM-DD>`  ·  **Severity:** page (user-impacting)

## Purpose & scope
Handles a spike in 5xx / errors (or a fast SLO **burn-rate** alert) that starts close to a deploy.
**Out of scope:** errors not correlated to a change (→ `sre-engineer` investigation), and dependency
slowness (→ [dependency-timeout.md](dependency-timeout.md)).

## Trigger
Burn-rate / error-rate alert for `<APP>` (see `slo-error-budget`), often minutes after a release.
Dashboard: `<grafana link>`.

## Prerequisites
- `cf` CLI v8 targeted; Splunk + Wavefront access; visibility into the release pipeline / `git log`.

## Triage / first checks (read-only)
1. **Establish onset and "what changed":**
   ```bash
   cf events <APP> | head -n 25        # last deploy/restage time + who
   git log --oneline -10               # what shipped
   ```
2. **Confirm the error spike and its start time (Splunk):**
   ```spl
   index=<INDEX> error earliest=-2h
   | where status>=500                       # status/error_type must be extracted fields — keep numeric
   | timechart span=1m count                 # comparisons OUT of the keyword base search, or a non-extracted
   | append [ search index=<INDEX> error earliest=-2h
            | stats count by error_type | sort -count | head 5 ]   # field silently matches nothing → false all-clear
   ```
3. **Error ratio (Wavefront):**
   ```
   100 * sum(ts(<app.http.requests.errors>, app="<APP>")) / sum(ts(<app.http.requests.count>, app="<APP>"))
   ```
4. **Decision:** errors begin at/just after the deploy time → **deploy regression → roll back** (step 1).
   Errors predate the deploy or no deploy → not this runbook → `sre-engineer`.

## Procedure
> State changes are **recommend-only**; hand to `release-engineer`, clear `production-change-gate`, confirm.
1. **Roll back the release — fastest reversible mitigation** (pick by what's available):
   - **Named blue-green**, previous app still exists → remap the prod route back to it (instant, reversible).
   - **Revisions enabled** → `cf revisions <APP>` to find the last good `<n>`, then `cf rollback <APP> --version <n>`.
   - **Rolling/canary deploy still mid-flight** → `cf cancel-deployment <APP>` (only works *before* the
     deploy completes; once finished, use revision rollback instead).
   See `rollback-mitigation`.
2. **If a feature flag introduced the behavior**, disabling the flag is often faster than a rollback —
   do that instead.
3. After recovery, hand the bad version + the error signature to `sde-engineer` for the durable fix
   (add the regression test that would have caught it — `tdd-workflow`).

## Verification
- Error ratio returns to baseline within a few minutes of rollback; SLO burn-rate alert clears.
- `cf app <APP>` healthy; Splunk `timechart` shows the 5xx line dropping back.

## Rollback / cleanup
- The mitigation *is* the rollback. If you flipped a flag, record it and re-enable only with the fix.
- Note budget consumed (`slo-error-budget/scripts/error_budget.py`) for the postmortem.

## Escalation
- Rollback doesn't restore service (so the deploy wasn't the cause) → `sre-engineer` immediately.
- Multiple services or stakeholders involved → declare an incident and run the incident-command process (`incident-severity`).

## References
- Skills: `rollback-mitigation`, `splunk-triage`, `wavefront-queries`, `slo-error-budget`, `pcf-ops`
- After resolution: `blameless-postmortem`; close detection gaps with `sre-monitor`.
