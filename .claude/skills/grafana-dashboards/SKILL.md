---
name: grafana-dashboards
description: >-
  Designing and reviewing Grafana dashboards for service health — layout, panels, variables, data
  sources, alerting, and dashboards-as-code. Use when building or improving a dashboard, deciding what
  to visualize, or wiring Grafana alerts. Built for the 3am on-call reader: top-down from SLO/health to
  drill-down.
metadata:
  domain: observability
  tool: grafana
---

# Grafana dashboards

A dashboard exists to answer a question fast under stress — not to show every metric. Design top-down.

## Layout (top → bottom)
1. **Health / SLO row** — current SLO status + error-budget burn (see `slo-error-budget`). The first
   thing on-call should see: are we in trouble?
2. **Golden signals row** — latency (p50/p95/p99), traffic, error rate, saturation
   (`triage-golden-signals`). One row, consistent time range.
3. **Drill-down rows** — per-dependency, per-instance, per-route breakdowns to localize a problem.

## Panel hygiene
- Title every panel as the **question it answers** ("p99 latency — checkout"). Set **units** (ms, %, req/s).
- Sensible thresholds/colors tied to SLO (green/amber/red), not arbitrary.
- Latency as percentiles, not averages (averages hide the tail). Error rate as a **ratio**, not raw count.
- Default to a useful window (last 1–6h) and the org timezone; keep all panels on the same range.

## Variables (make it reusable)
- Template variables for `app`, `env`, `instance`, `route` so one dashboard serves many services.
- Use a consistent data-source variable so the same dashboard works across Wavefront/Splunk back ends.

## Data sources (our stack)
- Metrics from **Wavefront / Aria Operations for Applications** (`wavefront-queries`); logs/log-derived
  panels from **Splunk** (`splunk-triage`); external/synthetic from **ThousandEyes**.
- **Concrete values** — our data-source UIDs, dashboard inventory, conventions, and provisioning path
  live in `references/dashboards.md` (fill in; loaded on demand, no credentials).

## Alerting
- Prefer SLO/burn-rate alerts over static thresholds where possible. Every alerting panel links a
  **runbook** (`runbook-template`). Route alert notifications through Moogsoft for correlation
  (`moogsoft-correlation`).

## As code
- Export the dashboard **JSON model** and commit it; use Grafana **provisioning** (or Terraform/grafana
  provider if present) so dashboards are reviewed and reproducible — no snowflake UI-only dashboards.
- On review: validate JSON, don't clobber others' panels, and note what changed and why.
