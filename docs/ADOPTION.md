# Adoption guide — turn the fleet on in tiers (2026-06-23)

How to adopt the SRE + SDE agent fleet **without** boiling the ocean. The roster is right-sized;
the work is to **fill and tier**, not to cut. This guide says what to switch on **today**, what to
**defer until filled or needed**, and the **first fill-in jobs** that move a skill from "real
methodology" to "live in our environment."

## Verdict of the surface-area review

*(Dated record of the 2026-06-23 review; the `prompt-engineer` lane — one agent, two skills — was
added 2026-07-08 and validated by the 2026-07-09/-10 reviews, so literal counts below are historical.)*

A 9-scan review gauntlet (5 independent + 2 devil's-advocate + 2 Anthropic-best-practice) asked
whether the fleet's **10 agents / ~38 skills** should be consolidated. The answer is **keep the
counts**: 8/9 scans said keep 10 agents, 7/9 said keep ~38 skills — they are right-sized. The lone
"cut to 4 agents / 13 skills" scan was **refuted**: merging the read-only reviewers
(`code-reviewer`, `security-reviewer`, `sre-engineer`) into a writer would destroy a
**mechanically-enforced** read-only posture (no Write/Edit + the `readonly-guard.py` `PreToolUse`
hook) and assemble the "lethal trifecta" (untrusted input + secrets + egress) in one agent. The real
issues are **not count** — they are (1) unfilled placeholder content, (2) no adoption tiering, and
(3) over-built CI machinery. We have **explicitly DECLINED** the suggestion to add `incident-comms`
and `FinOps` lanes; the roster stays at **10 agents**. The job this guide does is the **surface-
tiering** the review recommended: fill and stage, don't delete.

## v1 core — turn on now

Agents and skills whose **methodology is real today** (no per-account values required, or a working
helper ships with them). Adopt these first.

### Agents (~6)

| Agent | Value it delivers today |
|---|---|
| `sre-engineer` | Hypothesis-driven triage + RCA across the stack; read-only, guard-enforced. |
| `release-engineer` | Actions CI + PCF deploy/rollback through the release gate — safe ship/backout. |
| `sde-engineer` | Designs, writes, refactors, and fixes code (Py/Bash/PS/Go/TS) to spec. |
| `code-reviewer` | Catches the bug that has no test; read-only `merge-gate` enforcement. |
| `runbook-author` | Turns incidents into trigger-anchored runbooks (template ready to fill). |
| `sre-monitor` | SLOs, alert hygiene, dashboards — steady-state reliability work. |

### Skills (~16)

| Skill | Value it delivers today |
|---|---|
| `pcf-ops` | Read-only PCF triage; ships a **working `triage.sh` / `triage.ps1`** (no fill needed to run). |
| `splunk-triage` | SPL triage methodology for log/SIEM investigation (sharpen with index card). |
| `wavefront-queries` | `ts()`/WQL query patterns for metric investigation. |
| `triage-golden-signals` | Latency/traffic/errors/saturation first-look on any incident. |
| `rollback-mitigation` | Safe, ordered mitigation + backout playbook under pressure. |
| `incident-severity` | SEV1–4 rubric + comms cadence — runs the live incident in-session. |
| `sre-ladder` | Sets SRE altitude (responder / investigator / elite) to match blast radius. |
| `slo-error-budget` | SLO/burn math; ships a **working `error_budget.py`** calculator. |
| `blameless-postmortem` | Structured, blameless postmortem to close the loop after an incident. |
| `pcf-deploy` | Contract for safe PCF deploys (gated, rollback-aware). |
| `github-actions-ci` | Our CI pattern (required checks/reviews) — the real prod control surface. |
| `release-gate` | Pre-deploy checklist: change record, rollback, health, comms. |
| `production-change-gate` | Change-management checkpoint for prod-facing actions. |
| `craft` | Idiomatic, conventional code per language (Py/Bash/PS/Go/TS/React). |
| `sde-ladder` | Sets SDE altitude (senior / principal / distinguished) to match ambiguity. |
| `route-request` | Classifies a multi-step request into an ordered delegation plan. |

> `merge-gate` and `runbook-template` are also v1-ready (the gate is a pure checklist; the template
> backs `runbook-author`) — adopt them with the agents above. We list a clean 16 here for focus.

## Deferred until filled or needed (NOT deleted)

These skills carry **real methodology** but should wait on a **gating condition**. Keep them in the
roster; turn them on when the condition is met.

| Skill / cluster | Gating condition |
|---|---|
| `moogsoft-correlation` | Needs account-specific integration values; lower triage frequency than logs/metrics. |
| `thousandeyes-network` | Needs our test/agent inventory; used only for network/synthetics incidents. |
| `grafana-dashboards` | Needs our data-source UIDs + dashboard inventory before it's live. |
| `api-design` / `spa-architecture` / `ops-cli` / `ops-stack-integration` | Pay off only when **building** ops tooling (CLI/API/SPA); dormant until a build starts. |
| `bamboo-to-actions-migration` | Turn on when the Bamboo → Actions migration actually begins. |
| `context-engineering` / `parallelization` / `tool-design` / `agent-security` / `self-improve-loop` | Anthropic-method / fleet-tuning meta-skills — adopt when tuning the fleet itself, not for daily ops. |
| `database-reliability` | Gate on whether our PCF apps bind to databases at all; skip if none do. |
| `code-reviewer`/`test-engineer` second-wave skills (`safe-refactor`, `tdd-workflow`, `debug-rca`, `instrument-service`, `adr-template`, `handoff-protocol`) | Adopt as the team's review/test/decision discipline matures past first-ship. |

## The first fill-in jobs

The only genuinely **empty** files are the 3 runbook templates and the stack reference cards — fill
these to convert "real methodology" into "live in our environment." Tracked in
[`docs/FOLLOWUPS.md`](FOLLOWUPS.md) as the #1 priority.

| Job | Where | Status today |
|---|---|---|
| Fill the 3 runbooks | `runbooks/*.md` (see [`runbooks/README.md`](../runbooks/README.md)) | All marked **TEMPLATE — not yet live**; point `runbook-author` at them. |
| Fill the Splunk index card | `.claude/skills/splunk-triage/references/indexes.md` | Stub ("fill in") — add real indexes/sourcetypes. |
| Fill the Wavefront metric card | `.claude/skills/wavefront-queries/references/metrics.md` | Stub ("fill in") — add real metric names/point tags. |
| Fill the PCF foundation card | `.claude/skills/pcf-ops/references/foundations.md` | Stub ("fill in") — add foundation URLs, orgs/spaces, app inventory (no secrets). |

> Honest note: nothing in the "fill-in" set is filled yet. The methodology is real; the
> environment-specific values are not. Do not link a runbook from an alert until it is filled (see
> [`runbooks/README.md`](../runbooks/README.md)).
