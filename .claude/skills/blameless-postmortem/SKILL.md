---
name: blameless-postmortem
description: >-
  Structure and principles for a blameless postmortem after an incident. Use after an incident is
  resolved to write up what happened, the systemic cause and contributing factors, the timeline, and
  owned, dated action items. Covers the blameless stance and the standard sections. Pairs with
  incident-commander (timeline) and sre-engineer (root cause).
metadata:
  domain: doc
---

# Blameless postmortem

The goal is **learning, not blame**: find the systemic reasons a competent team still hit this, and fix
them so the failure class can't recur. Describe systems and decisions, never people.

## Blameless stance
- Assume everyone acted reasonably with the information they had at the time. Ask "what made this
  action make sense?" not "who messed up?".
- Treat human error as a **symptom** of a system that allowed it (missing guardrail, gate, alert, or
  unclear runbook) — fix the system.
- Separate the **trigger** (what set it off) from the **cause** (why our defenses didn't prevent/catch it).

## Structure
```
# Postmortem: <incident title>   (SEV-n)
Status: <draft|final>   Authors: <…>   Date: <…>

## Summary            — 3–5 sentences: what happened, impact, how it was resolved.
## Impact             — who/what, how long, magnitude (users, % traffic, $ if known), SLO/budget hit.
## Timeline (UTC)     — detection → diagnosis → mitigation → resolution; key decisions; from the IC log.
## Root cause & contributing factors — the systemic cause + the factors that aligned (usually several).
## Detection          — how we found out, and how fast. Could it have paged sooner? (→ sre-monitor)
## Response           — what went well, what was slow/hard (diagnosis, mitigation, comms, tooling).
## Five whys          — chain from symptom to systemic cause.
## Action items       — each: owner + due date + tracking link; concrete and verifiable.
## Lessons            — what we now know; what we'd tell our past selves.
```

## Action items that actually prevent recurrence
- Prefer **systemic** fixes (a gate, an alert, a guardrail, an automated check) over "be more careful."
- Each item is **owned, dated, tracked** — an un-owned action item is a wish. Route them:
  resilience/code → `sde-engineer`; detection/SLO → `sre-monitor`; deploy/rollback safety →
  `release-engineer`; runbook → `runbook-author`.
- Be honest about what you don't know; mark unconfirmed causes as hypotheses with how you'd confirm.

## Tip
Seed this from the `incident-commander` timeline and the `sre-engineer` root-cause writeup so it's
accurate and fast while memory is fresh.
