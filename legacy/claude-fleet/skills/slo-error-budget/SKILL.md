---
name: slo-error-budget
description: >-
  Define SLIs, set SLOs with error budgets, and design burn-rate alerts — pragmatically, for an
  ops-focused team. Use when someone says "define an SLO", "what should we alert on", "are we within
  budget", or when turning a noisy threshold alert into a symptom/burn-rate alert. Covers SLI formulas,
  window/target choices, and multi-window burn-rate alerting on our stack.
---

# SLOs & error budgets (pragmatic)

Start with **one SLO per critical user journey**, not a metric zoo. An SLO you can compute and act on
beats a perfect one you can't.

> **Helper:** `scripts/error_budget.py`
> - request-based status: `--slo 99.9 --bad-events <n> --total-events <n>`
> - time-based status: `--slo 99.9 --window-days 28 --bad-minutes <m>`
> - burn rate + severity: `--slo 99.9 --sli-long <pct> --sli-short <pct>` — **both windows required**.
>
> It will not mix a request-based SLI with a time-based one, and it will not emit PAGE/TICKET from a
> single window (see *Burn-rate alerting* below for why).

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
- **Error budget = 1 − SLO**, and its UNIT follows the SLI — do not convert between them:
  - **Request-based SLI** (the ratio above, and the usual case): the budget is a **number of bad
    requests**. 99.9% of 9.3M requests ≈ **9,300 failed requests**.
  - **Time-based SLI** (probe/uptime — the SLI is literally minutes): the budget is **minutes**.
    99.9% over 28d ≈ **40 minutes**.
  > Saying "99.9% ≈ 40 minutes of downtime" for a **request-based** SLO is wrong, and it is wrong in
  > the dangerous direction: it assumes traffic is uniform, so it under-counts a peak-hour outage and
  > over-counts a 3am one. This skill used to do exactly that, one section after defining the SLI as a
  > request ratio. Pick the SLI first; the unit follows.
- The budget is a *decision tool*: budget left → ship features; budget burned → freeze risky changes,
  spend on reliability. Fits a non-Google, ops-focused team — makes "how reliable is enough" an
  explicit, shared call.

## Burn-rate alerts (alert on symptoms, not causes)
Alert when you're **burning budget too fast**, using multi-window/multi-burn to be both fast and
low-noise:
| Severity | Burn rate | Windows (alert if both fire) | Budget consumed |
|---|---|---|---|
| Page (fast) | 14.4× | 1h **and** 5m | ~2% in 1h |
| Page (slower) | 6× | 6h **and** 30m | ~5% in 6h |
| Ticket | 1× (–3×) | 3d + 6h (or 24h) | slow leak |

*Burn-rate multipliers (14.4 / 6 / 1) are window-independent; the **budget-consumed** percentages assume a
30-day period (the SRE Workbook example) and shift slightly on a 28-day window. The canonical Workbook
ticket row is 1× over a 3-day long window + 6h short window.*

Two windows (long + short) means it fires fast on a real burn but resolves quickly when it stops —
far less flapping than a static threshold.

## Implement on our stack
- Express the SLI as a WQL ratio (`wavefront-queries`) or a Splunk search; build the burn-rate
  conditions in Wavefront/Splunk alerts; route through Moogsoft (`moogsoft-correlation`); surface
  budget on a Grafana SLO row (`grafana-dashboards`). Every page links a runbook.
- Hand finalized definitions to `sre-monitor` to own as code.

## Don't
- Don't set 99.99% because it sounds good — every nine multiplies cost; match the target to real user
  need and what we can operate.
- Don't alert on every cause (CPU, single instance). Alert on the **symptom** (budget burn); let
  investigation find the cause.
