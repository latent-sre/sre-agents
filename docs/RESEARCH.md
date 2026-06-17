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

## Stack — current product names (verify before quoting)
| We say | Current name / fact | Source |
|---|---|---|
| PCF | VMware **Tanzu Application Service** (Broadcom); `cf` CLI v8 / CAPI V3 | techdocs.broadcom.com (Tanzu Platform for Cloud Foundry) |
| Wavefront | **VMware Aria Operations for Applications** (WQL, `ts()`) | https://docs.wavefront.com/query_language_reference.html |
| Moogsoft | **Dell APEX AIOps Incident Management** (on-prem v9.x) | https://docs.moogsoft.com/ |
| Splunk / ThousandEyes | **Cisco** Splunk (SPL) / Cisco ThousandEyes (API v7; Enterprise vs Cloud agents) | docs.thousandeyes.com |

## PCF specifics we verified (and what we dropped)
**Verified against Cloud Foundry docs and baked into `pcf-ops`:**
- Gorouter **502** keep-alive race: if app keep-alive idle timeout `< 90s` it can close a connection as
  Gorouter reuses it → 502; set the app's keep-alive `> 90s`. — https://docs.cloudfoundry.org/adminguide/routing-keepalive.html
- Health-check **types** `port`/`process`/`http`; **default liveness = port, readiness = process**;
  liveness fail → restart, readiness fail → removed from route pool. — https://docs.cloudfoundry.org/devguide/deploy-apps/healthchecks.html
- `Exited with status 137` = OOM (SIGKILL). (Standard container behavior.)

**Dropped as unverified** (a sibling branch asserted them; we could not confirm, so they are NOT in our
skills): "503 = clock skew / `x509 not-yet-valid`", "health-check invocation-timeout default 1s",
"Gorouter `max_attempts=3`".

## Prior branches mined (provenance for upgrades)
Tier-1 and batch-2 content was adapted (and re-verified) from three earlier attempts on this repo:
- `origin/claude/vscode-sre-sde-agents-eu1uvu` — best PCF/stack content (502/503, Actions Importer, cf deploy job, SPL/WQL, language footguns).
- `origin/claude/elite-agent-architecture-n0q56b` — DBRE agent, OTel instrument-service, incident doctrine, researcher rigor.
- `origin/claude/great-shannon-98cxyn` — ADR/RFC templates, docs-first structure, current language tooling.

## Knowledge sources (broader grounding)
`anthropics/anthropic-cookbook` (agent/skill/eval patterns) · `ComposioHQ/awesome-claude-skills`
(community skills) · `affaan-m/ecc` (harness-native operator system; skill-first + per-language rules +
cross-harness adapters).
