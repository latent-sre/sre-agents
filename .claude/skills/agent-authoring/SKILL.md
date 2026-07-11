---
name: agent-authoring
description: >-
  Author or fix anything an LLM consumes — an agent definition, a SKILL.md, a system prompt, a tool
  description, a grader — and design the roster they live in. Use when writing one ("write me an
  agent/skill/prompt"), when one misbehaves (a skill that never triggers or fires too often, an agent
  that ignores an instruction, output with the wrong shape), or when the question is structural
  (should this be an agent or a skill, split/merge lanes, orchestration shape, handoff contracts,
  cross-agent failures like context poisoning or duplicated work). Two altitudes — read
  `references/artifact.md` for a single artifact, `references/roster.md` for the roster/orchestration.
  For tools an agent calls use `tool-design`; for injection surfaces use `agent-security`.
---

# Agent authoring — pick your altitude

Both altitudes share one discipline: **a prompt is a spec — edit it like code.** Reproduce the
failure, make the minimal fix, verify against a fresh run, and know which *form* of fix the failure
calls for. No edit without an observed failure (or an explicit new-behavior target) pinned to it.

Load **only** the altitude that matches:

- **Artifact** — one thing an LLM reads: a prompt, an agent definition, a `SKILL.md`, a tool
  description, a grader. The failure is in *this file's* wording, shape, or trigger.
  → [`references/artifact.md`](references/artifact.md)
- **Roster** — the *system*: what deserves to be an agent vs. a skill, how lanes split, the
  orchestration shape, handoff contracts, tool authority, context budgets, and cross-agent failure
  modes. The failure is *between* artifacts, or there's no artifact yet.
  → [`references/roster.md`](references/roster.md)

**Which one?** If rewording one file could fix it, it's *artifact*. If the fix means adding, splitting,
merging, or re-wiring agents — or the same problem keeps recurring across artifacts — it's *roster*.
Start at *artifact*; escalate when a wording fix can't reach the problem.
