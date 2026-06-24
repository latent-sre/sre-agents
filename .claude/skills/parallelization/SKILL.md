---
name: parallelization
description: >-
  Run INDEPENDENT strands CONCURRENTLY — sectioning, voting, multi-agent fan-out — and know WHEN the
  ~15× cost pays. Use when a task splits into independent strands (research, multi-lens review, surveying
  many files/services) or when diverse takes improve a judgment. Covers when to parallelize vs stay
  sequential, fan-out economics, and right-sizing. Distinct from `context-engineering` (one agent's
  attention budget). From Anthropic's "Building Effective Agents" and multi-agent research system.
metadata:
  domain: method
---

# Parallelization

Do independent work at the same time instead of in series — for latency, for breadth, or for diverse
perspectives. Two shapes: *[sourced: Anthropic, "Building Effective Agents"]*

- **Sectioning** — split a task into **independent subtasks** that run concurrently, then combine
  (e.g. fan out a search across services; review a diff for correctness ∥ security ∥ tests in parallel).
- **Voting** — run the **same** task several times for diverse outputs or a consensus (e.g. multiple
  reviewers on a high-stakes change; several hypotheses surfaced at once before testing).

## When it pays — and when it doesn't
- **Parallelize** genuinely *independent* strands: research across sources, a multi-lens review, sweeping
  many files/foundations, surfacing a differential of hypotheses. Anthropic's multi-agent research system
  beat single-agent by a wide margin on parallelizable breadth — *"token usage explains ~80% of the
  variance"*; the win is reasoning across more aggregate context than one window holds.
  *[sourced: Anthropic multi-agent research system]*
- **Keep sequential** tightly-coupled work — especially **coding**, where each step depends on the last.
  Fan-out there causes conflicting edits and rework. *[sourced: Anthropic — multi-agent is weak for coding]*
- **Mind the cost.** Multi-agent fan-out can run **~15× the tokens of a normal chat** (single agents
  already run ~4× chat) — so it's a few times a single agent's cost, paid on top of coordination
  overhead. Spend it only when the outcome's value clears that bar; **most tasks capture the reliability
  gains inside one agent** (sectioned tool calls, a couple of review lenses) without the multi-agent
  premium. *[sourced: Anthropic multi-agent research system]*

## Right-sizing the fan-out
- 1 agent for a simple lookup; 2–4 for a comparison or multi-lens review; more only for genuinely
  complex, decomposable work. Extra agents cost coordination and tokens — add them when parallelism pays.
- Give each parallel strand an **isolated context** and a **crisp, bounded mandate**, and have it return
  a **short summary**, not its transcript (see `context-engineering`).
- Combine deliberately: a citation/merge pass that reconciles the strands beats naive concatenation.

## In this fleet
The `route-request` skill produces an **ordered plan**; the main session executes its
parallel strands — kept in the session that holds the live context rather than paying a coordinator
subagent's extra round-trip (a cost choice, not a capability limit: subagents *can* now nest-dispatch).
During an incident, technical RCA (`sre-engineer`) runs *in parallel* with the incident-command process
(`incident-severity`), and `researcher` fans out
alongside. The fleet handoff map ([`docs/HANDOFFS.md`](../../../docs/HANDOFFS.md)) carries the
"parallelize independent work, keep coupled work sequential" rule — this skill is the *why* and *how much*.

## Handoffs
- → `route-request` to turn a parallelizable request into an ordered delegation plan.
- → `handoff-protocol` to package each strand's mandate and merge results.
- → `context-engineering` to keep fanned-out sub-agents lean and summary-returning.
