---
name: self-improve-loop
description: >-
  Generate → evaluate → refine loops, from Anthropic's agent patterns: the evaluator-optimizer, the
  act → verify → repeat loop, and the unattended outer ("Ralph") loop. Use when output quality is
  measurable and iteration demonstrably improves it — a draft to harden, a fix to verify, a test-backed
  build to grind through. Prefers deterministic checks (tests, linters, gates) over LLM-as-judge.
metadata:
  domain: method
---

# Self-improvement loops

Make output better by **checking it and acting on the check** — not by trying harder in one pass. Two
shapes from Anthropic's *Building Effective Agents* and the Claude Agent SDK, adapted to this fleet.

> **Start simple.** A single well-prompted pass handles most work. Add a loop only when (a) you can
> *measure* quality against clear criteria and (b) iteration *demonstrably* improves the result. A loop
> with no real evaluator is just extra tokens. *[sourced: Anthropic, "Building Effective Agents"]*

## Pattern 1 — Evaluator-optimizer (generate → critique → revise)

One role generates a candidate; a **separate** role evaluates it against explicit criteria and returns
actionable feedback; the generator revises. Loop until the evaluator is satisfied or the budget is hit.
*[sourced: Anthropic, "Building Effective Agents" — evaluator-optimizer workflow]*

- **Use when** the criteria are articulable and feedback measurably helps (code review comments, a
  rubric, a failing test, a security finding) — and the gap between "first draft" and "good" is real.
- **In this fleet:** `sde-engineer` generates → `code-reviewer`/`security-reviewer` evaluate → fixes
  loop back. `test-engineer` raises coverage against the same diff. The **gates** are the formal
  evaluator checkpoint (`merge-gate`, `release-gate`).
- **Separate the roles.** A fresh-context evaluator (or a different agent) catches more than self-
  critique in the same context — bias toward a second lens for anything load-bearing.

## Pattern 2 — The agent verify-loop (act → verify → repeat)

The Claude Agent SDK loop: **gather context → take action → verify the work → repeat** until done.
The leverage is in *verify* — an action you don't check is an assumption. *[sourced: Claude Agent SDK,
"How the agent loop works"]*

**Order your verifiers cheapest-and-surest first:** *[sourced: Anthropic agent guidance — prefer
rules-based feedback over LLM-as-judge]*

1. **Deterministic checks** — tests, linters/type-checks, schema/`EXPLAIN` validation, a gate
   checklist, the `readonly-guard`. Fast, reliable, no judgment risk. **Default to these.**
2. **Observed signal** — run it and read the result: the failing assertion clears, golden signals
   (`triage-golden-signals`) return to baseline, the `cf` health check passes.
3. **LLM-as-judge** — a reasoning review (`code-reviewer`, `security-reviewer`) for the things rules
   can't encode (design, intent, subtle correctness). Use it *after* the cheap checks, not instead.

> When the **same failure recurs**, encode it as a rules-based check (a test, a lint rule, a gate item,
> a hook) rather than re-judging it by reasoning each time. Move the lesson left.
> *[sourced: Anthropic — "add rules-based feedback via hooks when you see repeated failure patterns"]*

## Pattern 3 — The unattended outer loop ("Ralph")

Brute-force the verify-loop from *outside* the agent: a shell loop re-invokes a **fresh** coding-agent
process each iteration against a **spec + a task backlog in files**, so durable state lives in the repo
(spec, backlog, code, git history) — not in a context window that rots. Each pass: read the backlog, do
the **next one item**, run the verifier, commit *only if it passes*, exit; the loop restarts clean.
*[sourced: Geoffrey Huntley, "Ralph Wiggum as a software engineer"; mechanics = `context-engineering`
(externalize state) + Pattern 2 (act → verify), run as an outer loop.]*

- **Use when** the work is large, decomposable, and **test-backed** — greenfield building of ops tooling
  (a CLI/API/SPA) against a spec where each unit verifies mechanically. **Not** for triage, review, or
  anything prod-facing.
- **Why it works:** fresh context per iteration sidesteps context rot; the files are the memory. (Our
  `evals/run_evals.py` already uses fresh-process-per-trial for the same reason.)
- **Why it's dangerous bare:** an outer loop with no hard verifier makes confident messes at machine
  speed. The verifier *is* the safety system — it is not optional.

**Non-negotiable guardrails (this is an ops repo):**
1. **Code-building on a branch only.** Never point it at `release-engineer`/prod actions — no `cf push`,
   route remap, scale, or migration in a loop. The `readonly-guard` + `production-change-gate` lines hold.
2. **A hard verify gate every iteration.** Tests/evals/linters must pass or the iteration is rejected and
   **not committed** (`tdd-workflow`; Pattern 2's deterministic checks first). No verifier → don't run it.
3. **Bounded + a real stop condition** — a max-iteration cap and an explicit exit (backlog empty AND
   verifier green). Watch token cost; an outer loop spends like a multi-agent fan-out.
4. **A human clears `merge-gate` before merge.** The loop produces a diff on a branch, never a deploy.

A reference scaffold that enforces all four rails lives at [`ralph-loop.sh`](../../../scripts/ralph-loop.sh)
in the repo's scripts directory — it is an example you run yourself, deliberately **not** wired into CI or
any agent. A loop that can change prod, or that commits unverified work, is not a Ralph loop — it's an
incident generator.

## Run the loop well
- **Bound it.** Set a max-iterations budget up front (often 2–3). No convergence by then → stop and
  hand off with what you found; don't spin.
- **Define "done" before you start.** The stop criterion is the evaluator passing, not "feels good."
- **One change per turn, then re-verify** — so you know which change moved the signal (mirrors
  `debug-rca` and `rollback-mitigation`).
- **Altitude sets depth.** The ladder skills decide how many lenses and iterations a task earns —
  `sde-ladder` (senior tier)/`sre-ladder` (responder tier) for a quick check; the principal/elite tiers for multi-lens,
  blast-radius-aware loops.
- **Don't loop on prod.** Verify in lower envs; production changes still go through the gates with human
  sign-off (`production-change-gate`). Read-only agents *recommend* the next iteration; they don't apply it.

## Output
State the **criteria**, each **iteration** (what changed → how it was verified → result), and the
**stop reason** (criteria met / budget hit / handed off). Label each verification `[verified]`
(ran/observed — show it), `[sourced]`, or `[unverified]`, per the fleet evidence convention.

## Handoffs
- → `code-reviewer` / `security-reviewer` as the evaluator lens; → the **gates** as the formal
  checkpoint. → `test-engineer` to turn a recurring miss into a permanent deterministic check.
- → `debug-rca` when verification *fails for an unknown reason* (the loop found a bug; now find its
  cause). → `sde-engineer` to apply a confirmed revision.
