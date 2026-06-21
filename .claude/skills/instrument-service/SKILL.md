---
name: instrument-service
description: >-
  Instrument a service for observability — RED/USE metrics, traces, and structured logs with
  OpenTelemetry, plus the cardinality discipline that keeps metrics cheap. Use when adding monitoring to
  a service or improving its telemetry so it can actually be triaged. Emits via OTel so signals flow to
  our stack (Wavefront metrics, Splunk logs, Grafana dashboards); pairs with slo-error-budget.
metadata:
  domain: observability
---

# Instrument a service

Make a service observable with portable, standards-based telemetry — **instrument once, with
standards** — so the data lands in our stack (Wavefront / Splunk / Grafana) and stays portable.

## Steps
1. **Map** users, critical journeys, entry points, dependencies, and constrained resources.
2. **Auto-instrument first** with the OpenTelemetry SDK; then add **manual** spans for business-critical
   operations.
3. **Resource attributes** — set `service.name`, `service.version`, `deployment.environment` (OTel
   semantic conventions) so signals are filterable per app/space.
4. **RED per route** (request-driven services): request count, error count, and a latency **histogram**
   — split **success vs error** latency. Bounded labels only (method, route template, status class).
5. **USE per resource** (pools/queues/CPU/memory): utilization, saturation, errors — this is what catches
   the "saturation → latency → errors" cascade in `triage-golden-signals`.
6. **Traces** — propagate W3C trace context across services; tail-sample to keep all error/slow traces.
7. **Logs** — structured (JSON) carrying the trace/span IDs; **no secrets/PII** (see `craft` (Python)).
8. **Correlate** — verify metric→trace (exemplars) and trace→log (shared IDs) actually link.

## The cardinality rule (this is what blows up metric stores)
**Bounded** dimensions → metric labels/tags. **Unbounded** identity (user/request/trace IDs, full URLs,
emails, raw SQL) → traces and logs, **never** metric labels. A label with unbounded values creates a new
time series per value and melts the metrics backend.

## Naming
- **OTel / Prometheus style** for portability: `namespace_subsystem_unit` in base units (seconds, bytes);
  counters end `_total`; histograms expose `_bucket`/`_sum`/`_count`. Dimensions live in labels, not the name.
- In **Wavefront** the same metrics arrive as dot-delimited names (`app.http.requests.latency`) + point
  tags — keep the identical bounded-tag discipline (see `wavefront-queries`).

## Where it lands (our stack)
Emit via OTel → metrics to **Wavefront**, logs to **Splunk**, dashboards in **Grafana**, synthetics in
**ThousandEyes**. Keeping the emit layer OTel keeps the backend swappable. Then define SLIs/SLOs and
burn-rate alerts with **`slo-error-budget`** — and you'll actually be able to run the
`wavefront-queries` / `splunk-triage` queries during an incident.

## Done
Every critical journey emits RED; every constrained resource emits USE; traces propagate and correlate to
logs; **no unbounded metric label exists**; and there's at least one SLI you can compute from what you emit.
