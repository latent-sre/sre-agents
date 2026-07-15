# Task 46 root-document absorption audit

This table is the durable, PR-ready record required before the root files are rewritten. The source files
remain frozen under `legacy/claude-fleet/`; each inclusive range below is accounted for exactly once.

| Legacy range | Content absorbed or retired | Durable home | Status |
|---|---|---|---|
| `AGENTS.md:1-16` | Fleet introduction, routing entrypoint, and repository-mechanics pointer | `README.md` introduction and canonical inventory; `canonical/fleet.json` routing graph; new repository-only `AGENTS.md` | Complete |
| `AGENTS.md:17-52` | Stack profile and application/platform ownership boundary | `skills/stack-profile/SKILL.md` | Complete |
| `AGENTS.md:53-70` | Agent roster, lanes, write posture, and skill relationships | `canonical/fleet.json` agents, capabilities, required skills, delegation, and handoffs; `README.md` agent table | Complete |
| `AGENTS.md:71-89` | Read-only doctrine, structural capability limits, execution-mode distinctions, and guard caveats | `canonical/agents/reviewer.md` and `canonical/agents/scribe.md` terminal execution boundaries; `canonical/agents/sre.md` and `canonical/agents/observer.md` selected execution-mode boundaries; capability projection in `canonical/fleet.json`; `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md` Sections 3 and 5a | Complete |
| `AGENTS.md:90-119` | Egress census, lethal-trifecta warning, CI execution boundary, delegation-not-isolation rule, and no mutable-path exemption | `canonical/agents/sre.md` trifecta section; `canonical/agents/reviewer.md` CI boundary; `skills/agent-security/SKILL.md` delegation and content-hash rules; `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md` Sections 3 and 5c | Complete |
| `AGENTS.md:120-126` | Routing-as-skill cost rationale | Design decision record; `skills/agent-authoring/references/roster.md` agent-versus-skill rule | Complete |
| `AGENTS.md:127-130` | Seniority and incident altitude carried by skills | `skills/eng-ladder/SKILL.md` and its registered references | Complete |
| `AGENTS.md:131-143` | Skill discovery, trigger descriptions, and explicit loading | `skills/agent-authoring/SKILL.md` runtime reference; canonical 26-skill catalog; `README.md` skill table | Complete |
| `AGENTS.md:144-158` | Routing selectors, three distinct gates, and hard-enforcement boundary | Native agents/handoffs in `canonical/fleet.json`; `skills/merge-gate/`, `skills/release-gate/`, and `skills/production-change-gate/` | Complete |
| `AGENTS.md:159-167` | Feature, incident, and reliability handoff flows | Canonical `delegates_to` and `handoffs` edges; `README.md` agent routing table | Complete |
| `AGENTS.md:168-191` | Shared least-privilege, handoff, evidence, safety, reporting, and blameless doctrine | Uniform doctrine layers in all five `canonical/agents/*.md` bodies; new `AGENTS.md` verification policy | Complete |
| `CLAUDE.md:1-6` | Claude entrypoint importing the cross-tool repository guide | Minimal root `CLAUDE.md` with `@AGENTS.md` | Complete |
| `CLAUDE.md:7-34` | Claude-specific agent/skill loading and ladder behavior; gate enforcement versus cooperative local checks; administrator-bypass caveat; routing's token/latency rationale, rejection of obsolete capability/context-loss explanations, and reasoned-not-measured A/B qualification | Projection rules in `skills/agent-authoring/SKILL.md`; `skills/eng-ladder/SKILL.md`; canonical graph in `canonical/fleet.json`; enforcement boundary in `skills/production-change-gate/SKILL.md`; routing decision in `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md` and `skills/agent-authoring/references/roster.md`; `generated/claude/agents/` | Complete |
| `CLAUDE.md:35-53` | No-pinned-model synchronization benefit and the cost of losing heterogeneous cheap-versus-judgment-heavy tiers | Runtime model-policy decision in `docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md`; explicit maintenance-versus-tiering trade-off in `skills/agent-authoring/references/roster.md` | Complete |
| `CLAUDE.md:54-57` | Obsolete claim that both runtimes consume the same mutable `.claude` tree | Retired and replaced by `README.md` authoring model, `scripts/generate_fleet.py`, and separate `generated/copilot/` and `generated/claude/` projections | Complete |

Result: **15/15 sections absorbed**. No legacy section lacks a named durable home, and obsolete runtime
claims are explicitly retired rather than silently copied.
