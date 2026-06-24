---
name: adr-template
description: >-
  Architecture Decision Record (ADR) and lightweight RFC/design-doc templates and practices. Use when
  capturing a significant or hard-to-reverse technical decision, writing a design doc/RFC before
  non-trivial work, or recording why an approach was chosen over alternatives. Provides the Nygard ADR
  format, an RFC skeleton, and MADR guidance. Pairs with sde-ladder (principal and distinguished tiers).
---

# ADR & design-doc templates

Record decisions, not just mechanics: capture **context, the decision, and its consequences** so future
readers (and agents) understand the *why*. Treat docs like code — version-controlled, reviewed, owned.
**ADRs are immutable once accepted**: don't edit a superseded decision — mark it `superseded by ADR-NNN`
and write a new one. Keep them in-repo, numbered and append-only (e.g. `docs/adr/NNNN-title.md`). The
copy-paste fill-in is in [assets/adr-template.md](assets/adr-template.md).

## ADR — Michael Nygard format
```markdown
# ADR <NNN>: <short decision title>
## Status
<proposed | accepted | rejected | deprecated | superseded by ADR-NNN>   (<date>)
## Context
<the issue + forces: constraints, requirements, drivers, options considered. State facts.>
## Decision
<what we will do, written as "We will …">
## Consequences
<what becomes easier/harder: positive, negative, neutral; new risks, follow-ups, commitments>
```
For a large/contested trade-off space, **MADR** adds *Decision Drivers*, *Considered Options*, and
*Pros/Cons of the Options* — use it when the choice needs to be defended.

## Lightweight RFC / design doc (before non-trivial work)
Write one when the approach is uncertain, the change spans multiple files/systems, or others must weigh
in. RFCs **force clarity** — they're hard to write unless you actually understand the problem.
```markdown
# RFC: <title>   Author: <name>   Status: <draft|review|accepted>   Reviewers: <3–5 named>
## Problem & context        <what & why; current state; constraints>
## Goals / Non-goals        <explicit scope boundaries>
## Proposal                 <the design; diagrams welcome>
## Alternatives considered  <options + why not>
## Risks / trade-offs       <failure modes; compat (Hyrum's Law); SemVer impact; debt>
## Rollout & verification   <migration, flags, how we'll know it worked>
## Open questions
```
Guidance: keep it **concise** (over ~5–7 pages loses readers — diagram and link out); name **3–5 specific
reviewers**, not "everyone"; set a **review deadline** (~2 weeks); frame feedback as "Yes, if…" rather
than flat rejection to keep iteration moving.

## When to write which
- Reversible / local decision → a clear PR description (add a short ADR only if others will wonder "why").
- Significant or **hard-to-reverse** (data model, platform choice, a team standard) → **ADR**
  (load `sde-ladder`, distinguished tier).
- Non-trivial build spanning systems with an uncertain approach → **RFC first** (load `sde-ladder`, principal tier).
