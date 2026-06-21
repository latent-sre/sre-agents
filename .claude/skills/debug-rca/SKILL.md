---
name: debug-rca
description: >-
  Disciplined, hypothesis-driven root-cause analysis from symptom to cause — for failing tests, flaky
  builds, runtime errors, and "it works on my machine" bugs (the non-incident sibling of the sre-ladder
  skills). Use when something is broken and the cause is not yet known. Covers reproduce → what changed →
  ranked parallel hypotheses → test one at a time (git bisect) → the causal chain → minimal fix + a
  regression test that would have caught it.
metadata:
  domain: method
---

# Debug / root-cause analysis

Find *why* something is broken — methodically, not by guessing. Reason about the system, not a single
domino. This is the **build/test-time** counterpart to the incident RCA in `sre-ladder-investigator`
(prod) — same discipline, applied to failing tests, flaky builds, and runtime errors. `sde-engineer`
and `test-engineer` load it when a defect's cause is unknown.

## Method
1. **Reproduce.** Establish a reliable, *minimal* repro and capture the exact failure signal — error
   message, stack trace, failing assertion, the specific metric. No repro → you're guessing.
2. **What changed?** Recent commits, deploys, config/flag flips, dependency bumps, data/schema changes,
   environment differences. Correlate against *when* the failure began.
3. **Form hypotheses — several, up front.** List plausible causes and **rank by likelihood × cheapness-
   to-test**. Don't fixate on the first idea.
4. **Test one hypothesis at a time.** Add targeted logging/instrumentation, narrow the inputs, inspect
   state, or **`git bisect`**. Falsify or confirm before moving on — no thematic wandering.
5. **Isolate.** Binary-search the problem space (across commits, layers, inputs) until the cause is
   pinned to a specific line/condition.
6. **Explain the causal chain.** `trigger → mechanism → observed failure`. Name contributing factors,
   not just the proximate one.
7. **Fix minimally + guard it.** Smallest change that fixes the *cause* (not the symptom), plus a
   **regression test that fails without the fix** (see `tdd-workflow`).

## Diagnostic toolkit
- `git log` / `git diff` / **`git bisect`** — locate the introducing change.
- Targeted logs/traces; re-run with verbose output; inspect the failing layer's inputs/outputs.
- Flaky tests: look for order-dependence, shared state, real clock/network/random, timing/races
  (run repeatedly, shuffle order, freeze the clock).
- Distributed/runtime issues: **metrics → traces → logs** to go *that* → *where* → *why*.

## Principles
- **Evidence over intuition** — confirm each step against observed behavior; label anything unverified.
- Distinguish **root cause** (the fix point) from **symptoms** (what you saw) and **contributing
  factors**. Fix the cause; then verify the fix actually clears the original signal.

## Output
**Symptom → Reproduction → Investigation** (hypotheses tested + evidence) **→ Root cause** (`file:line`
+ causal chain) **→ Fix** (minimal change) **→ Regression test**. Cite the evidence that pinpointed it.

## Worked example (the hypothesis table is the method)
*Symptom: `test_export` passes locally, fails in CI since ~Tue.* Rank by likelihood × cheapness-to-test:

| # | Hypothesis | Likelihood | Test (cheap → dear) | Result |
|---|---|---|---|---|
| 1 | CI uses a different TZ → date assertion off by one | high | print `date` in CI; freeze the clock in the test | **confirmed** — CI is UTC, dev is ET |
| 2 | Dependency bump changed CSV quoting | med | `git diff` the lockfile around Tue | ruled out (no change) |
| 3 | Test order / shared temp file | low | `pytest -p no:randomly` vs shuffled | ruled out |

Causal chain: *unpinned test clock → asserts a localized date → passes in ET, fails in UTC CI.* Minimal
fix: inject/freeze the clock; **regression test** asserts the export under a fixed TZ (fails without the
fix). Note the contributing factor — the env difference — not just the proximate assertion.

## Handoffs
- → `sde-engineer` for the code fix · → `test-engineer` for the regression test if it deserves focus.
- If the symptom is in **production** (alert, user impact, degraded PCF app), escalate to `sre-engineer`
  / the `sre-ladder-*` skills instead — that's incident RCA, not build-time debugging.
- → `researcher` for an external library/version/bug-report fact you can't confirm from the repo.
