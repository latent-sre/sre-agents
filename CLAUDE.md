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
  The agent self-selects its tier by task complexity — but a self-assessment can **under-level** an ambiguous
  or high-blast-radius task, so treat the tier as a **default a human (or `route-request`) can override**, not
  a locked-in self-grade.
- **Gates** (`merge-gate`, `release-gate`, `production-change-gate`) are pass/fail checklists. **The real
  enforcement for prod changes is GitHub branch protection + protected environments** (our own
  `github-actions-ci` pattern: required reviews, required status checks, environment reviewers) — that is
  the security boundary, **provided GitHub's *Allow administrators to bypass protection rules* is disabled**
  (it is ON by default). Don't reach for a local `PreToolUse` denylist to enforce prod safety: it only
  works if the agent cooperates, so it buys a speed-bump while reading like a control. Branch protection
  and protected environments don't depend on the agent cooperating.
- **Subagent dispatch:** putting routing/incident-command in a *subagent* adds a round-trip — the main
  session spins up a coordinator, waits, then acts on its answer — for a decision the main session can make
  inline. That **token/latency cost**, not a capability limit, is why routing and incident-command live as
  **skills** (`route-request`, `incident-severity`) in the main session. (Routing is a *low*-context task,
  so "a subagent loses live context" isn't the reason — the extra hop is; Claude Code now supports nested
  subagent dispatch, so the old "subagents can't spawn subagents" limit no longer applies either.) Be
  honest that this is a **reasoned default, not a measured one** — neither direction has been A/B'd — so
  apply the bar symmetrically: flip it if an A/B shows a coordinator subagent beats the skill.

### No pinned models

Agents declare **no `model:` frontmatter** — they inherit whatever model the session is running. Pick the
model once (`/model`, or your Copilot setting) and the whole fleet follows it. Nothing to keep in sync,
and no policy table to update when the model lineup changes.

**The tradeoff is real, not pure upside:** with no pins the whole fleet moves together, so you *can't* run
cheap agents on a small model while keeping the judgment-heavy ones (`sde-engineer`, `code-reviewer`,
`security-reviewer`, `sre-engineer`, `prompt-engineer`) on a stronger one — you either raise the whole
session (paying for the cheap agents too) or accept those five run at the session tier. We take that for
zero sync/maintenance; pin per-agent (below) when a specific agent's wrong call is expensive enough to
justify the upkeep.

If you later want a specific agent on a specific model, add `model:` to that one agent's frontmatter —
it's a Claude-only field (Copilot ignores it and uses its own selection). Prefer a stronger session model
over per-agent pins: the agents that most reward it (`sde-engineer`, `code-reviewer`, `security-reviewer`,
`sre-engineer`, `prompt-engineer` — open-ended judgment where a wrong call is expensive and hard to catch)
are the ones you'd pin anyway.

## VS Code / Copilot

Both tools read `.claude/` directly, so the fleet works in Copilot as-is — no build or generation step.
Edit agent/skill definitions under `.claude/`; Copilot picks them up natively.
