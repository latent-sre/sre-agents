# Repo cleanup: retire the redesign's transitional scaffolding

**Date:** 2026-07-15
**Status:** Approved (owner selected all four recommended options)
**Branch:** `codex/cleanup`, stacked on the task-46 tip (`5530e6a`)

## Goal

The Copilot fleet redesign is content-complete (task 46 closed). The repository still carries the
scaffolding that existed only to make that migration safe: the frozen legacy fleet, the format spike,
one-shot phase gates, migration-era process documents, evals that target agents which no longer ship,
and duplicated plugin manifests. Remove all of it. What remains is the product: the canonical fleet
sources, the generated Copilot/Claude projections, the 26 skills, and the durable generator, validator,
gate, guard, eval, and CI machinery.

Target: ~324 tracked files down to roughly 160, about 1.4 MB lighter, with `py -3 scripts/gate_a.py`
green after every commit.

## What stays

- `canonical/` — fleet.json, 5 agent bodies, adr command (source of truth).
- `generated/` — Claude and Copilot projections (regenerated, never hand-edited).
- `skills/` — all 26 skill trees.
- `scripts/` durable machinery: `generate_fleet.py`, `gate_a.py`, `check_links.py`,
  `check_stale_names.py`, `readonly-guard.py`, `readonly-guard-hook.sh`, and the tests for each
  (`test_generate_fleet.py`, `test_check_links.py`, `test_readonly_guard.py`).
  **Correction (2026-07-15, owner-approved):** `validate_fleet.py` + `test_validate_fleet.py` moved
  to cut 1. Verified: its tests can only fixture against `legacy/claude-fleet/`, and the validator
  rejects the shipped fleet on the retired charter (PCF/no-K8s vs. the fleet's deliberate Prometheus
  content) and a roster check expecting retired units. The shipped fleet's structural guardrails are
  `generate_fleet.py --check`/`--require-content-complete`, its contract tests, `check_links.py`,
  and `check_stale_names.py`.
- `evals/` harness (`run_evals.py`, `graders.py`, `clean_room.py`, `discovery_probe.py`, their tests,
  README) and `evals/scenarios/` (25 scenarios; they target skills that still exist).
- `.github/workflows/validate.yml`, `.claude/settings.json`, root instruction files
  (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`), `requirements-dev.txt`, `.mcp.json`,
  `LICENSE`.
- Plugin manifests that a tool actually reads (see cut 4).
- This spec and its implementation plan — the design record for the cleanup itself.

## What goes, in four gate-green commits

### Cut 1 — transitional scaffolding

Delete:

- `legacy/claude-fleet/` (83 files). Existed as the frozen regression reference for the port.
- `spikes/copilot-claude-format/` (22 files). Its findings are baked into the generator and its
  load-bearing facts are captured in this spec's plan before deletion.
- One-shot suites: `scripts/test_no_regressions.py`, `scripts/test_phase1_canonical.py`,
  `scripts/test_phase2_skills.py`, `scripts/test_root_docs.py`.
- `scripts/ralph-loop.sh` if investigation confirms it is the plan-execution loop harness and nothing
  durable references it.

Rewire `scripts/gate_a.py` in the same commit: remove the "Fleet structure (legacy, frozen)",
"No ported regressions (Gate B)", phase-1/phase-2, "Format-spike projection contracts", and
legacy-targeted eval-parse steps. The eval-parse step is repointed at the shipped fleet instead of
`FLEET_ROOT=legacy/claude-fleet`. Scrub now-dangling legacy references from surviving files —
`validate_fleet.py`, `test_generate_fleet.py`, `check_stale_names.py`, `evals/run_evals.py` — so
`check_links.py` and grep sweeps come back clean.

Rationale for deleting rather than keeping Gate B: the regression gate compared ported content against
a frozen source; the port is finished and the six string-detectable Tier-2 bugs it guarded against are
absent from the shipped skills, which the gate itself proved before task 46 closed. Git history and the
pre-cleanup tag preserve the evidence.

### Cut 2 — migration process docs

Absorb, then delete:

- Absorb the durable rules of the redesign spec's Section 0 into `CONTRIBUTING.md`: the sync-from-main
  open protocol (fetch/prune, `--ff-only`, rebase before PR, branch only from `main`), the audit
  ladder (mechanical Gate A, adversarial correctness/security/conformance review, manual-only
  behavioral evals), and the `[verified]`/`[sourced]`/`[unverified]` evidence-label discipline.
  CONTRIBUTING.md already states most of this; the absorption replaces its dead link into the spec
  with the content itself.
- Repoint `AGENTS.md`'s required-workflow paragraph at CONTRIBUTING.md.
- Delete `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md`,
  `docs/superpowers/plans/2026-07-13-copilot-fleet-redesign.md`, the eval-clean-room spec/plan pair,
  `docs/superpowers/evidence/`, `docs/AUDIT-2026-07-12.md`, and `docs/RESEARCH.md`.

`docs/` survives with this cleanup's spec and plan as its only contents; the AGENTS.md layout line for
`docs/` stays.

### Cut 3 — stale discovery evals

Delete every file in `evals/discovery/` whose target agent or capability existed only in the legacy
fleet. Verification is mechanical, per file, against the shipped roster (`observer`, `reviewer`,
`scribe`, `sde`, `sre`) and shipped skill names — filenames are not trusted. Any discovery eval that
already targets the shipped fleet stays. `evals/scenarios/` is untouched. After the cut, the gate's
eval-validate step proves the remaining suite resolves against the shipped fleet — a check that did not
exist while the suite pointed at `legacy/`.

Porting the deleted discovery evals to the new roster is explicitly out of scope (future work).

### Cut 4 — manifest dedupe

**Corrected by verification (2026-07-15):** the Task-33 evidence records a `[verified]` inspection of
the installed VS Code 1.128.1 loader: its selection rule is `.plugin/plugin.json` first, else Claude on
`.claude-plugin/plugin.json`, else root Copilot `plugin.json`. All three plugin manifests are therefore
load-bearing generator projections — `.plugin/plugin.json` is the exact-byte Copilot alias the native
selector requires (without it, root `plugin.json` is unreachable in that client) and seven generator
tests defend it. The original assumption that `.plugin/` was unread is withdrawn.

What this cut actually removes: root `hooks.json` (empty `{"hooks": {}}`), the duplicate of the
auto-loaded standard `hooks/hooks.json` — the spike recorded the live `plugin_errors` mode *"Duplicate
hooks file detected."* `hooks/hooks.json` stays because OpenPlugin hook lookup was explicitly left
`[unverified]` by the evidence packet, so the standard wiring point is preserved. The generator's
`ROOT_OUTPUTS` and render map drop the root file so `--check` stays convergent.

## Execution and verification

- Annotated tag `pre-cleanup-2026-07-15` on the pre-cleanup tip before any deletion (repo precedent:
  tag before garbage collection).
- One commit per cut, in the order above. `py -3 scripts/gate_a.py` must pass after every commit —
  cut 1 lands the gate rewire in the same commit as the deletions it compensates for.
- Each cut opens with a focused check that fails before the change and passes after (per AGENTS.md),
  e.g. a grep asserting no tracked references to `legacy/` outside history before deleting `legacy/`.
- Final sweep: `git grep` proves no tracked file references `legacy/claude-fleet`, `spikes/`, deleted
  doc paths, deleted script names, or `.plugin/`; `check_links.py` (inside Gate A) proves no dangling
  markdown links; CI's entrypoint is unchanged (`gate_a.py`), so the workflow needs no edit.
- Adversarial review (correctness, security/agentic-boundary, plan-conformance) runs on the full diff
  before merge, per CONTRIBUTING.md.

## Decisions log

| Fork | Decision |
|---|---|
| Transitional scaffolding | Delete all (legacy/, spikes/, phase suites), tag first |
| Process docs | Absorb durable rules into CONTRIBUTING.md, then delete |
| Discovery evals | Delete legacy-targeted files; port later as separate work |
| Manifests | Dedupe to verified read paths; fix duplicate-hooks error |

## Risks

- **Gate A shrinks.** Deleting phase gates removes real coverage of the *port*; it removes nothing
  that guards the *shipped* fleet. The durable validator, generator contract, guard, link, and eval
  checks all remain.
- **A manifest guess could be wrong.** Mitigated by verifying read paths against the spike's sourced
  contract documentation before deletion, and by the structural validator.
- **The stacked branch inflates this PR** until the task-46 branch merges; rebase onto `origin/main`
  before opening the PR, per the open protocol.
