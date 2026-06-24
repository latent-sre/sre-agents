---
name: wavefront-queries
description: >-
  Wavefront Query Language (WQL) patterns for metrics investigation and alerting on VMware Aria
  Operations for Applications (formerly Tanzu Observability by Wavefront). Use when querying metrics —
  latency percentiles, error ratios, saturation, rates — during RCA, or when designing metric alerts.
  Covers ts(), aggregation, rate/deriv, moving windows, and error-ratio patterns.
metadata:
  domain: observability
  tool: wavefront-aria-operations-for-applications
---

# Wavefront queries (WQL / `ts()`)

Our metrics platform is **VMware Aria Operations for Applications** (formerly Tanzu Observability by
Wavefront). The query language is WQL; the core function is `ts()`.

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

## Percentile latency
```
percentile(95, ts(app.http.requests.latency, app="checkout"))                 # p95 across instances
percentile(99, ts(app.http.requests.latency, app="checkout"), instance)       # per-instance p99 (find the bad one)
```

## Error ratio (the SLI you usually want)
```
100 * sum(ts(app.http.requests.errors, app="checkout"))
    / sum(ts(app.http.requests.count,  app="checkout"))           # error % over time
```

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

## Missing data & PromQL equivalence
- **Alert on data gaps** (agent down / app stopped reporting): derive the threshold from the metric's
  **reporting interval**. For a metric reported once per minute you expect ~5 points per 5 min, so
  `mcount(5m, ts(<metric>, app="checkout")) < 5` flags a series that's dropping points (tune the
  number to your actual cadence). A metric that simply *stops* is a real outage signal that plain
  threshold alerts miss.
- **WQL ↔ PromQL** (Aria Operations also accepts PromQL): `sum(ts(m), tag)` ≈ `sum by(label)(m)`;
  `rate(ts(counter))` ≈ `rate(m[5m])`; `mavg(5m, ts(m))` ≈ a moving average. Write in whichever your
  team reads fluently.

## Investigation tips
- Break a flat aggregate down `by instance`/`by host` to find the one bad pod/instance.
- Overlay the metric with the deploy time (events) — a step change at deploy = the change is the cause.
- For alerts, hand the finalized query to `sre-monitor` with a window + threshold + burn-rate
  (`slo-error-budget`); avoid alerting on a raw, unsmoothed series.
- WQL specifics evolve — confirm a function against the current Aria Operations for Applications docs
  (`researcher`) before relying on an unusual one.
