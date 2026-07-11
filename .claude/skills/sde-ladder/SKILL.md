---
name: sde-ladder
description: >-
  Use at the start of SDE work to choose senior, principal, or distinguished depth from ambiguity and
  blast radius. Do not use to supply language conventions or execute the implementation itself.
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
