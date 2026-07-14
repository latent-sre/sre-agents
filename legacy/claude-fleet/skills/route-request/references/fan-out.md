# Fan-out — run independent strands concurrently, and know when the cost pays

The parallelism decision inside a routing plan. Two shapes:
*[sourced: Anthropic, "Building Effective Agents"]*

- **Sectioning** — split into **independent subtasks** that run concurrently, then combine (fan out a
  search across services; review a diff for correctness ∥ security ∥ tests).
- **Voting** — run the **same** task several times for diverse outputs or consensus (multiple reviewers
  on a high-stakes change; several hypotheses surfaced at once before testing).

## When it pays — and when it doesn't
- **Parallelize** genuinely *independent* strands: research across sources, a multi-lens review, sweeping
  many files/foundations, surfacing a differential of hypotheses. Anthropic's multi-agent research system
  beat single-agent by a wide margin on parallelizable breadth — *"token usage explains ~80% of the
  variance"*. *[sourced: Anthropic multi-agent research system]*
- **Keep sequential** tightly-coupled work — especially **coding**, where each step depends on the last.
  Fan-out there causes conflicting edits and rework. *[sourced: Anthropic — multi-agent is weak for coding]*
- **Mind the cost.** Multi-agent fan-out can run **~15× the tokens of a normal chat** (single agents
  already run ~4×). Spend it only when the outcome clears that bar; **most tasks capture the reliability
  gains inside one agent** (sectioned tool calls, a couple of review lenses) without the multi-agent
  premium. *[sourced: Anthropic multi-agent research system]*

## Right-sizing
- 1 agent for a simple lookup; 2–4 for a comparison or multi-lens review; more only for genuinely
  complex, decomposable work. Extra agents cost coordination and tokens.
- Give each strand an **isolated context** and a **bounded mandate**, and have it return a **short
  summary**, not its transcript (`context-engineering`).
- Combine deliberately: a merge pass reconciling the strands beats naive concatenation.

## In this fleet
The main session executes the plan's parallel strands itself — it holds the live context, so a
coordinator subagent would only add a round-trip (a cost choice, not a capability limit: subagents *can*
nest-dispatch). During an incident, technical RCA (`sre-engineer`) runs in parallel with the
incident-command process (`incident-severity`), and `researcher` fans out alongside.

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

- **Sequential** because coupled: the build (each edit depends on the last — *don't* fan out coding), and
  the gates (pass/fail checkpoints; prod needs human sign-off).
- **Parallel** because independent: three review lenses on the *same* diff, plus `researcher` up front if
  an API/spec is unknown. That's 3–4 strands — the right-sized band, run **inside the main session**.
- **`runbook-author` is downstream-gated**, not parallel with the build — it documents the *final* shipped
  behavior and real ops steps.
