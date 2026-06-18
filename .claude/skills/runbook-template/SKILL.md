---
name: runbook-template
description: >-
  The standard operational runbook structure and authoring rules — written for the stressed 3am on-call
  reader. Use when creating or updating a runbook/playbook for an alert, task, or failure mode. Provides
  the required sections (trigger, procedure, verification, rollback, escalation) and a fill-in template
  in assets/. Pairs with the runbook-author agent.
metadata:
  domain: doc
---

# Runbook template & rules

A good runbook is **specific, sequential, verifiable, and reversible** — not an essay. Write for someone
stressed, low-context, and in a hurry.

## Runbook vs playbook vs SOP
- **Runbook** — the steps to handle *one* alert/task/failure mode (this template).
- **Playbook** — a broader response *strategy* that orchestrates multiple runbooks (e.g. a major-incident
  playbook). Lives closer to `incident-severity` / `incident-commander`.
- **SOP** — a fixed procedure for routine, normal operations (not incident-driven).

Keep them current the only way that works: **rehearse them.** Run game days / drills under realistic
conditions — *ten minutes of rehearsal prevents ten hours of confusion* — and bump `last_verified` after each.

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real values or clearly templated
  `<PLACEHOLDER>`s. No "obviously" or "just".
- **Expected output per step** — so the reader knows it worked before moving on.
- **Verify and roll back** — every state-changing action has "how to confirm it worked" and "how to undo
  it." Mark destructive steps with a warning + required confirmation (`production-change-gate`).
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Current or deleted** — date it, own it, prune what's wrong. A wrong runbook is worse than none.
- **Machine-linkable frontmatter** — give each runbook YAML frontmatter (`alert_names`, `owner`,
  `severity`, `last_verified`, `version`) so alerts can auto-link to it and a linter can flag any not
  verified in ~90 days.
- **Verify commands before publishing** — run read-only ones to confirm syntax; never run destructive
  steps to "test" them; mark anything unverified.

## Required sections (never drop trigger, procedure, verification, rollback, escalation)
The full fill-in template is in [assets/runbook-template.md](assets/runbook-template.md) — copy it to
start a new runbook. Structure:

```
# Runbook: <title / the alert it answers>
Owner · Last reviewed · Severity
## Purpose & scope     — what this handles, and explicitly what it does NOT
## Trigger             — the exact alert/symptom that brings you here
## Prerequisites       — access, tools, env, links (dashboard, logs, source)
## Triage / first checks — quick assessment + decision tree (if X → step N)
## Procedure           — numbered steps; command + expected output per step
## Verification        — how to confirm the issue is resolved
## Rollback / cleanup  — how to undo each change; safe-abort
## Escalation          — when to escalate and to whom (+ what to hand over)
## Communication       — who to notify + cadence while this is active (link `incident-severity`)
## Post-Incident       — close-out checklist: bump `last_verified`, file automation candidates
## References          — dashboards, related runbooks, postmortems
```

## Tip
Link every paging alert to its runbook (`sre-monitor`). The best runbook step is sometimes "run this
script" — if a step is fully mechanical, recommend automating it (`sde-engineer`/`release-engineer`)
along the **Crawl → Walk → Run** path: first document the manual steps (crawl), then wrap them in a
checked script the on-call runs by hand (walk), then trigger it automatically once it's proven (run).
Data-drive the alert→runbook link so saved searches/alerts surface the right runbook automatically —
each tool in our stack has a mechanism:
- **Splunk:** `... | lookup instructions_lookup alert_type OUTPUT runbook_url`.
- **Grafana:** a `runbook_url` annotation on the alert rule (templated by labels).
- **Wavefront:** the alert's resolution/runbook link, with Mustache-templated targets.
- **Moogsoft:** enrichment that attaches the runbook URL + escalation path to the alert/Situation.
