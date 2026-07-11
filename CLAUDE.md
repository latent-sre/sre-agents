# CLAUDE.md — Claude Code entrypoint

This repo's full guide lives in [AGENTS.md](AGENTS.md) (the cross-tool source of truth). Read it.

@AGENTS.md

## Claude Code specifics

- **Agents** (`.claude/agents/`) auto-route by their `description`. For multi-step/ambiguous work, invoke
  `/route-request` first; or summon an agent explicitly — *"use the sre-engineer to triage this"*.
- **Skills** (`.claude/skills/`) auto-load when a task matches their `description`; you can also invoke
  one directly: `/pcf-ops`, `/release-gate`, `/merge-gate`, etc. The **ladder skills** set altitude —
  `sde-engineer` and `sre-engineer` pick `sde-ladder`/`sre-ladder` by task complexity.
- **Seniority/experience = skills, not agents.** One `sde-engineer` + one `sre-engineer`; the
  Senior/Principal/Distinguished and Responder/Investigator/Elite levels are the `sde-ladder`/`sre-ladder` skills.
- **Gates** (`merge-gate`, `release-gate`, `production-change-gate`) are pass/fail checklists. **The real
  enforcement for prod changes is GitHub branch protection + protected environments** (our own
  `github-actions-ci` pattern: required reviews, required status checks, environment reviewers) — that is
  the security boundary, **provided GitHub's *Allow administrators to bypass protection rules* is disabled**
  (it is ON by default). As an *auditable speed-bump* in Claude Code, the `production-change-guard.py`
  `PreToolUse` hook ([scripts/production-change-guard.py](scripts/production-change-guard.py)) blocks
  state-changing `cf` commands unless the gate sentinel (`PCF_GATE_CLEARED=1` or a `.gate-cleared` file)
  is set — wire it onto whatever agent runs `cf`. Treat that hook as a checklist-forcing convenience for a
  cooperative agent, **not** a security control — a determined path around a local denylist exists; branch
  protection + environments do not depend on the agent cooperating.
- **Subagent dispatch:** an orchestration *agent* would double-pay the routing round-trip and discard the
  main session's live context that the work needs — pure overhead. Routing and incident-command therefore
  live as **skills** (`route-request`, `incident-severity`) that run in the main session, not as agents.
  Claude Code now supports nested subagent dispatch, so the old "subagents can't spawn subagents" capability
  limit no longer applies, but that cost argument still holds; re-promoting an orchestration agent should be
  gated on an A/B that beats the skill.

### Model policy (the `model:` frontmatter)

Model choice follows the **nature of the work, not the seniority of the role** (seniority is the ladder
skills). The rule: **`opus` for open-ended reasoning under ambiguity where a wrong call is expensive and
hard to catch; `sonnet` for structured work that follows a defined method, checklist, or template.**

- **`opus` (5):** `sde-engineer` (design/write code), `code-reviewer` (find the bug that has no test),
  `security-reviewer` (adversarial threat reasoning), `sre-engineer` (hypothesis-driven RCA),
  `prompt-engineer` (diagnosing ambiguous prompt/agent failures — a wrong call ships a subtly broken
  artifact the whole fleet runs on). These hinge on getting an open-ended judgment *right*.
- **`sonnet` (4):** `researcher`, `runbook-author`, `sre-monitor`, `test-engineer`.
  Each runs a **defined procedure** — a source-and-cite loop, a runbook template, alert/SLO config, or a
  test plan. (Routing and the incident lifecycle are the `sonnet`-class skills `route-request` /
  `incident-severity`, run in the main session.)
- **Tuning:** `model:` is Claude-specific frontmatter (Copilot ignores it and uses its own selection).
  Change it per agent as your team sees fit — but it is an **enforced** policy, not a free-for-all:
  `scripts/validate_fleet.py` is the source of truth and **fails validation** on any agent whose `model:`
  doesn't match its table, so edit the table in the same commit.

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is — no build or generation step.
Edit agent/skill definitions under `.claude/`; Copilot picks them up natively.
