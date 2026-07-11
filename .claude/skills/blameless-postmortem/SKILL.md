---
name: blameless-postmortem
description: >-
  Structure and principles for a blameless postmortem after an incident. Use after an incident is
  resolved to write up what happened, the systemic cause and contributing factors, the timeline, and
  owned, dated action items. Covers the blameless stance and the standard sections. Pairs with
  incident-severity (the incident timeline) and sre-engineer (root cause).
---

# Blameless postmortem

The goal is **learning, not blame**: find the systemic reasons a competent team still hit this, and fix
them so the failure class can't recur. Describe systems and decisions, never people.

## Blameless stance
- Assume everyone acted reasonably with the information they had. Ask "what made this action make sense?"
  not "who messed up?".
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
## Action items       — table: action | type (mitigative/preventative) | owner | due | tracking link.
## Lessons            — what went well / what went wrong / where we got lucky.
```

## Action items that actually prevent recurrence
- Prefer **systemic** fixes (a gate, an alert, a guardrail, an automated check) over "be more careful."
- **Tag every item mitigative vs preventative** — *mitigative* fixes this specific gap; *preventative*
  eliminates the whole failure class. A postmortem with no preventative item rarely stops a recurrence.
  Track them in a table so none is lost:
  ```
  | # | Action | Type (mitigative/preventative) | Owner | Due | Tracking link |
  |---|--------|--------------------------------|-------|-----|---------------|
  | 1 | <specific, verifiable action>  | preventative | <name> | <date> | <ticket> |
  ```
- Each item is **owned, dated, tracked** — an un-owned action item is a wish. Route them:
  resilience/code → `sde-engineer`; detection/SLO → `sre-monitor`; deploy/rollback safety →
  a human release owner; runbook → `runbook-author`.
- Be honest about what you don't know; mark unconfirmed causes as hypotheses with how you'd confirm.

## Lessons — include "where we got lucky"
Capture three things, not just what broke: **what went well** (keep doing it), **what went wrong** (the
gaps), and **where we got lucky** — latent risks this incident *revealed* that didn't bite us this time
(an untested backup that happened to work, an alert that fired by coincidence, a key person who happened
to be online). Luck is a preventative action item waiting to be written.

## Tip
Seed this from the incident timeline (`incident-severity`) and the `sre-engineer` root-cause writeup so
it's accurate and fast while memory is fresh.
