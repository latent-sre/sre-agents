# Our Wavefront / Aria Operations for Applications — fill in

Concrete metric names, point tags, and dashboards for the `wavefront-queries` skill. Loaded on demand.

> Names and links only — no API tokens.

## Key metric names (what we actually emit)
| Concern | Metric name | Point tags |
|---|---|---|
| request rate | `<app.http.requests.count>` | `app`, `env`, `instance` |
| latency | `<app.http.requests.latency>` | `app`, `env` |
| errors | `<app.http.requests.errors>` | `app`, `env`, `status` |
| memory | `<app.container.memory.usage>` / `<...limit>` | `app`, `instance` |

## Source / tag conventions
- App identifier tag: `<app=...>`  ·  environment tag: `<env=prod|nonprod>`
- Instance/host tag: `<instance=...>` (use to find one bad instance)

## Dashboards & alert targets
| Name | Link | What it shows |
|---|---|---|
| `<dashboard>` | `<url>` | `<SLO / golden signals>` |

## Reusable query snippets (fill in real metric names)
Record which COUNTER TYPE your request/error metrics are — it changes the correct query. See the
`wavefront-queries` SKILL for why; the short version:
- **delta counters** → `cs()`, no `rate()`  ·  **cumulative counters** → `ts()` + `rate()`

```
# error % over time — DELTA counters (per-interval; units cancel). default() so "no errors" reads 0, not no-data.
100 * default(0, sum(cs(<app.http.requests.errors>, app="<app>"))) / sum(cs(<app.http.requests.count>, app="<app>"))

# error % over time — CUMULATIVE counters (must rate() first; raw division = ratio since process start)
100 * sum(rate(ts(<app.http.requests.errors>, app="<app>"))) / sum(rate(ts(<app.http.requests.count>, app="<app>")))

# TRUE request p95 — needs a HISTOGRAM. percentile(..., ts(...)) is a percentile ACROSS INSTANCES, not requests.
percentile(95, hs(<app.http.requests.latency.m>, app="<app>"))

# worst-INSTANCE hunt (this is what percentile(ts(...)) actually does — fine, as long as you mean it)
percentile(95, ts(<app.http.requests.latency>, app="<app>"), instance)

# missing-data alert — last() or it self-resolves while the app is still dead
last(1h, mcount(3m, ts(<app.http.requests.count>, app="<app>"))) = 0
```
