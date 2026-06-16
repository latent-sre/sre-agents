---
name: slo-error-budget
description: >-
  Define SLIs, set SLOs with error budgets, and design burn-rate alerts — pragmatically, for an
  ops-focused team. Use when someone says "define an SLO", "what should we alert on", "are we within
  budget", or when turning a noisy threshold alert into a symptom/burn-rate alert. Covers SLI formulas,
  window/target choices, and multi-window burn-rate alerting on our stack.
metadata:
  domain: sre
---

# SLOs & error budgets (pragmatic)

Start with **one SLO per critical user journey**, not a metric zoo. An SLO you can compute and act on
beats a perfect one you can't.

## SLI — the measurement
An SLI is a ratio of **good events / valid events**, from the user's perspective:
```
availability SLI = successful requests / valid requests
latency SLI      = requests faster than <threshold> / valid requests
```
Compute it from what you already have: error ratio in `wavefront-queries`, or good/bad counts in
`splunk-triage`. Define "good" and "valid" explicitly (e.g. exclude health checks; 5xx = bad, 4xx
usually not your fault).

## SLO — the target over a window
- Pick a **target** (e.g. 99.9%) over a **rolling window** (commonly 28 days).
- **Error budget = 1 − SLO.** 99.9% over 28d ≈ **40 minutes** of allowed badness.
- The budget is a *decision tool*: budget left → ship features; budget burned → freeze risky changes and
  spend on reliability. This fits a non-Google, ops-focused team — it makes "how reliable is enough"
  an explicit, shared call.

## Burn-rate alerts (alert on symptoms, not causes)
Alert when you're **burning budget too fast**, using multi-window/multi-burn to be both fast and
low-noise:
| Severity | Burn rate | Windows (alert if both fire) | Budget consumed |
|---|---|---|---|
| Page (fast) | ~14× | 1h **and** 5m | ~2% in 1h |
| Page (slower) | ~6× | 6h **and** 30m | ~5% in 6h |
| Ticket | ~1–3× | 24h–3d | slow leak |
Two windows (long + short) means it fires fast on a real burn but resolves quickly when it stops —
far less flapping than a static threshold.

## Implement on our stack
- Express the SLI as a WQL ratio (`wavefront-queries`) or a Splunk search; build the burn-rate
  conditions in Wavefront/Splunk alerts; route through Moogsoft (`moogsoft-correlation`); surface
  budget on a Grafana SLO row (`grafana-dashboards`). Every page links a runbook.
- Hand the finalized definitions to `sre-monitor` to own as code.

## Don't
- Don't set 99.99% because it sounds good — every nine multiplies cost; match the target to real user
  need and what we can operate.
- Don't alert on every cause (CPU, single instance). Alert on the **symptom** (budget burn); let
  investigation find the cause.
