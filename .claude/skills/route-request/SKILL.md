---
name: route-request
description: >-
  The routing/selector decision table — classify an SRE/SDE request and route it to the right agent(s)
  in the right order, with the gates that apply. Use at the start of any multi-step or ambiguous request
  to produce a delegation plan, or to decide whether a request even needs delegation. Backs the
  coordinator agent.
metadata:
  domain: routing
---

# Route a request (selector)

Classify intent → pick the minimum agents → sequence them → insert gates. If the whole request is one
obvious specialist task, **say so and route directly** — don't manufacture ceremony.

## 1. Classify intent
`build` · `review` · `operate/incident` · `release` · `document` · `research`. Note **urgency** (is
something on fire?).

## 2. Route (decision table)
| Signal in the request | Primary agent | Then (typical chain) |
|---|---|---|
| "implement / build / refactor / fix code" | `sde-engineer` (pick `sde-ladder-*` by scope; load language `*-craft`) | → `code-reviewer` (+`security-reviewer` if sensitive, `test-engineer` if thin) → **`merge-gate`** |
| "schema change / migration / slow query / DB-bound" | `sde-engineer` + **`database-reliability`** skill | → `code-reviewer` → **`merge-gate`**; prod migration → `release-engineer` + **`production-change-gate`** |
| "review this diff / is this correct" | `code-reviewer` | → `security-reviewer` if security depth needed |
| "is this secure / auth / secrets / deps" | `security-reviewer` | → `sde-engineer` to fix |
| "write tests / add coverage" | `test-engineer` | → `sde-engineer` if it reveals a bug |
| "failing test / flaky build / bug, cause unknown" | `sde-engineer` (or `test-engineer`) + **`debug-rca`** skill | → `sde-engineer` for the fix; → `sre-engineer` if it's actually a prod incident |
| "X is broken / slow / erroring / alerting" | `sre-engineer` (`sre-ladder-*` by depth) | → `incident-commander` if major; → `release-engineer` to mitigate |
| "run the incident / comms / who's doing what" | `incident-commander` | ⇄ `sre-engineer` (technical) in parallel |
| "set up monitoring / noisy alert / define SLO" | `sre-monitor` | → `runbook-author` for alert runbooks |
| "ship / release / deploy / roll back / move off Bamboo" | `release-engineer` | **`release-gate`** + **`production-change-gate`** for prod |
| "write/update a runbook / document this" | `runbook-author` | — |
| any agent is missing a fact | `researcher` | → back to the requester |

## 3. Insert gates (pass/fail checkpoints, not agents)
- Before merge → **`merge-gate`**.
- Before any prod deploy → **`release-gate`** then **`production-change-gate`**.

## 4. Output a plan
```
Intent: <…> (urgency: <low|high|critical>)
Plan:
  1. [agent] <task> — context to pass: <…> — done when: <…>
  2. [agent] <task> — depends on: 1 — gate: <…> — context: <…>
Parallelizable: <…>
Risks / watch-for: <…>
```
Each step names the **context to hand the agent** so it can start cold (`handoff-protocol`). For
prod-facing or destructive steps, mark them and require explicit human confirmation.
