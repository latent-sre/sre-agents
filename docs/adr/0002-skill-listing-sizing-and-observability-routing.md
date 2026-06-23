# ADR-0002: Skill-listing sizing and observability routing — measured, not restructured

- **Status:** Accepted
- **Date:** 2026-06-23
- **Deciders:** SRE+SDE fleet maintainers

## Context

A deep review of the skill layer proposed three changes, tiered by blast radius:

- **Tier 1** — demote the five "Anthropic-pattern" meta-skills (`context-engineering`,
  `parallelization`, `tool-design`, `agent-security`, `self-improve-loop`) out of the always-on skill
  listing, to cut its token cost and reduce selection dilution.
- **Tier 2** — sharpen colliding skill descriptions, trim two over-long ones, and give per-language test
  frameworks a single home.
- **Tier 3** — add a routing/dispatch layer over the nine flat observability skills (`splunk-triage`,
  `wavefront-queries`, `grafana-dashboards`, `moogsoft-correlation`, `thousandeyes-network`,
  `triage-golden-signals`, `slo-error-budget`, `instrument-service`, `pcf-ops`), on the theory that they
  are hard to select among.

Tiers 1 and 3 are structural and were contested. Rather than restructure on intuition, we measured.

## Decision

**Ship Tier 2; decline Tiers 1 and 3.**

**Tier 2 (shipped, PR #23).** Front-loaded the discriminator on colliding descriptions
(`triage-golden-signals` vs `sre-ladder`; `release-gate` "readiness?" vs `production-change-gate`
"authorization?"), trimmed the two longest descriptions to a table-of-contents (`spa-architecture`
593→387, `self-improve-loop` 563→391 chars), and folded `tdd-workflow`'s per-language framework table to
a pointer (`craft` owns the tooling, `tdd-workflow` owns the method). Zero behavior change; CI green.

**Tier 1 — declined on two independent grounds:**

1. **Budget.** `skillListingBudgetFraction` is `0.04` in this repo → ~40K-token listing budget on a
   1M-context model; all 38 descriptions cost ~3.9K tokens (**~10× headroom**). Even at a 200K context the
   `0.04` setting leaves ~2× headroom. Nothing is truncated. (Confirmed against the docs: default fraction
   is 1%; over budget, descriptions are dropped least-used-first.)
2. **Discovery.** An A/B with the four method-skills set to `skillOverrides: name-only` (description
   dropped from the listing, name kept) scored **6/12 → 6/12** vs baseline — no discovery loss *and* no
   measurable gain. The skill *name* alone carries the routing signal wherever it routes at all.

The mechanism exists and is safe — `name-only` via `settings.json` keeps agent-prose "load `X`" paths
working (whereas `disable-model-invocation` would break them) — so demotion is a **back-pocket lever keyed
to runtime, not a thing to do now**.

**Tier 3 — declined on evidence.** A discovery probe over eight ambiguous *symptom* prompts (the tool is
never named) routed to the correct per-tool skill **23/24 (96%) with zero cross-tool misroutes**; the one
miss answered from general knowledge without loading any skill — not a wrong pick. The model never got
stuck at `triage-golden-signals` framing either, so a dispatcher has nothing to rescue. A router would add
a hop and another broad-trigger listing entry to "fix" an already-correct baseline — negative expected
value.

## Evidence (reproducible)

Built [`evals/discovery_probe.py`](../../evals/discovery_probe.py) — a sibling to `run_evals.py` that,
unlike it, does **not** pre-inject the target skill; it reads which `Skill(...)` the model invokes from
the `stream-json` trace, so it measures *autonomous discovery*. Re-run:

```bash
python evals/discovery_probe.py --ab                 # Tier-1 A/B (listed vs name-only)
python evals/discovery_probe.py --run --match obs    # Tier-3 observability baseline
```

| Probe | Result |
|---|---|
| Tier-1 A/B (4 method-skills, 3 trials) | A (listed) **6/12** = B (name-only) **6/12** — no change |
| Tier-3 observability (8 symptoms, 3 trials) | **23/24** discovered the right tool; **0** misroutes |

Caveats: the probe needs a live model (not a CI gate — only `--validate` is); small N (3 trials),
keyword-cued prompts — directional, not proof.

## Consequences

**Positive**

- Three "we should restructure" hunches resolved with data; the listing stays flat and lean-enough, with
  no new hops or broad-trigger entries.
- The probe harness is now a reusable instrument for the next routing question (it caught its own
  limitation too: the pre-existing suite pre-injects the target and so cannot measure discovery).

**Negative / trade-offs**

- Two minor overlaps left unaddressed and accepted (no misroute): `self-improve-loop` ↔ `tdd-workflow` on
  "stop a recurring regression" (arguably correct behavior), and `moogsoft-correlation` at 2/3.

## Revisit if

- The fleet runs on a **small-context model at the default 1% budget** (the `0.04` override not travelling
  with it) → truncation becomes real; apply `skillOverrides: name-only` to the method-skills (re-run
  `--ab` first to confirm discovery survives).
- The observability skill set **grows materially or descriptions drift** → re-run `--run --match obs`; if
  routing drops below ~85% or *misroutes* (not just general-knowledge answers) appear, reopen Tier 3.
