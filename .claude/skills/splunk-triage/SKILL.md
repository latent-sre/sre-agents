---
name: splunk-triage
description: >-
  Splunk SPL search patterns for incident triage and investigation — finding error spikes, reading them
  over time, correlating by request/trace id, comparing before/after a deploy, and extracting fields.
  Use when investigating logs in Splunk during triage or RCA, or when designing log-based alerts.
metadata:
  domain: observability
  tool: splunk
---

# Splunk triage (SPL)

Find the signal fast, then read it over time and correlate. Always scope `index`, `source`/`sourcetype`,
and a tight time window first — broad searches are slow and noisy.

> **Fill in** our indexes, sourcetypes, correlation-id field, and saved searches in
> [references/indexes.md](references/indexes.md) so these queries use real names.

## Start narrow
```spl
index=<app_index> host=<...> sourcetype=<...> earliest=-1h latest=now
  ("ERROR" OR "Exception" OR status>=500)
```

## Read it over time (is it a spike? when did it start?)
```spl
index=<app_index> (error OR status>=500)
| timechart span=1m count                      # error count per minute — find the exact onset
```
```spl
index=<app_index>
| timechart span=1m count by status            # split by HTTP status to see 5xx vs 4xx
```

## Top offenders
```spl
index=<app_index> error
| stats count by error_type, message
| sort -count                                  # which error dominates
```

## Spot a spike vs the baseline (anomaly detection)
`eventstats` adds an aggregate to **every** row (unlike `stats`, which collapses rows) — use it to flag
buckets above the period's mean:
```spl
index=<app_index> (error OR status>=500) earliest=-24h
| bin _time span=5m | stats count by _time
| eventstats avg(count) as avg, stdev(count) as sd
| where count > avg + 2*sd                      # 5-min buckets > 2σ above the day's mean
```
`streamstats` computes a **trailing** baseline (per row, over a moving window) — answers "is *now* worse
than the last N points?":
```spl
index=<app_index> (error OR status>=500)
| bin _time span=1m | stats count by _time
| streamstats window=30 avg(count) as base
| eval ratio=count/base | where ratio > 3       # current minute 3x the trailing 30-min average
```

## Correlate one request across services (trace/correlation id)
```spl
index=* (request_id="<id>" OR trace_id="<id>")
| sort _time                                   # the full path of one failing request
| table _time host service status message
```
If logs lack a correlation id, that's a finding — recommend adding one (`sde-engineer`).

## Compare before vs after a deploy
```spl
index=<app_index> error
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| stats count by phase, error_type             # did this error appear only after the deploy?
```

## Extract fields ad hoc
```spl
... | rex field=_raw "latency=(?<latency_ms>\d+)"
    | stats p95(latency_ms), max(latency_ms) by uri
```

## Tips & gotchas (Splunk-specific — where the default bites)
- **Never leave the search unscoped.** `index=*` scans every index — slow, costly, and may silently
  miss role-restricted data. Always scope to the app index from `references/` (fill in your real values).
- **The time range is implicit and dangerous.** A bare search uses the picker's range (often last 24h);
  in a saved search/API job it's whatever the job sets. Set `earliest`/`latest` explicitly during triage.
- **Fields are case-sensitive and only exist after extraction.** `table status` shows nothing if the
  field was never extracted; `rex` it first. `_time` is in the search TZ, not necessarily the event's.
- `stats`/`timechart`/`tstats` aggregate; `transaction` groups events but is expensive — prefer
  `stats by <id>` for correlation.
- Match the search window to the incident timeline from `sre-ladder-investigator`.
- For recurring searches, hand the query to `sre-monitor` to make a saved search / alert (route through
  Moogsoft — see `moogsoft-correlation`).
