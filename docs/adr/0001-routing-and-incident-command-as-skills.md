# ADR-0001: Routing and incident-command are skills, not agents

- **Status:** Accepted
- **Date:** 2026-06-22 (justification amended 2026-06-23 — see note below)
- **Deciders:** SRE+SDE fleet maintainers

> **Amendment (2026-06-23):** the decision is unchanged, but its rationale was rewritten. The original
> draft leaned on a capability limit ("a classic subagent cannot dispatch others"). Claude Code now
> supports nested subagent dispatch, so that premise is obsolete. The **cost** argument — which never
> depended on the capability limit — now leads, and the Revisit section gates any reversal on a concrete
> A/B experiment.

## Context

The fleet modeled two orchestration roles as subagents: `coordinator` (turn a request into an ordered
delegation plan) and `incident-commander` (run the *process* of a live incident — severity, roles,
timeline, comms).

**The durable reason these are skills, not agents, is cost — not a capability limit.** Routing and
incident-command both need to *act within the same context that holds the live request or incident*. A
coordinator subagent works against that on two fronts:

- **It double-pays the routing round-trip.** The subagent pays a cold-start (system prompt + preloaded
  skills + re-reading files), produces a short plan, and then the main session re-reads that plan and
  re-derives context to execute it — the routing decision is paid for **twice, across two contexts**.
- **It discards exactly the context the live work needs.** The only thing a subagent buys — an isolated
  context window — is thrown away when the plan is handed back. For incident-command it is actively
  harmful: isolating the commander from the investigator's live findings is the opposite of useful. The
  whole value of these two roles is being *in* the main conversation, which a subagent definitionally is
  not.

This cost reasoning holds **regardless of nesting depth**. (Note: Claude Code has since added **nested
subagent dispatch** — a subagent can now spawn others, ~5 levels deep — so the earlier capability
constraint, "a classic subagent cannot dispatch others, so an orchestration agent could only emit a plan,"
**no longer applies**. We are not relying on it. Even with nested dispatch available, a coordinator
subagent still double-pays the round-trip and still discards the main session's context; the cost case is
unaffected.)

Four independent reviews of the 12-agent fleet (minimalist, best-practice, routing/usability, adversarial)
each converged on demoting these two. Anthropic's sub-agents guidance is explicit: prefer a **skill** for
"reusable prompts or workflows that run in the main conversation context rather than isolated subagent
context."

## Decision

Demote `coordinator` and `incident-commander` from agents to skills:

- **`coordinator` → `route-request`** (the skill already existed and backed the agent; it absorbed
  coordinator's two unique guardrails). The main session loads it to plan multi-step work.
- **`incident-commander` → `incident-severity`** (broadened to carry the incident-command process —
  roles, the live timeline, drive-to-mitigation, and the status output contract, folded in losslessly).
  Loaded by `sre-engineer` or a human incident commander in the main session.

The fleet goes from **12 agents to 10**; the skill count is unchanged (no new skill). No capability is
lost — the substance moved into skills that run where the dispatching actually happens.

## Consequences

**Positive**

- Removes the double-paid routing round-trip and the discarded-context cost.
- Improves auto-routing: two fewer paragraph-length agent descriptions competing in the router (the
  routing/usability review flagged coordinator/IC as ambiguity sources).
- Routing and incident-command now run with the full request/incident context in the window that acts on it.

**Negative / trade-offs**

- `incident-commander` carried the read-only `PreToolUse` guard (one of four Bash agents → now three). A
  *human* IC driving the skill in the main session is not constrained by that hook; the safety story for
  prod actions still rests on the gates (`production-change-gate`), which is where it belonged anyway.
- `incident-severity` is now a broader skill (severity + comms + command). Accepted over creating a new
  `incident-command` skill, to avoid re-inflating the skill count we are trying to keep lean.

## Revisit if

The capability constraint is already gone (nested subagent dispatch exists), so the trigger to revisit is
no longer "can the harness dispatch?" but **"does a dispatch-capable coordinator agent actually beat
`route-request`-as-skill on measured outcomes, despite the cost?"** Do not reverse this on reasoning alone —
run the A/B first:

- **Experiment:** compare (A) `route-request` run as a skill in the main session against (B) a
  dispatch-capable `coordinator` *agent* that plans and then dispatches the sub-agents itself. Measure with
  [`evals/discovery_probe.py`](../../evals/discovery_probe.py) plus the routing scenarios under
  [`evals/`](../../evals/): does the routing land on the right agents, and what is the token/latency cost of
  the extra hop? Record the result the way this Tier-1 decision was recorded (an ADR update or a dated note
  in [docs/FOLLOWUPS.md](../FOLLOWUPS.md)).
- **Reverse only if** (B) routes at least as accurately as (A) **and** the coordinator's added context
  isolation buys something the main session can't (e.g. very large fan-out where the main context would
  otherwise overflow) that outweighs the double-paid round-trip. Absent that evidence, the cost case stands
  and the skill shape holds — this demotion is "until an A/B says otherwise," not "forever."
