---
name: moogsoft-correlation
description: >-
  Alert correlation and noise reduction with Moogsoft / Dell APEX AIOps Incident Management — how events
  become deduplicated alerts and get correlated into incidents, and how to cut pager noise. Use when an
  alert storm is firing (find the real incident), when tuning correlation/dedup, or when reducing alert
  fatigue. Reflects on-prem Moogsoft v9.x behavior.
metadata:
  domain: aiops
  tool: moogsoft-apex-aiops
---

# Moogsoft / Dell APEX AIOps — correlation & noise reduction

Moogsoft (now **Dell APEX AIOps Incident Management**, on-prem v9.x) sits between your monitoring tools
and your pager. It turns a flood of raw events into a few actionable incidents.

## The pipeline (know where you are in it)
```
events  →  dedup into ALERTS  →  correlate into INCIDENTS  →  notify / page
```
- **Events** — raw signals from Splunk, Wavefront, ThousandEyes, etc.
- **Dedup** — repeated identical events collapse into one **alert** (with a count + first/last time).
- **Correlation** — related alerts cluster into one **incident** using *correlation definitions* (shared
  fields like service, host, time proximity).

## During an alert storm (investigation)
1. Look at the **incident**, not the individual alerts — Moogsoft has already grouped the related ones.
2. Read the incident's alert list ordered by time: the **first** alert often points at the trigger; the
   rest are downstream/correlated.
3. Watch for **superseded** incidents (a newer incident absorbing an older one) — follow the live one.
4. Hand the likely-root alert to `sre-ladder-investigator` to confirm cause; don't trust correlation as
   proof of causation — it's a strong hint, not a verdict.

## Reducing noise (tuning, with `sre-monitor`)
- **Dedup keys** — make repeated events from the same source collapse (right fields: service + check +
  host). Over-broad keys merge unrelated things; over-narrow keys leak duplicates.
- **Correlation definitions** — cluster by the fields that actually indicate "same incident" (service,
  app, dependency, time window). Validate against past incidents.
- **Enrichment** — add service/owner/runbook tags to events so incidents arrive actionable.
- **Maintenance windows** — suppress expected noise during deploys/patching so it doesn't page.
- **Kill non-actionable pages** — if an alert can't be acted on now, it's a ticket or dashboard, not a
  page (`sre-monitor` philosophy). Measure: alerts/incident ratio, % auto-correlated, page volume.

## Tip
Correlation/UI specifics differ between on-prem versions and APEX AIOps cloud — confirm exact field
names/screens against your foundation's docs (`researcher`) before scripting changes.
