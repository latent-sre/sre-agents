---
name: handoff-protocol
description: >-
  The agent-to-agent (or agent-to-human) HANDOFF PACKET convention. Use whenever work leaves your lane
  and another agent must pick it up — package intent, what's done, what you found, current state, and
  success criteria so the receiver can start cold. This is the transfer format between agents; for
  curating one agent's own attention budget, see `context-engineering`.
metadata:
  domain: convention
---

# Handoff protocol

When work leaves your lane, don't just say "over to you" — **name the target agent and hand them a
packet they can act on without re-deriving anything.** A good handoff is the difference between a fast
chain and a stalled one.

## The handoff packet
```
→ Handing to: <agent>            (the one agent who owns the next step)
Goal:         <the outcome they should achieve, in one line>
Why you:      <one line on why this is their lane>
Done so far:  <what you did / decided — the relevant trail, not everything>
Findings:     <what you learned, each with EVIDENCE (file:line, command output, query, URL)>
Verified:     <what you actually ran/checked + the result; and what's still [unverified]>
Current state:<what's true right now — branch, deploy state, incident status, what's running>
Not done / open: <explicitly what you did NOT do, and known unknowns>
Success when: <how they (and you) know the handoff's goal is met>
Refs:         <links: PR, dashboard, logs, runbook, ticket>
```

## Rules
- **One owner per handoff.** Hand to exactly one agent. If two are needed, sequence them or say which is
  primary.
- **Evidence travels with claims.** Anything load-bearing carries its source; label anything unverified
  so the receiver doesn't trust a guess.
- **State what you did NOT do** — especially for read-only → write handoffs (e.g. `sre-engineer` →
  `release-engineer`: "I changed nothing in prod; recommended mitigation is X with rollback Y").
- **Right-size it.** Enough to start cold; not a transcript. Link the detail, summarize the decision.
- **Prod-facing handoffs** carry the plan + rollback and require the `production-change-gate`.

## Common handoffs
- `sde-engineer` → `code-reviewer`: diff + intent + what you tested (the `merge-gate`).
- `sre-engineer` → incident command (`incident-severity`): symptom, severity, blast radius, timeline so far.
- `sre-engineer` → `release-engineer`: recommended mitigation + exact rollback (you don't execute).
- `*` → `researcher`: the precise question + what decision it informs.
- `*` → `runbook-author`: the procedure/diagnosis to capture, with verified commands.
