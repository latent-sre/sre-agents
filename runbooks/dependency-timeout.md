# Runbook: downstream dependency slow / timing out

> **Owner:** `<team>`  ·  **Last reviewed:** `<YYYY-MM-DD>`  ·  **Severity:** page if user-impacting

## Purpose & scope
Handles `<APP>` degraded because a **downstream dependency** `<DEP>` (API, DB, queue, auth) is slow or
erroring — latency climbs, then errors appear as upstream timeouts. **Out of scope:** our own
deploy/config regressions (→ [high-5xx-after-deploy.md](high-5xx-after-deploy.md)) and OOM
(→ [pcf-app-oom-restarts.md](pcf-app-oom-restarts.md)).

## Trigger
Latency SLO burn + timeout/upstream errors for `<APP>`; ThousandEyes alert on `<DEP>` path. Dashboard:
`<link>`.

## Prerequisites
- Splunk + Wavefront + ThousandEyes access; contact/status page for `<DEP>` and its owning team.

## Triage / first checks (read-only)
1. **Signal shape (golden signals):** latency up first, then errors? That pattern points downstream, not
   at our code. Saturation (thread/connection pool) often rises with it.
2. **Find the timeout signature (Splunk):**
   ```spl
   index=<INDEX> (timeout OR "connection reset" OR "<DEP>") earliest=-1h
   | timechart span=1m count by error_type
   ```
3. **Is it the network/path or `<DEP>` itself? (ThousandEyes)** Check the test to `<DEP>`: loss/latency at
   a specific hop/AS = network; clean path but slow responses = `<DEP>` is unhealthy. Compare Enterprise
   (inside) vs Cloud (outside) agents (see `thousandeyes-network`).
4. **Is `<DEP>` already in a known incident?** Check its status page / `researcher`.
5. **Decision:** confirmed downstream → Procedure. Path-clean **and** `<DEP>` healthy → it's likely us
   (pool exhaustion / bad config) → `sre-engineer` + `sde-engineer`.

## Procedure
> State changes are **recommend-only**; hand to `release-engineer`, clear `production-change-gate`, confirm.
1. **Reduce blast radius / degrade gracefully:** if `<APP>` supports it, fail over to a healthy
   `<DEP>` instance/region, serve cached/stale data, or disable the non-critical feature that needs
   `<DEP>` (feature flag).
2. **Stop the amplification:** if we're retry-storming `<DEP>`, recommend backing off (lower retry/raise
   backoff, or trip the circuit breaker). Retries without backoff make a struggling dependency worse
   (see `sre-ladder-elite`).
3. **Engage the dependency owner** with evidence (the ThousandEyes path + timeout timeline). Track in the
   incident.
4. **If the cause is on our side** (connection/thread pool exhaustion, too-tight/-loose timeouts) → durable
   fix by `sde-engineer` (`sde-ladder-principal`): bounded timeouts, pool sizing, circuit breaker, bulkhead.

## Verification
- Latency and timeout error rate return to baseline; saturation (pool/threads) recovers.
- ThousandEyes test to `<DEP>` green; `<DEP>` owner confirms recovery.

## Rollback / cleanup
- Re-enable any feature flag / restore normal retry+timeout config once `<DEP>` is stable (record what you
  changed and when).

## Escalation
- `<DEP>` owner / vendor for their fix; `incident-commander` if cross-team coordination or leadership
  comms are needed; `sre-engineer` if it turns out not to be the dependency.

## References
- Skills: `thousandeyes-network`, `splunk-triage`, `triage-golden-signals`, `rollback-mitigation`,
  `sre-ladder-elite`
- After resolution: `blameless-postmortem`; add the dependency-latency burn alert via `sre-monitor`.
