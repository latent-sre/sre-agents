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
```
# error % over time
100 * sum(ts(<app.http.requests.errors>, app="<app>")) / sum(ts(<app.http.requests.count>, app="<app>"))
# p95 latency, by instance (find the bad one)
percentile(95, ts(<app.http.requests.latency>, app="<app>")) by instance
```
