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

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real values or clearly templated
  `<PLACEHOLDER>`s. No "obviously" or "just".
- **Expected output per step** — so the reader knows it worked before moving on.
- **Verify and roll back** — every state-changing action has "how to confirm it worked" and "how to undo
  it." Mark destructive steps with a warning + required confirmation (`production-change-gate`).
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Current or deleted** — date it, own it, prune what's wrong. A wrong runbook is worse than none.
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
## References          — dashboards, related runbooks, postmortems
```

## Tip
Link every paging alert to its runbook (`sre-monitor`). The best runbook step is sometimes "run this
script" — if a step is fully mechanical, recommend automating it (`sde-engineer`/`release-engineer`).
