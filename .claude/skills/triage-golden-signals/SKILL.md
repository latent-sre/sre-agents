---
name: triage-golden-signals
description: >-
  The framing layer for any triage or investigation — read the four golden signals (latency, traffic,
  errors, saturation) plus RED and USE, and know what each tells you and where to find it on our stack.
  Use at the start of every incident/triage to characterize the problem before forming hypotheses.
metadata:
  domain: sre
---

# Golden signals — read the system in 60 seconds

Before hypotheses, characterize the symptom with a standard signal set. Pull these from Wavefront
(`wavefront-queries`), Grafana (`grafana-dashboards`), Splunk (`splunk-triage`), and `pcf-ops`.

## The four golden signals (Google SRE)
| Signal | Question | Where (our stack) |
|---|---|---|
| **Latency** | How long do requests take? Split **success vs error** latency. | Wavefront p50/p95/p99; Grafana |
| **Traffic** | How much demand? (req/s, msgs/s) | Wavefront rate; access logs in Splunk |
| **Errors** | What rate is failing? (5xx, exceptions, wrong results) | Splunk error count; Wavefront error ratio |
| **Saturation** | How full? (CPU, memory, threads, queue depth, connections) | `cf app`; Wavefront container metrics |

## Complementary methods
- **RED** (per request-driven service): **R**ate, **E**rrors, **D**uration. Best for app endpoints.
- **USE** (per resource): **U**tilization, **S**aturation, **E**rrors. Best for memory/CPU/pools/queues.

## Ask "what changed?" first
Most incidents follow a change. Before deep hypotheses, line up **what changed** against **when it broke**:
- recent **deploy / release** (`cf events`, the release pipeline, `git log`)
- **config or feature-flag** flip
- **PCF platform event** (cell evacuation, quota, cert rotation — `cf events`)
- **traffic shift** (spike, new client, retry/batch job)
- **dependency** incident or vendor status-page event
- **cert / credential / secret expiry** (failures starting at a round timestamp)
- **DB migration** or data change
A change whose timestamp matches the impact-start is your prime suspect → hand to `sre-ladder` (investigator tier).

## How to read them
1. **Errors + latency up together** → app or a downstream dependency is failing/slow.
2. **Saturation up, then latency, then errors** → resource exhaustion (memory/threads/pool/queue) —
   classic capacity or leak; check `cf app` instance memory and `cf events` for OOM restarts.
3. **Traffic spike → latency/errors** → load-driven; capacity or a missing limit/backpressure.
4. **Errors up, traffic flat, latency flat** → logic/deploy/config error, not load. Correlate to a change.
5. **All flat but users complain** → check from outside (ThousandEyes synthetic / health endpoint) — it
   may be network, DNS, routing, or a specific path/region.

## Pin it down
Always establish: **exact start time**, **blast radius** (which apps/routes/spaces, % of traffic), and
**trend** (worsening/stable/recovering). Hand that to `sre-ladder` (investigator tier) to drive RCA.
