---
name: wavefront-queries
description: >-
  Wavefront Query Language (WQL) patterns for metrics investigation and alerting on VMware Aria
  Operations for Applications (formerly Tanzu Observability by Wavefront). Use when querying metrics —
  latency percentiles, error ratios, saturation, rates — during RCA, or when designing metric alerts.
  Covers ts(), aggregation, rate/deriv, moving windows, and error-ratio patterns.
---

# Wavefront queries (WQL / `ts()`)

Our metrics platform is **VMware Aria Operations for Applications** (formerly Tanzu Observability by
Wavefront). Query language: WQL; core function: `ts()`.

> **Fill in** our real metric names, point tags, and dashboards in
> [references/metrics.md](references/metrics.md) so these snippets match what we emit.

## The building block
```
ts(<metric.name>, <source/tag filters>)
ts(app.http.requests.latency, app="checkout" and env="prod")
```
- Filter by point tags: `and`, `or`, `not`; wildcard with `*` (`app="checkout-*"`).
- Aggregate across series: `sum(...)`, `avg(...)`, `max(...)`, `count(...)`, optionally grouping by a
  tag — either as a parameter, `sum(ts(app.http.requests.count), app)`, or with the equivalent `by`
  keyword, `sum(ts(app.http.requests.count)) by (app)`. Prefer the comma form; the `by` form is valid
  but requires **parentheses** around the grouping keys — a bare `... by instance` (no parens) is not.

## Percentile latency — `percentile(ts(...))` is NOT request p95

**`percentile()` over `ts()` aggregates ACROSS SERIES, not across the request distribution.** At each
timestamp it takes one value per series (per instance), sorts *those*, and interpolates. If the metric
is a per-instance **mean** latency, `percentile(95, ts(...))` gives you *the 95th-percentile instance* —
with 4 instances, roughly "the worst instance's average". That is not p95 request latency, and no tag
filter makes it so. Report it as request p95 and you will understate tail latency, badly.

**For true request percentiles, use a histogram** (`hs()` stores the distribution, so any percentile is
computable at query time):
```
percentile(95,  hs(app.http.requests.latency.m, app="checkout"))    # real p95 of REQUESTS
percentile(99.9, hs(app.http.requests.latency.m, app="checkout"))   # any percentile, no pre-choosing
```
`percentile(<n>, hs(...))` is a *histogram conversion* function — a different function that happens to
share the name with the `ts()` aggregator. That collision is the whole trap.

*Precomputed* percentile metrics (e.g. Micrometer's `timer.p95` per instance) also work, but only
**per instance** — never `avg()`/`sum()` them across instances: the average of p95s is not a p95.

When you genuinely want "which instance is the outlier", the across-series form is the right tool —
just say so:
```
percentile(95, ts(app.http.requests.latency, app="checkout"), instance)   # worst-instance hunt, NOT request p95
```

## Error ratio (the SLI you usually want) — depends on your counter TYPE
Wavefront has **two** counter types and the correct query differs. Using the wrong one is silently wrong.

**Cumulative counters** (monotonically increasing; query with `ts()`) — you MUST take a rate first.
Dividing raw cumulative values gives the ratio *since process start*: it barely moves during a live
incident and resets when an instance restarts.
```
100 * sum(rate(ts(app.http.requests.errors, app="checkout")))
    / sum(rate(ts(app.http.requests.count,  app="checkout")))
```
> ⚠️ `rate()` produces a **gap** at every counter reset (it only reports positive change). On PCF,
> instances restart routinely — so a cumulative-counter SLI is full of holes exactly when the app is
> unhealthy. Prefer **delta** counters for request/error counts on this stack.

**Delta counters** (report the change since last report; query with **`cs()`**, not `ts()`) — already
per-interval, so the units cancel and `sum/sum` is correct. **Do not apply `rate()`** — it expects
increasing values and is wrong here.
```
100 * sum(cs(app.http.requests.errors, app="checkout"))
    / sum(cs(app.http.requests.count,  app="checkout"))
```

**Either way — the numerator vanishes when there are no errors.** If the errors metric doesn't emit a
`0` during clean periods, the whole ratio goes to *no data* instead of to *zero*. Apply `default()` to
the **numerator only**:
```
100 * default(0, sum(cs(app.http.requests.errors, app="checkout")))
    / sum(cs(app.http.requests.count, app="checkout"))
```
> Use `default()` sparingly: on a metric that arrives >1 min late it can *prevent* an alert firing.
> For spanning gaps in an alert condition, prefer `last()` (see *Missing data*).

## Rates and deltas (counters)
```
rate(ts(app.messages.processed))        # per-second rate of a counter
deriv(ts(app.queue.depth))              # is the backlog growing (positive) or draining?
```

## Smooth / window for alerts (reduce flapping)
```
mavg(5m, ts(app.http.requests.latency))           # 5-min moving average
align(1m, mean, ts(...))                           # align to a 1-min grid before combining series
```

## Saturation
```
ts(app.container.memory.usage) / ts(app.container.memory.limit) * 100   # mem % toward limit (OOM risk)
```

## Missing data — a bare `mcount()` alert SILENTLY SELF-RESOLVES
- **Alert on data gaps** (agent down / app stopped reporting): derive the threshold from the metric's
  **reporting interval**. For a metric reported once per minute you expect ~5 points per 5 min, so
  `mcount(5m, ts(<metric>, app="checkout")) < 5` flags a series dropping points. A metric that simply
  *stops* is a real outage signal that plain threshold alerts miss.
- ⚠️ **But wrap it in `last()`.** `mcount()` decays to 0 after the series dies, then — after **2× the
  window** — stops reporting entirely. The condition goes NO DATA, and an alert **resolves when its
  resolve window contains no data**. So a bare `mcount()` alert *fires* on a sustained outage and then,
  minutes later, **marks itself healthy while the app is still dead**. The dashboard goes green. That
  is worse than never firing.
  ```
  last(1h, mcount(3m, ts(app.http.requests.count, app="checkout"))) = 0
  ```
  `last()` holds the last known value across the gap, so the condition keeps evaluating and the alert
  stays firing. *[sourced: Wavefront `mcount`, "Alerting on Missing Data", "Alert States and Lifecycle"]*
- **For ordinary threshold alerts** (`ts(latency) > 500`), a vanished series doesn't fire at all — the
  alert enters the **NO_DATA** state. Don't build a second alert for this: attach **"Alert Has No Data"**
  notification targets to the alert you already have.
- The case no query can fix: if `ts()` matches **nothing at all** for the whole window (app died before
  the alert existed, source renamed, tag typo'd), there is no series to evaluate. That is what the
  NO_DATA target is for.
- **WQL ↔ PromQL** (Aria Operations also accepts PromQL): `sum(ts(m), tag)` ≈ `sum by(label)(m)`;
  `rate(ts(counter))` ≈ `rate(m[5m])`; `mavg(5m, ts(m))` ≈ a moving average. Write in whichever your
  team reads fluently.

## Investigation tips
- Break a flat aggregate down `by instance`/`by host` to find the one bad pod/instance.
- Overlay the metric with the deploy time (events) — a step change at deploy = the change is the cause.
- For alerts, hand the finalized query to `sre-monitor` with a window + threshold + burn-rate
  (`slo-error-budget`); avoid alerting on a raw, unsmoothed series.
- WQL specifics evolve — confirm an unusual function against the current Aria Operations for Applications
  docs (`researcher`) before relying on it.
