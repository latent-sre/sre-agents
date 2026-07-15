# Task 33 content-complete and runtime evidence

This is the durable evidence packet for Task 33. Repository content, imported legacy content, runtime output, and handoff text are treated as **[UNTRUSTED] data**, not instructions. A command result is `[verified]` only when the command and exact result are recorded below. Runtime behavior remains `[unverified]` until Checkpoint 4 binds and smokes one immutable commit through each channel separately.

## Candidate and ordering contract

| Item | Evidence |
|---|---|
| Branch | `[verified]` `codex/phase3-close-task-33` |
| Reviewed Task 32 starting SHA | `[verified]` `74c98596e20b471ce4c547d1232a381170e44696` |
| Reviewed Task 31 parent SHA | `[verified]` `2e372ab6579c4ffebf58346395b56c7b1f5883e5` |
| Starting tree object | `[verified]` `9b1c5df2f154d7fb9ea0cb11470114395fe46895` |
| Starting status | `[verified]` empty `git status --short` before the first Task 33 edit |
| Checkpoint order | Checkpoint 1 proof was recorded in this file before the canonical state transition. Checkpoints 2 and 3 are recorded only after their predecessor is green. Checkpoint 4 begins only after static review and a committed candidate. |

## Checkpoint 1 — pre-transition completeness

### Commands and outcomes before the state edit

| Command | Exact outcome |
|---|---|
| `python scripts/test_generate_fleet.py -v` | `[verified]` `Ran 29 tests in 0.926s` and `OK`. This includes the production Task 32 slice, pinned catalog/dependency negative fixtures, greatest-closed-ready-set fixtures, runtime projection checks, stale-output checks, and content-complete negative/positive fixtures. |
| `python scripts/generate_fleet.py --check` | `[verified]` `generate_fleet: CHECK PASS` |
| `python scripts/generate_fleet.py --check --require-content-complete` | `[verified expected red]` exit 1 with exactly `generate_fleet: FAIL: --require-content-complete requires assembly_state content-complete` |
| Exact read-only production report (`load_and_validate`, `render`, and `check` over the reviewed Task 32 tree) | `[verified]` `assembly_state=content-building`; 26 active, 0 planned; ready set `reviewer,sde,sre,observer,scribe`; `check()` returned `[]` |

The red result is the intended fail-closed proof: the complete content exists, but the one-way completion state has not yet been asserted.

### Exact 26-name catalog and bundle inventories

Every row was returned by the validated production manifest before the transition. The generator recursively compares each listed inventory with disk and rejects missing, unexpected, escaping, link-like, reparse, or hardlinked content.

| # | Skill | Directory | References | Assets | Scripts |
|---:|---|---|---|---|---|
| 1 | `stack-profile` | `skills/stack-profile` | — | — | — |
| 2 | `root-cause` | `skills/root-cause` | — | — | — |
| 3 | `runbook` | `skills/runbook` | — | `assets/runbook-template.md` | — |
| 4 | `eng-ladder` | `skills/eng-ladder` | `references/builder.md`, `references/principal.md`, `references/distinguished.md`, `references/responder.md`, `references/investigator.md`, `references/elite.md`, `references/golden-signals.md` | — | — |
| 5 | `craft` | `skills/craft` | `references/python.md`, `references/bash.md`, `references/powershell.md`, `references/go.md`, `references/tdd.md`, `references/safe-refactor.md` | — | — |
| 6 | `backend-craft` | `skills/backend-craft` | `references/stack.md`, `references/consuming-apis.md`, `references/background-work.md`, `references/live-data.md`, `references/persistence.md`, `references/auth.md` | `assets/openapi.starter.yaml` | — |
| 7 | `frontend-craft` | `skills/frontend-craft` | `references/stack.md`, `references/data-views.md`, `references/data-viz.md`, `references/forms.md`, `references/auth.md` | — | — |
| 8 | `ops-tooling` | `skills/ops-tooling` | `references/cli.md` | `assets/cli_skeleton.py` | — |
| 9 | `pcf-ops` | `skills/pcf-ops` | `references/foundations.md` | — | `scripts/triage.sh`, `scripts/triage.ps1` |
| 10 | `pcf-deploy` | `skills/pcf-deploy` | — | `assets/manifest.yml` | — |
| 11 | `database-reliability` | `skills/database-reliability` | — | — | — |
| 12 | `ci-actions` | `skills/ci-actions` | — | `assets/ci.reusable.yml` | — |
| 13 | `merge-gate` | `skills/merge-gate` | — | — | — |
| 14 | `release-gate` | `skills/release-gate` | — | — | — |
| 15 | `production-change-gate` | `skills/production-change-gate` | — | — | — |
| 16 | `incident-command` | `skills/incident-command` | — | — | — |
| 17 | `postmortem` | `skills/postmortem` | — | — | — |
| 18 | `service-onboarding` | `skills/service-onboarding` | — | — | — |
| 19 | `agent-authoring` | `skills/agent-authoring` | `references/artifact.md`, `references/roster.md`, `references/tools.md`, `references/context.md` | — | — |
| 20 | `agent-security` | `skills/agent-security` | — | — | — |
| 21 | `obs-logs` | `skills/obs-logs` | `references/spl.md`, `references/logql.md`, `references/indexes.md` | — | — |
| 22 | `obs-metrics` | `skills/obs-metrics` | `references/wql.md`, `references/promql.md`, `references/metrics.md` | — | — |
| 23 | `obs-traces` | `skills/obs-traces` | `references/traceql.md`, `references/otel-semantics.md` | — | — |
| 24 | `obs-dashboards` | `skills/obs-dashboards` | `references/provisioning.md`, `references/wavefront-legacy.md` | — | — |
| 25 | `obs-alerting` | `skills/obs-alerting` | `references/grafana-alerting.md`, `references/burn-rate.md`, `references/moogsoft.md`, `references/thousandeyes.md` | — | `scripts/error_budget.py` |
| 26 | `obs-pipeline` | `skills/obs-pipeline` | `references/alloy.md`, `references/otel-sdk.md` | — | — |

Proof totals: `[verified]` exactly 26 catalog names, exactly 26 active records, zero planned records, and exactly 26 top-level `skills/` directories.

### Exact five agents, 28 required-skill edges, and runtime identity pairs

Each entry below records `canonical = Copilot = <bare-name>` and `Claude = sre-agents:<name>`. The generator found exactly one marked identity row per required edge, in the same order as the canonical list; missing, extra, duplicate, or wrongly namespaced pairs fail validation.

| Agent | Exact required edges and paired runtime identities |
|---|---|
| `reviewer` (1) | `stack-profile` / `stack-profile` / `sre-agents:stack-profile` |
| `sde` (6) | `stack-profile` / `stack-profile` / `sre-agents:stack-profile`; `root-cause` / `root-cause` / `sre-agents:root-cause`; `eng-ladder` / `eng-ladder` / `sre-agents:eng-ladder`; `craft` / `craft` / `sre-agents:craft`; `backend-craft` / `backend-craft` / `sre-agents:backend-craft`; `frontend-craft` / `frontend-craft` / `sre-agents:frontend-craft` |
| `sre` (11) | `stack-profile` / `stack-profile` / `sre-agents:stack-profile`; `root-cause` / `root-cause` / `sre-agents:root-cause`; `eng-ladder` / `eng-ladder` / `sre-agents:eng-ladder`; `pcf-ops` / `pcf-ops` / `sre-agents:pcf-ops`; `database-reliability` / `database-reliability` / `sre-agents:database-reliability`; `incident-command` / `incident-command` / `sre-agents:incident-command`; `obs-logs` / `obs-logs` / `sre-agents:obs-logs`; `obs-metrics` / `obs-metrics` / `sre-agents:obs-metrics`; `obs-traces` / `obs-traces` / `sre-agents:obs-traces`; `obs-dashboards` / `obs-dashboards` / `sre-agents:obs-dashboards`; `obs-alerting` / `obs-alerting` / `sre-agents:obs-alerting` |
| `observer` (7) | `stack-profile` / `stack-profile` / `sre-agents:stack-profile`; `obs-logs` / `obs-logs` / `sre-agents:obs-logs`; `obs-metrics` / `obs-metrics` / `sre-agents:obs-metrics`; `obs-traces` / `obs-traces` / `sre-agents:obs-traces`; `obs-dashboards` / `obs-dashboards` / `sre-agents:obs-dashboards`; `obs-alerting` / `obs-alerting` / `sre-agents:obs-alerting`; `obs-pipeline` / `obs-pipeline` / `sre-agents:obs-pipeline` |
| `scribe` (3) | `stack-profile` / `stack-profile` / `sre-agents:stack-profile`; `runbook` / `runbook` / `sre-agents:runbook`; `postmortem` / `postmortem` / `sre-agents:postmortem` |

Proof totals: `[verified]` exactly five canonical agents and exactly `1 + 6 + 11 + 7 + 3 = 28` required-skill edges, all resolving to active catalog records. The derived greatest closed ready set is exactly `reviewer`, `sde`, `sre`, `observer`, `scribe`.

### Exact skill-dependency rows

| Owner | Exact resolved targets |
|---|---|
| `ops-tooling` | `eng-ladder` |
| `service-onboarding` | `production-change-gate`, `obs-pipeline`, `obs-dashboards`, `obs-alerting`, `ci-actions`, `runbook` |

Proof totals: `[verified]` exactly two rows and seven resolved edges. The same canonical/Copilot/Claude identity equality is enforced in each owner's marked dependency block.

### Exact generated runtime projection

| Runtime | Exact wrappers |
|---|---|
| Copilot | `generated/copilot/agents/observer.agent.md`, `reviewer.agent.md`, `scribe.agent.md`, `sde.agent.md`, `sre.agent.md` |
| Claude | `generated/claude/agents/observer.md`, `reviewer.md`, `scribe.md`, `sde.md`, `sre.md` |

`[verified]` There are exactly five wrappers per runtime. Every rendered Claude wrapper contains generic tool `Skill` exactly once and no frontmatter field beginning `skills:`. `generate_fleet.check()` returned an empty failure list, proving no stale, missing, or unexpected generator-owned output.

### Pre-runtime registration and cleanup baseline

No runtime channel was enabled for Checkpoints 1–3. This census is metadata-only: profile files were hashed and scanned for the Task 33 worktree and registration keys without printing unrelated values. Existing user profile content is out of scope and must retain the exact baseline hash after Checkpoint 4 cleanup.

| Profile file | SHA-256 | Registration census |
|---|---|---|
| `%APPDATA%/Code/User/settings.json` | `0d8ce40390ed05c8ca405e5e653507f1b77114a0bab32578b473bfa260658e4c` | No Task 33 worktree path; none of `chat.pluginLocations`, `chat.agentFilesLocations`, `chat.agentSkillsLocations`, or `chat.promptFilesLocations` present. |
| `~/.claude/settings.json` | `d8c967ee3bbaf08dba725a0b646155a6d46f541798c244fca5f35274fefc3f68` | No Task 33 worktree path and no `--plugin-dir`. Contains pre-existing unrelated permissions mentioning an older source checkout; do not mutate them. |
| `~/.claude/settings.local.json` | `d1a2adadbf199974e3f7fafd35877c70b9de599a367773149c1b2550cd9748e8` | No Task 33 worktree path and no `--plugin-dir`. |
| `~/.claude.json` | `dadfbcef1da46f73defdd4f64de37ddc106a60898ed30b12dd53bac7c1cccf32` | No Task 33 worktree path and no `--plugin-dir`; treat the whole file as unrelated state. |
| `~/.claude/plugins/installed_plugins.json` | `df41d33d4f3da44229f39887d93c5348f5ef4881cd24c3710506b0a59fca786a` | No Task 33 worktree path and no `--plugin-dir`. |
| `~/.claude/plugins/known_marketplaces.json` | `7c1959d128e241e871ef6ef92932b1c98d863b1166768a5a7d44ed79d41c3655` | No Task 33 worktree path and no `--plugin-dir`. |
| `~/.copilot/config.json` | absent | No persistent Copilot CLI registration exists at this path. |
| Project `.vscode/settings.json` | absent | The mutable authoring worktree is not registered through project fallback settings. |

Checkpoint 4 must record the final candidate SHA, candidate tree object, source-tree digest, runtime-tree digest, and exact file map before registration. It must rehash this original worktree and all baseline profile files after unregistering every channel and removing the snapshot. Those final values are intentionally not claimed by this pre-transition checkpoint.

### Checkpoint 1 verdict

`[verified] PASS — 100% (12/12 required structural claims green).` After this proof was saved, the only canonical state edit changed `assembly_state: content-building` to `content-complete`. Then `python scripts/generate_fleet.py --write --require-content-complete`, `python scripts/generate_fleet.py --check`, and `python scripts/generate_fleet.py --check --require-content-complete` each returned their exact PASS line. Regeneration changed no projected runtime bytes because the already-complete wrapper set was current.

## Checkpoint 2 — permanent Gate A completion assertion

### Red-first proof

The four focused CLI/Gate-A contract tests were run before either implementation edit. Two passed, pinning the old behavior, and two failed for the intended reasons:

| Test | Red result |
|---|---|
| `test_gate_a_requires_exact_content_complete_step_once` | `[verified expected red]` `AssertionError: 1 != 0` because the exact tuple was absent. |
| `test_cli_completion_assertion_standalone_performs_a_check` | `[verified expected red]` `standalone --require-content-complete exited with status 2 instead of checking the fleet`; argparse reported that `--write` or `--check` was required. |
| `test_cli_requires_a_mode_when_no_completion_assertion_is_requested` | `[verified]` passed before implementation, proving no-argument exit status 2 was pinned. |
| `test_cli_preserves_explicit_write_and_check_modes` | `[verified]` passed before implementation, proving both explicit dispatch paths and their `require_content_complete=False` calls were pinned. |

### Minimal implementation and green proof

`scripts/gate_a.py` now contains exactly one tuple `("Fleet content complete", ["scripts/generate_fleet.py", "--require-content-complete"], None)`. `scripts/generate_fleet.py` treats the standalone assertion as check mode while preserving the no-argument parser error and mutually exclusive explicit write/check modes.

`[verified]` The same four focused tests then ran 4/4 `OK`; the standalone production command returned `generate_fleet: CHECK PASS`; the full generator suite ran 33/33 `OK`; ordinary `--check` and standalone `--require-content-complete` both passed.

### Checkpoint 2 verdict

`[verified] PASS — 100% (4/4 focused behavior contracts green, exact Gate A tuple count = 1).`

## Checkpoint 3 — disposition-ledger and filesystem closure

The fail-closed test was written and run before these tables existed. Its expected red result was six subtest failures, each naming one missing evidence heading. The test reads the two spec appendices directly, compares exact ordered first-column identity against every evidence row, rejects omissions, duplicates, blank proofs, or placeholder dispositions, and then pins the filesystem projections.

### Ledger table: skills

| Spec row | Audit status | Exact realization |
|---|---|---|
| adr-template | `[verified realized]` | Canonical command `canonical/commands/adr.md`; exact generated native Copilot, fallback prompt, and Claude command views exist; no separate ADR asset ships. |
| agent-authoring | `[verified realized]` | Active `skills/agent-authoring/` with `artifact.md`, `roster.md`, `tools.md`, and `context.md`. |
| agent-security | `[verified realized]` | Active rewritten `skills/agent-security/SKILL.md`; structural runtime claims remain explicitly deferred to Task 38. |
| api-design | `[verified realized]` | Content and OpenAPI asset live under `skills/backend-craft/references/stack.md` and `skills/backend-craft/assets/openapi.starter.yaml`. |
| bamboo-to-actions-migration | `[verified realized]` | Default deletion realized: no canonical Bamboo command and no generated Bamboo view exist; the optional Task 20 branch was not activated. |
| blameless-postmortem | `[verified realized]` | Renamed active skill `skills/postmortem/SKILL.md`. |
| context-engineering | `[verified realized]` | Demoted to `skills/agent-authoring/references/context.md`. |
| craft | `[verified realized]` | Active `skills/craft/`; language references plus `tdd.md` and `safe-refactor.md` are inventoried. |
| database-reliability | `[verified realized]` | Active `skills/database-reliability/SKILL.md`. |
| debug-rca | `[verified realized]` | Replaced by active `skills/root-cause/SKILL.md`. |
| github-actions-ci | `[verified realized]` | Renamed active `skills/ci-actions/`; fixed reusable workflow asset is `assets/ci.reusable.yml`. |
| grafana-dashboards | `[verified realized]` | Merged into active `skills/obs-dashboards/` with `references/provisioning.md` and `references/wavefront-legacy.md`. |
| handoff-protocol | `[verified realized]` | Dissolved into canonical `handoffs` records plus packet, SHA-pinning, and taint sections in the five canonical agent bodies. |
| incident-severity | `[verified realized]` | Renamed active `skills/incident-command/SKILL.md`. |
| instrument-service | `[verified realized]` | OTel content lives under active `skills/obs-pipeline/references/otel-sdk.md`; pipeline body and Alloy reference are inventoried. |
| merge-gate | `[verified realized]` | Active `skills/merge-gate/SKILL.md` with the P0–P3 verdict rubric. |
| moogsoft-correlation | `[verified realized]` | Demoted to `skills/obs-alerting/references/moogsoft.md`. |
| ops-cli | `[verified realized]` | Demoted to `skills/ops-tooling/references/cli.md`; skeleton asset moved with it. |
| ops-stack-integration | `[verified realized]` | Content lives under `skills/backend-craft/references/stack.md` and `references/consuming-apis.md`. |
| pcf-deploy | `[verified realized]` | Active `skills/pcf-deploy/` with `assets/manifest.yml` and manual-only frontmatter. |
| pcf-ops | `[verified realized]` | Active `skills/pcf-ops/` with foundations reference and both human-run triage scripts. |
| production-change-gate | `[verified realized]` | Active `skills/production-change-gate/SKILL.md`. |
| release-gate | `[verified realized]` | Active `skills/release-gate/SKILL.md`. |
| rollback-mitigation | `[verified realized]` | Reversible-action decision table merged into `skills/incident-command/SKILL.md` under `Choose the mitigation`. |
| route-request | `[verified realized]` | Dissolved into canonical agent delegation and handoff metadata; roster method lives under agent-authoring. |
| runbook-template | `[verified realized]` | Merged into active `skills/runbook/`; template is `assets/runbook-template.md`. |
| safe-refactor | `[verified realized]` | Demoted to `skills/craft/references/safe-refactor.md`. |
| sde-ladder | `[verified realized]` | Merged into active `skills/eng-ladder/` with builder, principal, and distinguished references. |
| self-improve-loop | `[verified realized]` | Deleted from the 26-name catalog and runtime-visible skill tree; the `Move failures left` doctrine is carried by `canonical/agents/sde.md`. |
| slo-error-budget | `[verified realized]` | Merged into `skills/obs-alerting/references/burn-rate.md`; fixed script is `scripts/error_budget.py`. |
| spa-architecture | `[verified realized]` | Demoted to the active `skills/frontend-craft/` reference set. |
| splunk-triage | `[verified realized]` | SPL content moved to `skills/obs-logs/references/spl.md`; index guidance is separately inventoried. |
| sre-ladder | `[verified realized]` | Merged into `skills/eng-ladder/` SRE references: responder, investigator, elite, and golden signals. |
| tdd-workflow | `[verified realized]` | Tests-first discipline is in `canonical/agents/sde.md`; process reference is `skills/craft/references/tdd.md`. |
| thousandeyes-network | `[verified realized]` | Demoted to `skills/obs-alerting/references/thousandeyes.md`. |
| tool-design | `[verified realized]` | Demoted to `skills/agent-authoring/references/tools.md`. |
| wavefront-queries | `[verified realized]` | WQL content moved to `skills/obs-metrics/references/wql.md`; metric guidance is separately inventoried. |

### Ledger table: agents

| Spec row | Audit status | Exact realization |
|---|---|---|
| sde-engineer | `[verified realized]` | Replaced by canonical `sde`; domain methods are carried by required skills and `canonical/agents/sde.md`. |
| code-reviewer | `[verified realized]` | Replaced by canonical read-only `reviewer`. |
| security-reviewer | `[verified realized]` | Threat/security lens merged into `canonical/agents/reviewer.md`; canonical reviewer holds read/search only. |
| test-engineer | `[verified realized]` | Agent deleted; tests-first and untrusted-code refusal are explicit in `canonical/agents/sde.md` and craft references. |
| sre-engineer | `[verified realized]` | Replaced by canonical `sre`; five-agent readiness includes it. |
| sre-monitor | `[verified realized]` | Replaced by canonical `observer`. |
| runbook-author | `[verified realized]` | Replaced by canonical `scribe`; runtime projection contains no execute alias. |
| researcher | `[verified realized]` | Agent deleted; scoped native web capabilities remain only on agents that need them, with no researcher wrapper. |
| prompt-engineer | `[verified realized]` | Agent deleted; method carried by active `skills/agent-authoring/`. |

### Ledger table: evals

| Spec row | Audit status | Exact realization |
|---|---|---|
| `evals/discovery/*.yaml` (**45 cases**) | `[sourced scheduled]` | Current 45-case legacy corpus is frozen; Task 34 deletes and rewrites it as 24 discovery plus two explicit invocation cases. |
| `evals/scenarios/*.yaml` (**25 cases**) | `[sourced scheduled]` | Current 25-case corpus is frozen; Task 34 rewrites surviving-unit cases and records every deleted-unit disposition. |
| `evals/clean_room.py` | `[verified realized]` | File survives at `evals/clean_room.py` and its test remains in Gate A. |
| `evals/run_evals.py`, `discovery_probe.py`, `graders.py` | `[sourced scheduled]` | Files survive now: `run_evals.py` consumes the Task 34 corpus, Task 34 adapts `discovery_probe.py`, and Task 35 extends `graders.py` with routing and fan-out grading. |
| `evals/test_graders.py`, `test_discovery_probe.py` | `[verified realized]` | Both test files survive and are current Gate A steps; Task 35 extends grader coverage. |
| `evals/README.md` | `[sourced scheduled]` | Task 35 rewrites the operator guide while preserving manual-only and runtime-separated doctrine. |

### Ledger table: scripts, CI, hooks

| Spec row | Audit status | Exact realization |
|---|---|---|
| `scripts/readonly-guard.py` + `readonly-guard-hook.sh` | `[sourced scheduled]` | Frozen old machinery remains for comparison; Task 38 determines the replacement boundary and Task 40 deletes both old files. |
| `scripts/test_readonly_guard.py` | `[sourced scheduled]` | Current regression corpus remains green; Task 38 replaces its control and Task 40 deletes the old suite. |
| `scripts/validate_fleet.py` | `[sourced scheduled]` | Task 37 rewrites it as validator v2 over canonical and both generated projections. |
| `scripts/ralph-loop.sh` | `[sourced scheduled]` | Claude-specific loop remains only until Task 40 deletes it. |
| `.github/workflows/validate.yml` | `[sourced scheduled]` | Existing workflow survives; Task 40 extends it with the protected validation harness. |
| `requirements-dev.txt` | `[verified realized]` | File survives; Gate A invokes substeps under `sys.executable` and does not hardcode `python3`. |
| `.mcp.json` | `[verified realized]` | Task 30 adoption is present as the optional read-only Grafana MCP configuration. |

### Ledger table: root docs

| Spec row | Audit status | Exact realization |
|---|---|---|
| `AGENTS.md` | `[sourced scheduled]` | Legacy copy is preserved under `legacy/claude-fleet/AGENTS.md`; Task 46 performs the absorption audit and short project-only rewrite. |
| `CLAUDE.md` | `[sourced scheduled]` | Legacy copy is preserved under `legacy/claude-fleet/CLAUDE.md`; Task 46 reduces the live file to the development entrypoint. |
| `README.md` | `[sourced scheduled]` | Legacy copy is preserved; Task 45 rewrites install, ownership, mode, and generated inventory guidance. |
| `docs/RESEARCH.md` | `[sourced scheduled]` | File survives; Task 45 retargets it to the required VS Code, Copilot, and control-plane sources. |
| `docs/AUDIT-2026-07-12.md` | `[verified realized]` | Audit evidence remains at the exact path. |
| `docs/superpowers/{specs,plans}/` | `[verified realized]` | Both decision-history directories and this Task 33 source plan/spec survive. |
| `LICENSE` | `[verified realized]` | Root MIT license survives unchanged. |

### Ledger table: in-skill assets and references

| Spec row | Audit status | Exact realization |
|---|---|---|
| `ops-cli/assets/cli_skeleton.py` | `[verified realized]` | Moved to `skills/ops-tooling/assets/cli_skeleton.py` and included in canonical inventory. |
| `api-design/assets/openapi.starter.yaml` | `[verified realized]` | Moved to `skills/backend-craft/assets/openapi.starter.yaml` and included in canonical inventory. |
| `pcf-deploy/assets/*`, `github-actions-ci/assets/*` | `[verified realized]` | Survive as `skills/pcf-deploy/assets/manifest.yml` and `skills/ci-actions/assets/ci.reusable.yml`. |
| `runbook-template/assets/*` | `[verified realized]` | Moved to `skills/runbook/assets/runbook-template.md`. |
| `adr-template/assets/adr-template.md` | `[verified realized]` | Content embedded in `canonical/commands/adr.md`; only its three generated runtime views ship. |
| `route-request/references/fan-out.md` | `[verified realized]` | File deleted from runtime content; cost and right-sizing model live in `skills/agent-authoring/references/roster.md`, including the sourced 15× estimate. |
| `sre-ladder/references/golden-signals.md` | `[verified realized]` | Moved to `skills/eng-ladder/references/golden-signals.md`. |
| `craft/references/{python,bash,powershell,go,typescript,react}.md` | `[verified realized]` | Python, Bash, PowerShell, and Go survive under craft; TypeScript and React are absent because frontend-craft owns that layer. |
| `pcf-ops/{references,scripts}/*`, `splunk-triage/references/*`, `wavefront-queries/references/*`, `grafana-dashboards/references/*`, `moogsoft-correlation/references/*`, `thousandeyes-network/references/*` | `[verified realized]` | Exact current inventories are under `pcf-ops`, `obs-logs`, `obs-metrics`, `obs-dashboards`, and `obs-alerting`, all enumerated in Checkpoint 1. |
| `slo-error-budget/scripts/error_budget.py` | `[verified realized]` | Moved with fixes to `skills/obs-alerting/scripts/error_budget.py`. |
| `agent-authoring/references/*`, `sde-ladder/references/*`, `route-request/references/*` (others) | `[verified realized]` | Folded into the four agent-authoring references and seven eng-ladder references listed in the exact inventory. |

### Filesystem and projection closure

| Required count | Exact result |
|---|---|
| Skill directories | `[verified]` 26, with names exactly equal to the pinned catalog. |
| Canonical agent bodies | `[verified]` 5: `reviewer`, `sde`, `sre`, `observer`, `scribe`. |
| Copilot wrappers | `[verified]` 5 exact `*.agent.md` names for the canonical roster. |
| Claude wrappers | `[verified]` 5 exact `*.md` names for the canonical roster. |
| Manual-only skills | `[verified]` exactly `pcf-deploy` and `service-onboarding`; no third `disable-model-invocation: true` frontmatter exists. |

### Checkpoint 3 verdict

`[verified] PASS — 100% (77/77 ledger rows accounted: 37 skills + 9 agents + 6 eval rows + 7 scripts/CI/hooks rows + 7 root-document rows + 11 asset/reference rows).` The red-first run failed all six missing-table subtests as intended. After the row audit was recorded, `test_disposition_ledger_rows_and_projection_counts_are_closed` ran 1/1 `OK`. Security review then required identities and dispositions to be independent of both mutable Markdown sources: the contract now pins all 77 ordered identities, the exact realized/scheduled status of each row, and all 13 scheduled rows' Task 34/35/37/38/40/45/46 destinations. Its coordinated same-key substitution negative test passes only when that attack is rejected. The final generator suite ran 35/35 `OK`; `python scripts/generate_fleet.py --check` and standalone `--require-content-complete` each returned `generate_fleet: CHECK PASS`.

The first managed-sandbox Gate A run reached 12/16 green; the four failures were exclusively `PermissionError: [WinError 5]` while legacy tests created or cleaned child directories under `%LOCALAPPDATA%/Temp`. `[verified]` After the review fixes, the exact same `python scripts/gate_a.py` command was rerun with permission to use those temporary directories and passed `Gate A: PASS -- 16/16 structural steps green.` Expanded results included 29 Phase-2 tests with one existing environment skip, 11/11 validator tests, 9/9 Phase-1 tests, 60 format-spike tests with one Windows symlink-privilege skip, 35/35 generated-fleet tests, 505/505 read-only-guard cases, 56/56 grader checks, 24/24 discovery-probe checks, and 24/24 clean-room checks. The two skips are platform-capability skips, not Task 33 failures.

## Checkpoint 4 — immutable runtime smoke

### Superseded candidate and native selector finding

The first candidate was committed before any runtime registration:

| Binding | Exact value |
|---|---|
| Source candidate SHA | `[verified]` `a8dcd1d8f70e6e533a3642fcc17614e711b4922a` |
| Source/snapshot tree object | `[verified]` `8fec0082f52e373a307f22f7404908dc4cef714a` |
| Immutable snapshot full-tree digest (320 files) | `[unverified transcript value]` `7f54c927643dd8357bdbe16b9e75d76ed539b3bdc5267489b43951e3525f0f12`; the failed row did not retain its digest-serialization helper, so this value receives no credit and is not reused. |
| Runtime-tree digest (99 files) | `[unverified transcript value]` `e8e787d7f3c3af68809fe620cd8d5562bf6fea642f8d0d9dc90ab83fe50be7f5`; the failed row did not retain its exact file-selection/serialization helper, so this value receives no credit and is not reused. |

`[verified]` The durable candidate commit still resolves to the recorded SHA/tree. `[unverified transcript observation]` The removed disposable diagnostic packet reported that native VS Code, enabled alone through `chat.pluginLocations`, selected `generated/claude/agents/reviewer.md` and watched `.claude-plugin/plugin.json`; because that packet was not retained and hash-bound, it is a hypothesis only. The independently reproducible installed-loader inspection below confirms the selection defect mechanically. The probe produced no accepted skill/delegation/execution tool evidence, so **the entire attempt receives 0% runtime credit**. No positive runtime-smoke claim is carried into the replacement candidate; only the negative selector defect is retained as a repair input.

The reproducible part of the sanitized failure/cleanup audit uses the literal commands below. It intentionally omits authentication values and unrelated profile contents. Transcript-only rows are explicitly downgraded above instead of being presented as verified evidence:

| Command/check | Exact sanitized outcome |
|---|---|
| `git rev-parse a8dcd1d8f70e6e533a3642fcc17614e711b4922a` and `git rev-parse 'a8dcd1d8f70e6e533a3642fcc17614e711b4922a^{tree}'` | `a8dcd1d8f70e6e533a3642fcc17614e711b4922a`; `8fec0082f52e373a307f22f7404908dc4cef714a` |
| `$p='C:\Users\hawkins\AppData\Local\Programs\Microsoft VS Code\5264f2156c\resources\app\out\vs\workbench\workbench.desktop.main.js'; (Get-Item -LiteralPath $p).Length; (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower()` | `17809503`; `cd2ec82418998e6141a1f7cdfc957265e3bc52dd772998c8dc245229ab21b87b` |
| `$p='C:\Users\hawkins\AppData\Local\Programs\Microsoft VS Code\5264f2156c\resources\app\out\vs\workbench\workbench.desktop.main.js'; $t=[IO.File]::ReadAllText($p); $needle='.plugin/plugin.json'; $offset=0; $found=@(); while(($i=$t.IndexOf($needle,$offset,[StringComparison]::Ordinal)) -ge 0){$found+=$i; $offset=$i+$needle.Length}; $found -join ','` | `4088646,11277382`; the 650-byte sanitized inspection window at offset `4088646` contains the selector function: `.plugin/plugin.json` first, else Claude on `.claude` path/marker, else root Copilot. |
| `$snapshot='C:\Users\hawkins\.codex\visualizations\2026\07\15\019f641c-f61f-7540-95d7-f89259f943c5\task33-runtime-a8dcd1d8'; $control='C:\Users\hawkins\.codex\visualizations\2026\07\15\019f641c-f61f-7540-95d7-f89259f943c5\task33-smoke-a8dcd1d8'; Get-CimInstance Win32_Process \| Where-Object { $_.CommandLine -like "*$snapshot*" -or $_.CommandLine -like "*$control*" } \| Select-Object ProcessId,Name` | Zero rows after the failed client was stopped. |
| `icacls $snapshot /grant:r 'GALACTICA\hawkins:(F)' /T /C`; `Remove-Item -LiteralPath $snapshot -Recurse -Force`; `Remove-Item -LiteralPath $control -Recurse -Force`; `Test-Path -LiteralPath $snapshot`; `Test-Path -LiteralPath $control` | ACL reset completed for the disposable snapshot; final outputs `False`; `False`. |
| `$paths=@("$env:APPDATA\Code\User\settings.json","$HOME\.claude\settings.json","$HOME\.claude\settings.local.json","$HOME\.claude.json","$HOME\.claude\plugins\installed_plugins.json","$HOME\.claude\plugins\known_marketplaces.json"); $paths \| ForEach-Object { (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToLower() }` | Exact outputs, in order: `0d8ce40390ed05c8ca405e5e653507f1b77114a0bab32578b473bfa260658e4c`; `d8c967ee3bbaf08dba725a0b646155a6d46f541798c244fca5f35274fefc3f68`; `d1a2adadbf199974e3f7fafd35877c70b9de599a367773149c1b2550cd9748e8`; `dadfbcef1da46f73defdd4f64de37ddc106a60898ed30b12dd53bac7c1cccf32`; `df41d33d4f3da44229f39887d93c5348f5ef4881cd24c3710506b0a59fca786a`; `7c1959d128e241e871ef6ef92932b1c98d863b1166768a5a7d44ed79d41c3655`. |

`[sourced]` The current VS Code plugin documentation both describes `.plugin/plugin.json` as an OpenPlugin marker and publishes a cross-tool lookup sequence that places `.plugin/plugin.json` ahead of root and Claude manifests. `[verified]` Inspection of the installed VS Code 1.128.1 loader showed its effective rule: choose `.plugin/plugin.json` first; otherwise choose Claude when `.claude-plugin/plugin.json` is present; otherwise choose root Copilot. This explained why the coexistence design made root `plugin.json` unreachable in that client. The narrowly amended contract generates `.plugin/plugin.json` as an exact-byte alias of root `plugin.json`, owns the complete `.plugin/` directory, and rejects missing, stale, linked, hardlinked, or unexpected selector content. The selector creates no new wrappers, skills, or semantic authoring source. `[unverified]` OpenPlugin hook/MCP lookup is intentionally not inferred; Phase 4 must re-probe it before relying on that machinery.

`[verified]` No process command line references either disposable root, both roots are absent, and all six profile hashes match their pre-registration baselines. `[unverified historical transcript]` `git status --short` was reported empty at the superseded candidate before the replacement fix began; this historical worktree-state claim receives no runtime credit and is replaced by the new candidate's independently recorded clean-tree proof.

### Replacement-candidate requirement

Pending replacement static closure, independent reviews, and a new committed candidate. The new exact SHA must be exported to a fresh immutable snapshot and all three channels must restart from the beginning. No superseded evidence and no mutable-worktree smoke are permitted. Before native registration the evidence packet must record a sanitized environment with no `GRAFANA_*`, an unresolvable `uvx`, MCP access `none`, MCP autostart `never`, discovery/gallery/apps off, zero profile/workspace/CLI MCP registrations, and before/during/after Diagnostics plus process censuses with no MCP, hook, or `uvx` event/process. Failure of any containment assertion stops the channel before registration.
