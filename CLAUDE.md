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
  (it is ON by default). Don't reach for a local `PreToolUse` denylist to enforce prod safety: it only
  works if the agent cooperates, so it buys a speed-bump while reading like a control. Branch protection
  and protected environments don't depend on the agent cooperating.
- **Subagent dispatch:** an orchestration *agent* would double-pay the routing round-trip and discard the
  main session's live context that the work needs — pure overhead. Routing and incident-command therefore
  live as **skills** (`route-request`, `incident-severity`) that run in the main session, not as agents.
  Claude Code now supports nested subagent dispatch, so the old "subagents can't spawn subagents" capability
  limit no longer applies, but that cost argument still holds; re-promoting an orchestration agent should be
  gated on an A/B that beats the skill.

### No pinned models

Agents declare **no `model:` frontmatter** — they inherit whatever model the session is running. Pick the
model once (`/model`, or your Copilot setting) and the whole fleet follows it. Nothing to keep in sync,
and no policy table to update when the model lineup changes.

If you later want a specific agent on a specific model, add `model:` to that one agent's frontmatter —
it's a Claude-only field (Copilot ignores it and uses its own selection). Prefer a stronger session model
over per-agent pins: the agents that most reward it (`sde-engineer`, `code-reviewer`, `security-reviewer`,
`sre-engineer`, `prompt-engineer` — open-ended judgment where a wrong call is expensive and hard to catch)
are the ones you'd pin anyway.

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is — no build or generation step.
Edit agent/skill definitions under `.claude/`; Copilot picks them up natively.
