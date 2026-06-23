# Our Grafana dashboards & data sources — fill in

Concrete values for the `grafana-dashboards` skill. The agent loads this on demand.

> Names, UIDs, and links only — **no credentials, no API tokens**.

## Data sources (UIDs the JSON model references)
| Data source | Type | UID | Notes |
|---|---|---|---|
| `<Wavefront>` | wavefront / aria | `<uid>` | metrics (`wavefront-queries`) |
| `<Splunk>` | splunk | `<uid>` | log-derived panels (`splunk-triage`) |
| `<ThousandEyes>` | — | `<uid>` | synthetic/external |

## Dashboard inventory
| Dashboard | UID | Folder | Owner | Purpose |
|---|---|---|---|---|
| `<service health>` | `<uid>` | `<folder>` | `<team>` | top-down SLO → drill-down |

## Conventions we standardize on
- Template variables present on every dashboard: `<app>`, `<env>`, `<instance>`, `<route>`.
- Org timezone: `<tz>` · default window: `<last 1–6h>`.
- Threshold palette tied to SLO: green `<…>` / amber `<…>` / red `<…>`.

## Alerting
| Alert | Dashboard/panel | Contact point | Runbook |
|---|---|---|---|
| `<burn-rate / availability>` | `<uid>#panel` | `<moogsoft route>` | `<runbook url>` |

## Provisioning
- Dashboards-as-code location: `<repo path / provisioning dir>`.
- How to apply: `<provisioning / CI step>` (no snowflake UI-only dashboards).
