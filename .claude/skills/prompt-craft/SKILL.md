---
name: prompt-craft
description: >-
  Author and optimize a single LLM-facing artifact — a system prompt, an agent definition, a
  SKILL.md, a tool description, or a grader prompt. Use when creating one, or when one misbehaves:
  a skill that never triggers or fires too often, an agent that ignores an instruction, output with
  the wrong shape. Covers the eval-first loop, trigger-only descriptions, and matching the fix's
  form to the failure. For roster/orchestration-level design use `agent-architecture`; for tools an
  agent calls use `tool-design`.
---

# Prompt craft

A prompt is a spec. Edit it like code: reproduce the failure, make the minimal fix, verify, and
know which *form* of fix the failure calls for. *[sourced: Anthropic prompt/skill authoring
guidance; obra/superpowers `writing-skills` (empirical skill-testing)]*

## The loop (eval-first)

1. **Success criteria before edits** — what does correct output look like, measurably? Write 3+
   test cases: happy path, edge case, failure mode.
2. **Baseline** — run the current artifact and capture the actual failure. No edit without an
   observed failure (or explicit new-behavior target) pinned to it.
3. **Minimal change** — fix that failure only; don't rewrite everything you'd phrase differently.
4. **Retest fresh** — fresh-context runs, multiple reps; one pass proves nothing and **variance is
   a metric**. For fleet artifacts, a subagent given a realistic task tells you whether the thing
   triggers *and* complies.

## Descriptions: trigger, not workflow

The frontmatter `description` states **when to invoke** — in the words a user actually says — and
never summarizes the process. A description that summarizes the workflow becomes a shortcut: the
agent executes the summary and skips the body. Diagnosis table:

| Symptom | Cause | Fix |
|---|---|---|
| Never triggers | Description doesn't match real user phrasing | Add the literal phrases ("review this", "why is X slow") |
| Fires too often | Topic-shaped ("helps with docs") | Make it action-shaped ("extracts form fields from PDFs") |
| Triggers, then does the wrong steps | Description summarizes the workflow | Strip the summary; leave only trigger conditions |

## Match the form to the failure

The form that fixes one failure type measurably backfires on another:

| Observed failure | Right form | Wrong form |
|---|---|---|
| Knows the rule, breaks it under pressure | Hard prohibition + rationalization table + red-flag list | Soft guidance ("prefer…") |
| Complies, but wrong output shape | Positive recipe: state what the output IS, part by part | A list of don'ts |
| Omits a required element | Required slot in a template it must fill | Prose reminders near the template |
| Behavior should depend on a condition | Conditional keyed to an observable predicate | Unconditional rule + exemption clauses |

Prohibitions backfire on shaping problems — a recipe leaves nothing to negotiate. No nuance clauses
("don't X unless it matters"): they reopen the negotiation. One excellent example beats five
mediocre ones. Never vague qualifiers ("be concise") — state the threshold ("≤150 words, no preamble").

## Structural beats behavioral

When a rule is load-bearing, prefer the mechanical control and say so: tool scoping (`tools:`),
hooks/guards, gates, validators. Prose guardrails are for cooperative agents; harness enforcement
holds under pressure. *(This fleet's pattern: read-only via missing Write/Edit + `readonly-guard.py`,
prod via `production-change-gate` + branch protection.)*

## In this fleet

- Frontmatter rules: `name` = dir/filename, charset `[a-z0-9-]`, description ≤1024 chars —
  enforced by `scripts/validate_fleet.py` (CI gate). Keep descriptions lean: every skill
  description loads into the listing budget each session.
- `model:` changes must update the policy table in `scripts/validate_fleet.py` in the same
  commit; agent frontmatter changes need `scripts/sync-copilot.sh` re-run (drift-gated).
- Add an eval scenario under `evals/` only when the outcome is gradeable (gate blocks, route lands,
  refusal happens) — no tautological evals for prose-quality skills.
- House style: trigger-style descriptions, `[verified]/[sourced]/[unverified]` labels, lead with
  the conclusion, blameless language.

## Handoffs

- → `agent-architecture` when the fix is really a lane/roster/orchestration problem, not one artifact.
- → `agent-security` before shipping anything that ingests untrusted content.
- → `self-improve-loop` to run the generate→evaluate→refine iteration on a measurable artifact.
- → `sde-engineer` for validator/eval-harness code changes.
