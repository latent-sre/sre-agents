---
name: sde-ladder
description: >-
  Set your engineering altitude for a coding task, then load the matching tier — match depth to the
  task's ambiguity and blast radius. Use at the start of any SDE work to decide how much rigor it needs:
  senior (a scoped, well-defined change inside one component), principal (cross-cutting design, a
  contract/schema change, a migration, real blast radius), or distinguished (org-wide/high-ambiguity
  architecture, build-vs-buy, a standard others follow). Read the one tier file for the full method.
metadata:
  domain: ladder
  track: sde
---

# SDE ladder — pick your altitude

Judge the task's **ambiguity** and **blast radius**, then work at the matching tier. When in doubt,
think one level up, then drop to execution. Load **only** the tier that matches.

- **Senior** — scoped change inside one component with a clear spec; match patterns, edge cases, test,
  ship. → [`references/senior.md`](references/senior.md)
- **Principal** — spans components, alters a contract/schema, needs a design, or carries real blast
  radius; call-site/impact analysis + expand→contract migration. → [`references/principal.md`](references/principal.md)
- **Distinguished** — high ambiguity, multiple systems/teams, build-vs-buy, or a standard others
  follow; frame the problem and the tradeoffs before any code. → [`references/distinguished.md`](references/distinguished.md)
