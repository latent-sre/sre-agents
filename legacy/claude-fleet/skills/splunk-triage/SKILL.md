---
name: splunk-triage
description: >-
  Splunk SPL search patterns for incident triage and investigation — finding error spikes, reading them
  over time, correlating by request/trace id, comparing before/after a deploy, and extracting fields.
  Use when investigating logs in Splunk during triage or RCA, or when designing log-based alerts.
---

# Splunk triage (SPL)

Find the signal fast, then read it over time and correlate. Always scope `index`, `source`/`sourcetype`,
and a tight time window first — broad searches are slow and noisy.

> **Fill in** our indexes, sourcetypes, correlation-id field, and saved searches in
> [references/indexes.md](references/indexes.md) so these queries use real names.

> ## ⚠️ `#` IS NOT AN SPL COMMENT
> SPL comments are **triple backticks**: `` ```like this``` ``. A `#` is parsed as a **search term**, so
> pasting `| where status>=500  # find the spike` silently searches for the literal tokens `find`, `the`,
> `spike` — quietly changing your results mid-incident. Every example below therefore uses backtick
> comments, and is safe to copy verbatim.
>
> Two documented restrictions: a comment **cannot precede a generating command** (`tstats`,
> `makeresults`, `multisearch`, `gentimes`) — the search fails or returns wrong results — and comments
> **cannot appear inside a quoted string**.
> *(There is a community `` `comment()` `` macro, but it is **not** in Splunk's official docs and its
> app-scoped sharing means it can fail to resolve for other users. Don't rely on it.)*
> *SPL2 is different again: `//` and `/* */`.*

## Start narrow
````spl
index=<app_index> host=<...> sourcetype=<...> earliest=-1h latest=now
| where status>=500
```scope the base search by index/sourcetype/host/time ONLY — no keyword filter.
   a keyword like "error" would drop 5xx access-log events whose raw text has no
   "error", false-clearing the very spike you're confirming.```
````
> **Numeric field comparisons (`status>=500`, `error_type=...`) belong in a `| where`/`| search`
> *after* the base search, not in the raw keyword search.** A numeric comparison on a field that isn't
> search-time-extracted silently matches **nothing** — a false "all clear" mid-incident. Confirm
> `status`/`error_type` are extracted (or `rex` them first); see the extraction note under *Tips*.

## Read it over time (is it a spike? when did it start?)
````spl
index=<app_index>
| where status>=500     ```status must be an extracted field, else this matches nothing```
| timechart span=1m count     ```5xx per minute — find the exact onset```
````
> Same trap as above: a keyword like `error` in the base search filters before `| where status>=500`
> runs, missing 5xx access-log events with no "error" text and false-clearing the spike. Scope the base
> search; filter the status in `| where`.
````spl
index=<app_index>
| timechart span=1m count by status     ```split by HTTP status to see 5xx vs 4xx```
````

## Top offenders
````spl
index=<app_index> error
| stats count by error_type, message
| sort -count
```error_type must be indexed/extracted — if it isn't, `stats by error_type` buckets
   everything into one empty group```
````
`error_type` must be search-time-extracted; if it isn't, `rex` it first (see *Tips* below).

## Spot a spike vs the baseline (anomaly detection)

**Three traps here, and the skill used to fall into all of them.**

**1. The baseline must EXCLUDE the current point.** `streamstats` defaults to `current=true` and
`window=0` (all previous *and current* events), so a naive trailing baseline is **contaminated by the
very spike you are trying to detect** — the bigger the spike, the more it raises its own baseline and
hides itself. Pass `current=f`.

**2. `streamstats` follows RESULT order, not time order.** Splunk returns newest-first by default, so
without a sort your "previous events" are the *newer* ones — the baseline is built from the future.
Put `sort 0 _time` first (`0` = no result limit; `sort` silently truncates otherwise).

**3. Compare RATES, not raw counts.** A rise in error *count* during a traffic doubling is not a rise in
error *rate*. Normalize by total volume, or you page on a marketing campaign.

````spl
index=<app_index> earliest=-24h
| where status>=500
| bin _time span=5m
| stats count by _time
| sort 0 _time                                    ```ascending — streamstats follows RESULT order```
| streamstats window=12 current=f
      avg(count) AS baseline stdev(count) AS sd   ```trailing 1h, EXCLUDING this bucket```
| where isnotnull(baseline) AND sd>0 AND count > baseline + 3*sd
   ```guards: the first rows have no baseline; a flat window gives sd=0 and would flag everything```
````

**Normalized (rate, not count) — prefer this:**
````spl
index=<app_index> earliest=-24h
| bin _time span=5m
| stats count(eval(status>=500)) AS errors, count AS total by _time
| eval error_rate = errors / total                ```a ratio survives a traffic spike; a count does not```
| sort 0 _time
| streamstats window=12 current=f avg(error_rate) AS baseline stdev(error_rate) AS sd
| where isnotnull(baseline) AND sd>0 AND error_rate > baseline + 3*sd
````

**Seasonal comparison** — "is this hour worse than the same hour last week?" is usually the question you
actually mean, and a trailing window can't answer it:
````spl
index=<app_index> earliest=-8d
| bin _time span=5m
| stats count(eval(status>=500)) AS errors, count AS total by _time
| eval error_rate = errors / total
| timechart span=5m avg(error_rate)
| timewrap 1week                                  ```overlay this week on last week```
````

> `eventstats` (adds an aggregate to **every** row, unlike `stats` which collapses them) is still the
> right tool for "which buckets exceed the *whole period's* mean" — but note it has the same
> contamination problem in reverse: the outlier is inside the mean it is being compared against.
> *Caveat on sourcing: `sort 0 _time`, `current=f`, and the null/`sd>0` guards are statistically
> correct, but they are **our** guidance — Splunk's own outlier example omits `current=f`. Don't cite
> Splunk for the normalization advice either; it documents the mechanisms (`streamstats`, `timewrap`),
> not the choice to normalize.*

## Correlate one request across services (trace/correlation id)
````spl
index=<app_index> (request_id="<id>" OR trace_id="<id>")
```one index; use (index=a OR index=b) to span several — a LIST inside index= is not valid SPL```
| sort 0 _time     ```the full path of one failing request; 0 = don't truncate```
| table _time host service status message
````
Tracing one id is the rare case a broad search is justified — use `index=*` only when the request may
touch services you can't enumerate, and keep the window tight. If logs lack a correlation id, that's a
finding — recommend adding one (`sde-engineer`).

## Compare before vs after a deploy
Compare **rates**, not raw counts — if traffic differs between the two phases (and after a deploy it
usually does), a count comparison tells you about traffic, not about the deploy.
````spl
index=<app_index>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| stats count(eval(status>=500)) AS errors, count AS total by phase, error_type
| eval error_rate = errors / total
   ```did this error's RATE rise after the deploy — or did traffic just grow?```
````

## Extract fields ad hoc
````spl
index=<app_index> sourcetype=<...> earliest=-1h     ```scope the base search — never start bare```
| rex field=_raw "latency=(?<latency_ms>[\d.]+)"    ```[\d.]+ keeps fractional ms; \d+ truncates them```
| stats p95(latency_ms), max(latency_ms) by uri
````

## Tips & gotchas (Splunk-specific — where the default bites)
- **Never leave the search broadly unscoped without reason.** `index=*` scans every index — slow, costly,
  and may silently miss role-restricted data. Scope to the app index from `references/`; the one justified
  exception is tracing a single correlation id across services you can't enumerate — even then, keep the
  window tight.
- **The time range is implicit and dangerous.** A bare search uses the picker's range (often last 24h);
  in a saved search/API job it's whatever the job sets. Set `earliest`/`latest` explicitly during triage.
- **Fields are case-sensitive and only exist after extraction.** `table status` shows nothing if the
  field was never extracted; `rex` it first. `_time` is in the search TZ, not necessarily the event's.
- `stats`/`timechart`/`tstats` aggregate; `transaction` groups events but is expensive — prefer
  `stats by <id>` for correlation.
- Match the search window to the incident timeline from `sre-ladder` (investigator tier).
- For recurring searches, hand the query to `sre-monitor` for a saved search / alert (route through
  Moogsoft — see `moogsoft-correlation`).
