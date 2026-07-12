---
name: instrument-service
description: >-
  Instrument a service for observability — RED/USE metrics, traces, and structured logs with
  OpenTelemetry, plus the cardinality discipline that keeps metrics cheap. Use when adding monitoring to
  a service or improving its telemetry so it can actually be triaged. Emits via OTel so signals flow to
  our stack (Wavefront metrics, Splunk logs, Grafana dashboards); pairs with slo-error-budget.
---

# Instrument a service

Make a service observable with portable, standards-based telemetry — **instrument once, with
standards** — so the data lands in our stack (Wavefront / Splunk / Grafana) and stays portable.

## Steps
1. **Map** users, critical journeys, entry points, dependencies, and constrained resources.
2. **Auto-instrument first** with the OpenTelemetry SDK; then add **manual** spans for business-critical
   operations.
3. **Resource attributes** — set `service.name`, `service.version`, and **`deployment.environment.name`**
   (OTel semantic conventions) so signals are filterable per app/space.
   > ⚠️ **`deployment.environment` is DEPRECATED** — renamed to **`deployment.environment.name`** in
   > semconv **v1.27.0**, and stabilized in v1.41.0. Emit the `.name` form. Well-known values:
   > `development`, `staging`, `production`, `test`.
4. **RED per route** (request-driven services): request count, error count, and a latency **histogram**
   — split **success vs error** latency. Bounded labels only (method, route template, status class).
5. **USE per resource** (pools/queues/CPU/memory): utilization, saturation, errors — this is what catches
   the "saturation → latency → errors" cascade in the `sre-ladder` golden-signals reference.
6. **Traces** — propagate W3C trace context across services. Use a **Collector tail-sampling processor**
   with explicit policies (status=error, latency threshold) to **prioritize** error and slow traces.
   > ⚠️ **Tail sampling does NOT guarantee you keep all error traces.** It is best-effort under capacity
   > limits, and it fails *silently*. Three things must hold, and none is automatic:
   > - **Routing:** *all spans of a trace MUST reach the same collector instance*, or policies evaluate
   >   on a fragment. This needs a two-layer topology — a **load-balancing exporter** layer in front of
   >   the tail-sampling layer. Deploying tail sampling behind a plain round-robin LB is the classic
   >   silent misconfiguration.
   > - **Capacity:** `num_traces` (default **50,000**) is how many traces are held in memory. *"When a
   >   new trace arrives, the oldest trace is removed"* — it can be **dropped before it is ever
   >   sampled**. **Watch `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early`**; that
   >   metric is how the "guarantee" visibly fails.
   > - **Decision window:** `decision_wait` (default **30s**). Spans arriving after it miss the
   >   decision — long or slow traces are exactly the failure mode, and they're the ones you wanted.
7. **Logs** — structured (JSON) carrying the trace/span IDs; **no secrets/PII** (see `craft` (Python)).
8. **Correlate** — verify metric→trace (exemplars) and trace→log (shared IDs) actually link.

## The cardinality rule (this is what blows up metric stores)
**Bounded** dimensions → metric labels/tags. **Unbounded** identity (user/request/trace IDs, full URLs,
emails, raw SQL) → traces and logs, **never** metric labels. A label with unbounded values creates a new
time series per value and melts the metrics backend.

## Naming — OTel uses DOTS, not underscores
- **The OTel name is the source of truth:** namespaces delimited by **dots**, `snake_case` only *within*
  a multi-word component. **Units live in instrument metadata (UCUM), never in the name** — *"units do
  not need to be specified in the names since they are included during instrument creation."* Base units
  (seconds, bytes); counters not pluralized; dimensions in attributes, not the name.
  ```
  ✅  http.server.request.duration     unit: s     <- an OTel instrument name
  ❌  http_request_duration_seconds                <- an EXPORTER's rendering, not an OTel name
  ```
- **This lands natively on our stack.** Wavefront takes dot-delimited names + point tags
  (`app.http.requests.latency`) — the OTel shape, near-unchanged. Keep the bounded-tag discipline
  (see `wavefront-queries`).
- *Portability note (off-stack):* an underscore-style exporter translates **for you** — dots → `_`, a
  unit suffix appended, `_total` on monotonic sums. Never pre-bake that shape into the instrument name
  or it gets applied twice. Authoring the underscore form and calling it OTel is the common error.
- In **Wavefront** the same metrics arrive as dot-delimited names (`app.http.requests.latency`) + point
  tags — keep the identical bounded-tag discipline (see `wavefront-queries`).

## Where it lands (our stack)
Emit via OTel → metrics to **Wavefront**, logs to **Splunk**, dashboards in **Grafana**, synthetics in
**ThousandEyes**. An OTel emit layer keeps the backend swappable. Then define SLIs/SLOs and burn-rate
alerts with **`slo-error-budget`** — so you can run the `wavefront-queries` / `splunk-triage` queries
during an incident.

## Done
Every critical journey emits RED; every constrained resource emits USE; traces propagate and correlate to
logs; **no unbounded metric label exists**; at least one SLI is computable from what you emit.
