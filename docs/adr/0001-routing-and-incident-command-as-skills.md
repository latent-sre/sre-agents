# ADR-0001: Routing and incident-command are skills, not agents

- **Status:** Accepted
- **Date:** 2026-06-22
- **Deciders:** SRE+SDE fleet maintainers

## Context

The fleet modeled two orchestration roles as subagents: `coordinator` (turn a request into an ordered
delegation plan) and `incident-commander` (run the *process* of a live incident — severity, roles,
timeline, comms).

In Claude Code's classic, portable subagent model, **a subagent cannot spawn or dispatch other
subagents** — only the main session delegates (see [CLAUDE.md](../../CLAUDE.md)'s *Subagent dispatch*
note; the same holds for VS Code / Copilot custom agents). An agent whose job is to orchestrate others
therefore cannot act on its output: it can only emit a *plan* handed back to the main session, which then
does the dispatching.

That makes the orchestration-as-agent shape a net cost:

- The subagent pays a cold-start (system prompt + preloaded skills + re-reading files), produces a short
  plan, and then the main session re-reads that plan and re-derives context to execute it — the routing
  decision is paid for **twice, across two contexts**.
- The only thing a subagent buys — an isolated context window — is **discarded** when the plan is handed
  back. For incident-command it is worse: isolating the commander from the investigator's live findings is
  the opposite of useful.

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

- We adopt Claude Code **"agent teams"** or any dispatch-capable harness, **or** Copilot custom agents gain
  nested dispatch. At that point an orchestration agent *can* act on its plan, and re-promoting
  `coordinator` / `incident-commander` may pay. This demotion is "until the harness can dispatch," not
  "forever."
