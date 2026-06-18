---
name: adr-template
description: >-
  Architecture Decision Record (ADR) and lightweight RFC/design-doc templates for capturing the WHY of a
  significant technical decision before non-trivial work. Use when recording why an approach was chosen
  over alternatives, or writing a short design doc/RFC ahead of cross-cutting work. Provides the Nygard
  ADR format plus RFC guidance. Pairs with sde-ladder-principal / sde-ladder-distinguished (which produce
  designs) and blameless-postmortem (which records incidents).
metadata:
  domain: docs
---

# ADR & design-doc templates

Record **decisions, not just mechanics**: capture *context → decision → consequences* so future readers
(and agents) understand the **why**. Treat docs like code — version-controlled, reviewed, owned.
**ADRs are immutable once accepted:** don't edit a superseded decision; mark it `superseded by ADR-NNN`
and write a new one. Our ladder skills (`sde-ladder-principal`, `sde-ladder-distinguished`) *produce*
designs; this skill is how you *record* the resulting decision.

## When to write one
- An ADR: for any decision that's **expensive to reverse** or that others will build on (a contract,
  a framework/library choice, a migration strategy, a standard the team will follow).
- An RFC/design doc: **before** non-trivial work when the approach is uncertain, the change spans
  multiple files/systems, or others need to weigh in. Writing it forces clarity.

## ADR template (Michael Nygard format)
```markdown
# ADR <NNN>: <short decision title>

## Status
<proposed | accepted | rejected | deprecated | superseded by ADR-NNN>   (<date>)

## Context
<The issue motivating this decision. Forces at play: technical constraints, requirements,
business drivers, options considered. State facts — for us, name stack/lane constraints
(on-prem + PCF, no Kubernetes) where they bear on the decision.>

## Decision
<What we will do, written as "We will …".>

## Consequences
<What becomes easier or harder. Positive, negative, and neutral outcomes; new risks,
follow-ups, and what this commits us to.>
```

Keep ADRs in-repo under **`docs/adr/`**, numbered and append-only (e.g. `docs/adr/0007-pcf-blue-green.md`).
For a large trade-off space, MADR adds *Decision Drivers*, *Considered Options*, and *Pros/Cons of the
Options* — use it when the alternatives are many.

## Lightweight RFC / design doc (before coding)
```markdown
# RFC: <title>   Author: <name>   Status: <draft|review|accepted>   Reviewers: <3–5 named>
## Problem & context        <what & why; current state; constraints>
## Goals / Non-goals        <explicit scope boundaries>
## Proposal                 <the design; diagrams welcome>
## Alternatives considered  <options + why not>
## Risks / trade-offs       <failure modes, backward-compat, rollout/rollback, debt>
## Rollout & verification   <migration, flags, how we'll know it worked>
## Open questions
```

Guidance: keep it **concise** (past ~5–7 pages you lose readers — use diagrams and link out); name
**3–5 specific reviewers**, not "everyone"; set a **review deadline** (~2 weeks). Frame feedback as
"Yes, if…" rather than a flat rejection to keep iteration moving.
