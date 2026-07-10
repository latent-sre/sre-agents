---
name: route-request
description: >-
  The routing/selector decision table — classify an SRE/SDE request and route it to the right agent(s)
  in the right order, with the gates that apply. Use at the start of any multi-step or ambiguous request
  to produce a delegation plan, or to decide whether a request even needs delegation. This is the fleet's
  routing logic — the main session loads it to plan multi-step work (there is no separate coordinator agent).
---

# Route a request (selector)

Classify intent → pick the minimum agents → sequence them → insert gates. If the request is one obvious
specialist task, **say so and route directly** — don't manufacture ceremony.

## 1. Classify intent
`build` · `review` · `operate/incident` · `release` · `document` · `research`. Note **urgency** (is
something on fire?).

## 2. Route (decision table)
| Signal in the request | Primary agent | Then (typical chain) |
|---|---|---|
| "implement / build / refactor / fix code" | `sde-engineer` (pick `sde-ladder` by scope; load language `craft`) | → `code-reviewer` (+`security-reviewer` if sensitive, `test-engineer` if thin) → **`merge-gate`** |
| "build a tool for the ops side — a CLI, an API endpoint, or a web GUI" | `sde-engineer` (pick the shape: **`ops-cli`** / **`api-design`** / **`spa-architecture`**; + **`ops-stack-integration`** if it calls cf/Splunk/Wavefront/Moogsoft; + the language `craft`) | → `code-reviewer` (+`security-reviewer` for auth/secrets/token/CORS) → **`merge-gate`** |
| "review this diff / is this correct" | `code-reviewer` | → `security-reviewer` if security depth needed |
| "is this secure / auth / secrets / deps" | `security-reviewer` | → `sde-engineer` to fix |
| "write tests / add coverage" | `test-engineer` | → `sde-engineer` if it reveals a bug |
| "failing test / flaky build / bug, cause unknown" | `sde-engineer` (or `test-engineer`) + **`debug-rca`** skill | → `sde-engineer` for the fix; → `sre-engineer` if it's actually a prod incident |
| "DB schema/migration / slow query / DB incident" | `database-reliability` (loads the **`database-reliability`** skill; pairs with `sde-engineer` on query/ORM code) | → `code-reviewer` → **`merge-gate`**; prod migration → `release-engineer` runs it under **`production-change-gate`** |
| "X is broken / slow / erroring / alerting" | `sre-engineer` (`sre-ladder` by depth) | → run the incident-command process (`incident-severity`) if major; → `release-engineer` to mitigate |
| "run the incident / comms / who's doing what" | load **`incident-severity`** (severity, roles, comms, timeline) | ⇄ `sre-engineer` (technical RCA) in parallel |
| "set up monitoring / noisy alert / define SLO" | `sre-monitor` | → `runbook-author` for alert runbooks |
| "ship / release / deploy / roll back / move off Bamboo" | `release-engineer` | **`release-gate`** + **`production-change-gate`** for prod |
| "write/update a runbook / document this" | `runbook-author` | — |
| "write/tune an agent, skill, or prompt / skill never triggers / agent ignores instruction" | `prompt-engineer` (loads **`prompt-craft`** for one artifact, **`agent-architecture`** for roster/orchestration design) | → `security-reviewer` if the artifact ingests untrusted input; → `code-reviewer` for gate/guard wording changes |
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
Each step names the **context to hand the agent** so it can start cold (`handoff-protocol`). Mark
prod-facing or destructive steps and require explicit human confirmation. When the plan has independent
strands (or wants multi-lens review/voting), load **`parallelization`** to decide whether to fan them out
concurrently and whether the cost pays.

## Guardrails
- **Don't invent an agent** not in the fleet — if none fits, say so (or have the main session do it).
- **Stay a router.** If you find yourself investigating or writing code, stop and route it — routing runs
  in the main session's context, not a separate one.
