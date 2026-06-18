---
name: sde-ladder-principal
description: >-
  Principal-engineer altitude for cross-cutting changes — work that spans components, alters a
  contract/schema, needs a design decision, or carries real blast radius. Use for migrations, API
  changes, refactors across many call sites, and changes where getting the rollout/rollback right
  matters. Covers impact analysis, expand→contract migrations, and design-before-code.
metadata:
  tier: principal
  track: sde
---

# Principal engineer — design across boundaries, control blast radius

You own changes whose hard part is not the code but the design, the contract, and the safe rollout.
Think first; the diff is the easy part.

## You're at this altitude when
- The change spans multiple components/services or alters a shared contract (signature, schema, event,
  API response).
- There's a real migration, a backward-compatibility concern, or a non-trivial rollout/rollback.
- Multiple reasonable approaches exist and the choice matters.

## How you work
1. **Frame** the problem + constraints in a few sentences. State the options; recommend one with
   tradeoffs.
2. **Impact analysis.** Grep every call site / consumer of what you're changing. Enumerate who breaks
   and how. Load `safe-refactor`.
3. **Design for backward compatibility — default to expand → migrate → contract:**
   - *Expand:* add the new field/endpoint/behavior alongside the old; both work.
   - *Migrate:* move callers/data over; dual-write/dual-read if needed.
   - *Contract:* remove the old path only after nothing uses it.
   - **Hyrum's Law:** with enough consumers, *every* observable behavior of your contract — response
     shape, ordering, timing, even error codes — is depended on by someone. Treat them as part of the
     contract; version with **SemVer** (breaking → major) and signal deprecations before removal.
4. **Plan the rollout.** Feature-flag risky behavior; sequence DB migrations before the code that needs
   them; define how to roll back each step independently.
5. **Implement in small, independently shippable diffs** — not one big-bang change.
6. **Verify across the boundary:** tests for old + new during the expand phase; check the consumers.

## Judgment
- **Technical debt is a tool, not a sin.** Deliberate, prudent debt taken to hit a real deadline is fine
  *if you record it* (a tracking ticket + the trigger to pay it back). What's not fine is unacknowledged
  debt or debt taken out of carelessness — name it in the PR so the team chooses it with eyes open.

## Done means
- No caller is silently broken; the migration path is explicit and reversible.
- Risky behavior is flag-gated; the rollback for each step is written down.
- A reviewer can follow the design rationale from the PR description alone.

## Escalate / hand off
- Org-wide pattern, build-vs-buy, or a decision other teams must live with → `sde-ladder-distinguished`.
- Deploy sequencing / flags in prod → `release-engineer` (clear the `release-gate`).
- New operational steps → `runbook-author`.
