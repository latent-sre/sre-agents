# Roster altitude — design the agent system, not one artifact

Multi-agent is an architecture decision with real costs — tokens, latency, and information loss at
every handoff — justified only when one context genuinely can't hold the work, stages need isolation,
independent perspectives reduce error, or parallelism pays. Fan-out runs **~15× the tokens of a normal
chat** (single agents already run ~4×), so default to fewer agents with better skills.
*[sourced: Anthropic "Building effective agents", "How we built our multi-agent research system"]*

## Agent vs. skill (this fleet's decision rule)

An **agent** exists when it needs a **distinct tool-scope**, a **distinct guard posture**, **or**
is a **recurring, separable domain lane with its own handoff edges**. Everything else — altitude,
method, checklist, playbook — is a **skill**. Seniority tiers are ladder skills, not cloned agents;
routing and incident-command are main-session skills because a coordinator subagent only adds a
round-trip for a low-context decision the main session can make inline. Apply this test before adding any agent, and record the
justification in the agent's own file (or an ADR if it reshapes the roster).

## Orchestration shapes

- **Orchestrator–workers** — the main session owns plan + synthesis; workers get bounded mandates
  and isolated context. The fleet's default (`route-request` plans, agents execute).
- **Pipeline** — items flow through stages independently, no barrier; wall-clock = slowest
  single-item chain. Default for multi-stage work.
- **Fan-out with barrier** — only when a stage needs ALL prior results at once (dedupe,
  cross-compare, early-exit on zero). Barriers idle the fast workers; justify each one.
- **Judge panel / adversarial verification** — independent attempts scored, or findings that
  survive only if skeptics prompted to *refute* them fail. Kills plausible-but-wrong output;
  worth the cost on high-stakes review.
- **Loop-until-dry** — for unknown-size discovery, iterate until K consecutive rounds surface
  nothing new; fixed counts miss the tail.

## Design principles

- **Workers are stateless and context-blind.** Construct exactly the context each needs (intent,
  state, success criteria — the `handoff-protocol` package); never assume they inherit yours.
  Underspecified handoffs are the #1 multi-agent bug.
- **The final message is the interface.** Specify each agent's return contract; free-text handoffs
  drop constraints at every hop. (`researcher`'s cited-brief contract is the model.)
- **Tools are authority.** The `tools:` list encodes the mandate — reviewers can't edit,
  researchers can't write. Enforce roles at the harness layer, not with prose.
- **Descriptions route; keep them trigger-only** (see [`artifact.md`](artifact.md)).
- **Budget explicitly.** Tokens, latency, and strand count per task; right-size the fan-out: 1 agent
  for a lookup, 2–4 for a comparison or multi-lens review, more only for genuinely decomposable work.
- **Design the failure path.** Decide up front what happens when a worker returns garbage, nothing,
  or half the contract — and where untrusted content could enter (`agent-security`).

## Failure modes to diagnose

Context poisoning (bad early output contaminates downstream) · telephone-game loss (each
summarization hop drops a constraint) · duplicated/overlapping work from vague lane boundaries ·
ambiguity amplification (one underspecified task fanned to N agents → N interpretations) · barrier
waste · runaway loops with no dry-out condition · missing return contracts.

## Deliverable

A roster delta or design: each agent's lane, trigger description, tool authority, handoff edges (each
agent's own body lists them), context budget, and failure handling. Agents inherit the session's model —
don't add a `model:` pin unless that one agent genuinely needs a different tier. Capture roster-shaping decisions with `adr-template`. Hand
single-artifact wording to [`artifact.md`](artifact.md), implementation to `sde-engineer`, and
injection surfaces to `agent-security`.
