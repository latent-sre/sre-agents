---
name: parallelization
description: >-
  Run INDEPENDENT strands CONCURRENTLY — sectioning, voting, multi-agent fan-out — and know WHEN the
  ~15× cost pays. Use when a task splits into independent strands (research, multi-lens review, surveying
  many files/services) or when diverse takes improve a judgment. Covers when to parallelize vs stay
  sequential, fan-out economics, and right-sizing. Distinct from `context-engineering` (one agent's
  attention budget). From Anthropic's "Building Effective Agents" and multi-agent research system.
---

# Parallelization

Do independent work concurrently instead of in series — for latency, breadth, or diverse perspectives.
Two shapes: *[sourced: Anthropic, "Building Effective Agents"]*

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
- Give each strand an **isolated context** and a **crisp, bounded mandate**, and have it return a
  **short summary**, not its transcript (see `context-engineering`).
- Combine deliberately: a citation/merge pass reconciling the strands beats naive concatenation.

## In this fleet
The `route-request` skill produces an **ordered plan**; the main session executes its parallel strands —
kept in the session holding the live context rather than paying a coordinator subagent's extra round-trip
(a cost choice, not a capability limit: subagents *can* now nest-dispatch). During an incident, technical
RCA (`sre-engineer`) runs *in parallel* with the incident-command process (`incident-severity`), and
`researcher` fans out alongside.

### Worked example — "ship feature X with tests and a runbook"
A feature ship is a **sequential spine with one parallel burst**:

```
 research (unknown API?) ─┐
                          ▼
              build feature X  (sde-engineer)         ── SEQUENTIAL (coupled; never fan out coding)
                          │  produces a diff
                          ▼
   ┌──────────── on the finished diff (sectioning) ───────────┐
   │  code-reviewer  ∥  security-reviewer  ∥  test-engineer   │ ── PARALLEL (independent lenses)
   └───────────────────────────┬──────────────────────────────┘
                               ▼  main session merges findings → one fix list
                       sde-engineer applies fixes → re-verify   (evaluator-optimizer loop)
                               ▼
                          [merge-gate] ─▶ human release owner ─▶ pcf-deploy ─▶ runbook-author
```

- **Sequential** because coupled: the build (each edit depends on the last — *don't* fan out coding),
  and the gates (pass/fail checkpoints; prod needs human sign-off).
- **Parallel** because independent: three review lenses on the *same* diff, plus `researcher` up front if
  an API/spec is unknown. That's 3–4 strands — the right-sized band, run as fan-out **inside the main
  session**, not a multi-agent swarm.
- **Each strand** gets an isolated context, a bounded mandate, and returns a **short summary**
  (`context-engineering`); the main session does a **merge pass** (dedupe/reconcile) before routing one
  consolidated fix list back (`self-improve-loop`).
- **`runbook-author` is downstream-gated**, not parallel with the build — it documents the *final*
  shipped behavior and real ops steps.

## Handoffs
- → `route-request` to turn a parallelizable request into an ordered delegation plan.
- → `handoff-protocol` to package each strand's mandate and merge results.
- → `context-engineering` to keep fanned-out sub-agents lean and summary-returning.
