---
name: agent-authoring
description: >-
  Use when creating or fixing anything an LLM consumes — a prompt, an agent definition, a SKILL.md, a
  tool description, or a grader — or when designing the roster of agents they live in. Triggers:
  "write me an agent/skill/prompt", "my skill never triggers", "it fires on almost every request",
  "how do I rewrite this description", "the model keeps ignoring this instruction", "the output is the
  wrong shape", "should this be an agent or a skill", "should we split this into subagents", "what
  orchestration shape", "our agents duplicate work / lose context between handoffs". For tools an agent
  calls use `tool-design`; for injection surfaces use `agent-security`.
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
