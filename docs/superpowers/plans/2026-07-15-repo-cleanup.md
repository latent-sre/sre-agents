# Repo Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the fleet redesign's transitional scaffolding (legacy fleet, spike, phase gates, migration docs, stale evals, duplicate hooks manifest) while keeping the shipped Copilot/Claude fleet and its durable machinery, per the approved spec `docs/superpowers/specs/2026-07-15-repo-cleanup-design.md`.

**Architecture:** Four gate-green commits (scaffolding, docs, evals, manifests), each pairing deletions with the rewiring that keeps `py -3 scripts/gate_a.py` passing. An annotated tag preserves the pre-cleanup tree.

**Tech Stack:** git, Python 3 (`py -3` on this machine), stdlib-only scripts.

## Global Constraints

- `py -3 scripts/gate_a.py` must PASS after every commit (exit 0).
- Never hand-edit `generated/**` or the five manifest projections; change `scripts/generate_fleet.py` and regenerate.
- Surgical diffs: no reformatting of surviving code beyond removing references to deleted artifacts.
- Evidence labels: every claim in commit messages/reports is `[verified]` (command run here) or `[unverified]`.

## Evidence ledger (verified during planning, 2026-07-15)

- `run_evals.py:47` — `ROOT = Path(os.environ.get("FLEET_ROOT") or <repo root>)`; unsetting `FLEET_ROOT` points it at the shipped fleet. `[verified]`
- `py -3 evals/run_evals.py --validate` (shipped root) fails on exactly 13 scenario files whose targets are retired units: `handoff-preserves-untrusted-taint`, `incident-severity-classifies`, `ops-cli-safety`, `readonly-agent-recommends-not-acts`, `rollback-mitigation-picks-reversible`, `route-request-active-technical-investigation`, `route-request-build-api-ui`, `route-request-fanout-decision`, `route-request-live-incident-coordination`, `route-request-resolved-incident-writeup`, `runbook-author-resolved-postmortem-structure`, `sde-ladder-principal`, `self-improve-ralph-guardrails`. `[verified]`
- `discovery_probe.py:60-61` hardcodes `SKILLS_DIR = ROOT/".claude/skills"`, `AGENTS_DIR = ROOT/".claude/agents"` — the pre-migration layout; all 45 `evals/discovery/*.yaml` target that dead layout. `test_discovery_probe.py` pins no paths. `[verified]`
- **All three `plugin.json` projections are load-bearing.** Task-33 evidence records a `[verified]` inspection of the installed VS Code 1.128.1 loader: selector rule is `.plugin/plugin.json` first, else Claude on `.claude-plugin/plugin.json`, else root Copilot `plugin.json`. The generator emits `.plugin/plugin.json` as an exact-byte alias of root `plugin.json` and 7 tests defend it. The spec's cut-4 assumption that `.plugin/` is unread is **corrected**: it stays. Only root `hooks.json` (empty, duplicate of auto-loaded `hooks/hooks.json`, the spike's documented `plugin_errors` mode) is removed. Hook lookup for the OpenPlugin channel is `[unverified]` per the evidence doc, so `hooks/hooks.json` stays as the standard wiring point.
- `generate_fleet.py` owns all five manifest projections (`ROOT_OUTPUTS`, lines 212-218; render map, lines 1267-1273). `[verified]`
- `test_generate_fleet.py` transitional members: `TASK33_EVIDENCE_PATH` (line 38), `PINNED_LEDGER_KEYS` (84), `PINNED_SCHEDULED_LEDGER_TASKS` (179), `_assert_pinned_ledger` (309), tests `test_disposition_ledger_rows_and_projection_counts_are_closed` (642), `test_ledger_rejects_coordinated_identity_substitution` (701), `test_task32_obs_pipeline_preserves_the_planned_disposition` (712, reads `legacy/`). Durable constants `PINNED_SKILLS`, `PINNED_SKILL_DEPENDENCIES`, `TASK32_DEPENDENCIES` are used by fixtures and surviving tests — keep. `[verified]`
- `ralph-loop.sh` is a hand-run example scaffold for the retired `self-improve-loop` skill; referenced only by legacy/, docs being deleted, the ledger pins being deleted, and the stale ralph scenario. `[verified]`
- `check_stale_names.py` scans only `skills/`, `canonical/agents`, `canonical/commands`, `canonical/fleet.json` — unaffected by these deletions. `[verified]`
- **Execution finding (owner-approved fork):** `test_validate_fleet.py` fixtures against `legacy/claude-fleet/` (its `_copy` helper returns that path), and `validate_fleet.py` run against a synthetic shipped-fleet root fails on retired-charter scope rules ("repo is PCF / no-K8s" vs. shipped Prometheus content) and roster checks expecting `route-request`/root docs. `[verified]` Both files deleted in cut 1; the "Validator's own tests" gate step removed with them.

---

### Task 1: Tag the pre-cleanup state

**Files:** none (git ref only)

- [ ] **Step 1:** `git tag -a pre-cleanup-2026-07-15 -m "Tree before retiring redesign transitional scaffolding (spec 2026-07-15)" && git tag -l pre-cleanup*` → tag listed. Push together with the branch when the PR opens.

### Task 2 (cut 1): Delete transitional scaffolding, rewire Gate A

**Files:**
- Delete: `legacy/` (83 files), `spikes/` (22 files), `scripts/test_no_regressions.py`, `scripts/test_phase1_canonical.py`, `scripts/test_phase2_skills.py`, `scripts/test_root_docs.py`, `scripts/ralph-loop.sh`
- Modify: `scripts/gate_a.py:36-73`, `scripts/test_generate_fleet.py` (members above), `scripts/validate_fleet.py:64-70` (comment + dead `.claude` layout entry), `evals/run_evals.py:69` (comment)

- [ ] **Step 1 (focused check, must FAIL first):** `git grep -lE "legacy/claude-fleet|spikes/|ralph-loop" -- ':!docs/superpowers' && echo REFS-REMAIN` → prints files (the check that must end clean).
- [ ] **Step 2:** `git rm -r -q legacy spikes scripts/test_no_regressions.py scripts/test_phase1_canonical.py scripts/test_phase2_skills.py scripts/test_root_docs.py scripts/ralph-loop.sh`
- [ ] **Step 3:** Replace `gate_a.py` lines 36-73 (the `LEGACY` dict + `STEPS`) with:

```python
STEPS = [
    ("Reference links load in VS Code (5d)",
     ["scripts/check_links.py"], None),
    ("No stale unit names",
     ["scripts/check_stale_names.py"], None),
    ("Validator's own tests",
     ["-m", "unittest", "discover", "-s", "scripts", "-p", "test_validate_fleet.py"], None),
    ("Generated fleet contract",
     ["-m", "unittest", "discover", "-s", "scripts", "-p", "test_generate_fleet.py"], None),
    ("Generated fleet is current",
     ["scripts/generate_fleet.py", "--check"], None),
    ("Fleet content complete",
     ["scripts/generate_fleet.py", "--require-content-complete"], None),
    ("Read-only guard",
     ["scripts/test_readonly_guard.py"], None),
    ("Eval graders",
     ["evals/test_graders.py"], None),
    ("Discovery probe",
     ["evals/test_discovery_probe.py"], None),
    ("Clean-room rig",
     ["evals/test_clean_room.py"], None),
]
```

  The eval-parse step is deliberately ABSENT here: with `legacy/` gone it cannot run against the old
  fleet, and against the shipped fleet it fails until Task 4 deletes the 13 stale scenarios. Task 4
  re-adds it pointed at the shipped fleet, restoring the coverage in the same commit that makes it
  green.

  Decision point: first run `py -3 scripts/validate_fleet.py` with no env. If it resolves the shipped layout and passes, add `("Fleet structure (shipped)", ["scripts/validate_fleet.py"], None)` as the first step; if it cannot (no root `agents/` dir), leave it to its unit tests and record that in the commit message. Also update the module docstring's spec reference (Task 3 deletes the spec): point at `CONTRIBUTING.md`.
- [ ] **Step 4:** In `test_generate_fleet.py` delete: `TASK33_EVIDENCE_PATH`, `PINNED_LEDGER_KEYS`, `PINNED_SCHEDULED_LEDGER_TASKS`, `_assert_pinned_ledger`, and the three tests at 642/701/712. Then `grep -n "TASK33_EVIDENCE\|PINNED_LEDGER\|PINNED_SCHEDULED\|pinned_ledger" scripts/test_generate_fleet.py` → no hits.
- [ ] **Step 5:** `validate_fleet.py`: rewrite the lines 64-70 comment to describe the current layout without the `legacy/claude-fleet` path; drop the dead `('.claude/skills', '.claude/agents')` entry from `_LAYOUTS` if nothing else uses it. `run_evals.py:69`: reword comment without `legacy/claude-fleet/`.
- [ ] **Step 6:** `py -3 scripts/gate_a.py` → `Gate A: PASS`. Step-1 grep → no output.
- [ ] **Step 7:** `git add -A && git commit` — message: `cleanup: retire migration scaffolding (legacy fleet, spike, phase gates)`.

### Task 3 (cut 2): Absorb durable rules, delete migration docs

**Files:**
- Modify: `CONTRIBUTING.md:20-24`, `AGENTS.md:18`, `README.md:85-86`
- Delete: `docs/AUDIT-2026-07-12.md`, `docs/RESEARCH.md`, `docs/superpowers/evidence/`, `docs/superpowers/plans/2026-07-13-copilot-fleet-redesign.md`, `docs/superpowers/plans/2026-07-13-eval-clean-room.md`, `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md`, `docs/superpowers/specs/2026-07-13-eval-clean-room-design.md`

- [ ] **Step 1:** In `CONTRIBUTING.md`, replace the sentence `Follow [Section 0 of the design](...)` (line 22) with the absorbed protocol:

```markdown
Open every working session from a clean tree: `git fetch --prune origin`, `git switch main && git pull
--ff-only origin main` (`--ff-only` fails loudly instead of manufacturing a merge commit), record the
base SHA, and branch from `main` — never from another feature branch. Before opening a PR, `git rebase
origin/main` and confirm `git log --oneline origin/main..HEAD` shows only your commits; a PR stacked on
a merged-and-deleted branch silently absorbs the parent's diff.
```

- [ ] **Step 2:** In `AGENTS.md`, replace line 18's spec link sentence with: `Follow the [work and verification protocol](CONTRIBUTING.md#work-and-verification-protocol).`
- [ ] **Step 3:** In `README.md`, replace lines 85-86's decision-record sentence with: `The design history for the current fleet is preserved in git history (tag `pre-cleanup-2026-07-15`); current working docs live in [docs/superpowers/](docs/superpowers/).`
- [ ] **Step 4:** `git rm -q docs/AUDIT-2026-07-12.md docs/RESEARCH.md docs/superpowers/evidence/*.md docs/superpowers/plans/2026-07-13-*.md docs/superpowers/specs/2026-07-13-*.md`
- [ ] **Step 5:** `git grep -n "docs/superpowers/specs/2026-07-13\|docs/superpowers/plans/2026-07-13\|AUDIT-2026-07-12\|docs/RESEARCH" -- ':!docs/superpowers'` → no hits. `py -3 scripts/gate_a.py` → PASS (its link checker proves no dangling markdown links).
- [ ] **Step 6:** Commit: `cleanup: absorb run protocol into CONTRIBUTING, drop migration docs`.

### Task 4 (cut 3): Delete stale evals, repoint the discovery probe

**Files:**
- Delete: all 45 `evals/discovery/*.yaml`; the 13 stale `evals/scenarios/*.yaml` from the evidence ledger (if not already removed by Task 2 Step 6)
- Modify: `evals/discovery_probe.py:24-26,60-61` (layout + docstring), `evals/README.md` (stale counts/names if any)

- [ ] **Step 1:** `git rm -q evals/discovery/*.yaml` and the 13 stale scenario files by name.
- [ ] **Step 2:** In `discovery_probe.py` set `SKILLS_DIR = ROOT / "skills"` and `AGENTS_DIR = ROOT / "generated" / "claude" / "agents"`; update the docstring lines that say `folder in .claude/skills/` / `file in .claude/agents/` to the new paths.
- [ ] **Step 2b:** Re-add the eval-parse step to `gate_a.py` `STEPS` (removed in Task 2), now pointed at the shipped fleet:

```python
    ("Eval suite parses (shipped fleet)",
     ["evals/run_evals.py", "--validate"], None),
```
- [ ] **Step 3:** `grep -n "discovery\|45\|25\|scenario" evals/README.md` — update any now-wrong counts or retired-unit references; leave the rest untouched.
- [ ] **Step 4:** `py -3 evals/run_evals.py --validate` → `EVAL SUITE OK` (or equivalent success output) with no `FLEET_ROOT` set; `py -3 evals/discovery_probe.py --validate` → passes over the empty set (if it errors on zero scenarios, that is a finding to fix minimally by allowing empty).
- [ ] **Step 5:** `py -3 scripts/gate_a.py` → PASS. Commit: `cleanup: drop evals targeting the retired fleet; probe points at shipped layout`.

### Task 5 (cut 4): Drop the duplicate root hooks.json

**Files:**
- Modify: `scripts/generate_fleet.py` (`ROOT_OUTPUTS` line ~213, render map line ~1272), `scripts/test_generate_fleet.py` (any pin on root `hooks.json`), spec evidence note
- Delete: `hooks.json` (root)

- [ ] **Step 1:** `grep -n "hooks.json" scripts/generate_fleet.py scripts/test_generate_fleet.py` — remove the root `Path("hooks.json")` entries (keep `hooks/hooks.json`); update any test pinning the root file.
- [ ] **Step 2:** `git rm -q hooks.json && py -3 scripts/generate_fleet.py --check` → clean (if `--check` demands regeneration, run the generator's write mode first, then `--check`).
- [ ] **Step 3:** Append the manifest evidence correction to the spec's cut-4 section (three plugin manifests verified load-bearing; only root hooks.json removed).
- [ ] **Step 4:** `py -3 scripts/gate_a.py` → PASS. Commit: `cleanup: single hooks manifest; record verified selector evidence in spec`.

### Task 6: Final sweep and review packet

- [ ] **Step 1:** `git grep -nE "legacy/claude-fleet|spikes/|ralph|test_no_regressions|test_phase1|test_phase2|test_root_docs|2026-07-13" -- ':!docs/superpowers/plans/2026-07-15-repo-cleanup.md' ':!docs/superpowers/specs/2026-07-15-repo-cleanup-design.md'` → no hits.
- [ ] **Step 2:** `py -3 scripts/gate_a.py` → PASS. `git ls-files | wc -l` → record the count (expected ≈ 160).
- [ ] **Step 3:** Report the review packet: what changed (file:line), assumptions, verified/unverified, likely-wrong spots (gate step removal breadth; the taint-handoff scenario deletion — top port-later candidate; the discovery-probe repoint).
