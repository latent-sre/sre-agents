---
name: moogsoft-correlation
description: >-
  Cut through an alert storm and find the single real problem — alert correlation and noise reduction
  with Moogsoft. Use when many alerts are firing at once across services (find the underlying Situation),
  when tuning clustering/dedup, or when reducing pager fatigue. Covers how events become deduplicated
  alerts and cluster into Situations. On-prem Moogsoft v9.x (the cloud product is rebranded Dell APEX
  AIOps Incident Management); uses v9.x terminology.
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
2. Read the Situation's alert list by time. The **first** alert is a **ranked hypothesis, not the
   cause.** First-in-time is a weak signal and routinely wrong: detection latency differs per check
   (a 60s poll reports after a 10s one), a slow dependency often alerts *after* the fast service it
   starved, and clock skew across sources reorders the list outright. Treat arrival order as a place to
   *start looking*, never as a finding.
3. If your foundation merges Situations (a newer one absorbing an older), follow the live one — confirm
   exact merge/supersede behavior against your version's docs.
4. Hand the top-ranked alert to `sre-ladder` (investigator tier) and **clear the bar below** before
   anyone writes "root cause" in the incident channel.

## The bar for asserting cause (correlation is a ranking, not a verdict)
Clustering and time-ordering **rank hypotheses**. Promoting one to a *cause* takes at least one of:

- **Mechanism** — you can state *how* A produces B, concretely enough to be wrong ("the pool saturated
  at 20:04, so requests queued, so p99 crossed the 5s gateway timeout"). "They fired together" is not a
  mechanism.
- **Corroboration** — an independent signal class agrees (metrics *and* logs *and* an event/change),
  not three views of the same feed.
- **Disconfirmation** — you looked for what should be true if the hypothesis is FALSE, and didn't find
  it. Ask: *what would I expect to see if this were NOT the cause?*
- **Controlled response** — the fix reverses the symptom, and the timing lines up. (Strongest, and the
  one you usually only get after mitigation.)

None of these? Say **"leading hypothesis"** and keep the alternatives alive. Writing a coincidence into
the postmortem as a cause is how a fleet fixes the wrong thing and the incident recurs — see
`blameless-postmortem`.

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
