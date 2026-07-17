# Research & provenance

Why the fleet is built the way it is, with sources. Current as of **2026-06-17**. Formats and product
names move fast — re-verify load-bearing specifics (and label anything you can't confirm "unverified",
per the `researcher` agent's rules).

## Format & portability (the foundation)
| Claim | Source |
|---|---|
| Claude Code subagents: `.claude/agents/*.md`, frontmatter `name`/`description`/`tools`/`model`(+`hooks`,`skills`,…) | https://code.claude.com/docs/en/sub-agents |
| Claude Code skills follow the open Agent Skills standard; `.claude/skills/<name>/SKILL.md`; invocation control, `context: fork` | https://code.claude.com/docs/en/skills |
| **Agent Skills** open standard (`SKILL.md`): `name` ≤64 lowercase-hyphen + matches dir, `description` ≤1024; `scripts/`,`references/`,`assets/`; progressive disclosure | https://agentskills.io/specification |
| Published by Anthropic **2025-12-18**, adopted across 30+ tools | https://agentskills.io , https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/ |
| VS Code / Copilot **custom agents** (renamed from chat modes): read `.github/agents/*.agent.md` **and** `.claude/agents/`; tools are namespaced (`search/codebase`, `web/fetch`) + flat (`edit`, `runCommands`) | https://code.visualstudio.com/docs/agent-customization/custom-agents |
| VS Code / Copilot **skills**: read from `.github/skills/`, `.claude/skills/`, `.agents/skills/` | https://code.visualstudio.com/docs/agent-customization/agent-skills |
| `AGENTS.md` cross-tool project-guide standard | https://agents.md |
| Claude Code `CLAUDE.md` imports other files with `@path` (recommended: `@AGENTS.md`) | https://code.claude.com/docs/en/memory |
| `PreToolUse` hooks: subagent-frontmatter `hooks:` form; block via exit-2 or `permissionDecision:"deny"` JSON; stdin gives `tool_input.command` | https://code.claude.com/docs/en/hooks |

**Implication:** one source under `.claude/` is read natively by both tools → author once, generate
Copilot-native `.github/` files only for hard tool scoping.

## Knowledge sources (broader grounding)
`anthropics/anthropic-cookbook` (agent/skill/eval patterns) · `ComposioHQ/awesome-claude-skills`
(community skills) · `affaan-m/ecc` (harness-native operator system; skill-first + per-language rules +
cross-harness adapters).

## Fleet adoption provenance (2026-07-17)

| Fact | Source |
|---|---|
| Fleet content adopted from the codex/cleanup implementation of the 2026-07-13 redesign | docs/superpowers/specs/2026-07-17-claude-fleet-adoption-design.md |
| Sister-repo state grafted | latent-sre/sde-agents @ ac2e222 |
| Frontmatter `hooks:` fire on project-scope agents, silently ignored on plugin agents (probed) | scripts/readonly-guard.py docstring |
| `tools: Bash(...)` specifiers are inert on agents; real only in settings permission rules (probed) | scripts/readonly-guard.py docstring |
| `Agent(target)` type lists bind main-thread agents only; ignored at subagent depth | .claude/skills/agent-authoring/references/claude-code-frontmatter.md |
