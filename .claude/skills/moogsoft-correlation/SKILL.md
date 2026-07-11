---
name: moogsoft-correlation
description: >-
  Use for a Moogsoft alert storm, Situation, event deduplication, clustering, correlation, routing, or
  noise-reduction problem. Do not use for a single noisy threshold alert outside Moogsoft.
---

# Moogsoft / Dell APEX AIOps — correlation & noise reduction

Moogsoft sits between your monitoring tools and your pager, turning a flood of raw events into a few
actionable **Situations**. (On-prem v9.x clusters related alerts into a *Situation*; the cloud product,
rebranded **Dell APEX AIOps Incident Management**, calls the equivalent an *incident*. This skill uses
on-prem v9.x terms.)

## The pipeline (know where you are in it)
```
events  →  dedup into ALERTS  →  cluster into SITUATIONS  →  notify / page
```
- **Events** — raw signals from Splunk, Wavefront, ThousandEyes, etc.
- **Dedup** — repeated identical events collapse into one **alert** (with a count + first/last time).
- **Clustering** — related alerts group into one **Situation** via **Sigalisers** (the clustering
  algorithms): **Cookbook** (attribute/similarity-based, tuned through *Recipes*) and **Tempus**
  (time-based). *(Cloud APEX AIOps instead uses "correlation definitions" → incidents.)*

## During an alert storm (investigation)
1. Look at the **Situation**, not individual alerts — Moogsoft has already clustered the related ones.
2. Read the Situation's alert list by time: the **first** alert often points at the trigger; the rest
   are downstream/correlated.
3. If your foundation merges Situations (a newer one absorbing an older), follow the live one — confirm
   exact merge/supersede behavior against your version's docs.
4. Hand the likely-root alert to `sre-ladder` (investigator tier) to confirm cause; don't trust clustering as
   proof of causation — it's a strong hint, not a verdict.

## Reducing noise (tuning, with `sre-monitor`)
- **Dedup keys** — collapse repeated events from the same source (the de-duplication key is built from
  source/service/check). Over-broad keys merge unrelated things; over-narrow keys leak duplicates.
- **Sigaliser tuning** — Cookbook *Recipes* cluster by fields that indicate "same Situation" (service,
  app, dependency); Tempus clusters by time proximity. Validate against past incidents.
- **Enrichment** — add service/owner/runbook tags to events so incidents arrive actionable.
- **Maintenance windows** — suppress expected noise during deploys/patching so it doesn't page.
- **Kill non-actionable pages** — if an alert can't be acted on now, it's a ticket or dashboard, not a
  page (`sre-monitor` philosophy). Measure: alerts/Situation ratio, % auto-clustered, page volume.

## Concrete values
Our feeds, dedup-key formulas, Sigaliser recipes, enrichment tags, and Situation routing live in
`references/integrations.md` (fill in; loaded on demand, no credentials).

## Tip
Correlation/UI specifics differ between on-prem versions and APEX AIOps cloud — confirm exact field
names/screens against your foundation's docs (`researcher`) before scripting changes.
