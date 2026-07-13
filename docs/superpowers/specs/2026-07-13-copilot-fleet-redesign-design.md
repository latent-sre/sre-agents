# Copilot fleet redesign — first-principles rebuild for VS Code / GitHub Copilot

**Date:** 2026-07-13
**Status:** approved design, pre-implementation
**Supersedes:** the Claude-Code-targeted fleet in this repo (9 agents / 37 skills) as the *distributed* artifact. This repo remains the source; the fleet it ships is rebuilt.

## Problem

The current fleet has grown to 46 units (9 agents, 37 skills) and exhibits all four failure modes the owner named:

- **Routing confusion** — one incident prompt loaded six skills at once (recorded probe trace: `incident-severity, pcf-ops, rollback-mitigation, splunk-triage, sre-ladder, …`); four skills have never fired at all on their own on-target prompts (`agent-security`, `ops-cli`, `pcf-deploy`, and — pre-clean-room — `sde-ladder`).
- **Context cost** — ~8.3k tokens always-on (AGENTS.md ~3.3k + CLAUDE.md ~1k + 37 skill descriptions ~3.9k) before any work starts.
- **Maintenance rot** — prose transcribing facts that drift: a fabricated WQL clause, a blue-green playbook that inverts on its second run, a security skill wrong about its own guard. The git history is a parade of `fix(guard)`/`fix(skill)` commits patching a denylist that is permanently behind.
- **Can't hold it in your head** — 46 units defeats roster-level reasoning.

Separately, the **target runtime changed**: the consuming team works in **VS Code + GitHub Copilot chat**, not Claude Code. And the **stack changed**: Grafana 13.x + Alloy/Loki/Tempo/Mimir/Prometheus (LGTM) arrives alongside the incumbent Splunk/Wavefront/Moogsoft/ThousandEyes stack (coexistence, not replacement), with a possible GCP onboarding later in 2026.

## Decisions already made (with the owner, in order)

| Decision | Choice |
|---|---|
| Depth of change | **First-principles redesign** (not prune, not consolidation-in-place) |
| Target runtime | **VS Code Copilot chat** only (not Copilot CLI, not the cloud coding agent) |
| Consumers | **A team of SREs** — not an org rollout; no org-admin dependencies; works in any repo they open; self-updates when this repo changes |
| Distribution | **Agent plugin, plugin-first** (owner-verified docs: private-repo marketplaces, 24h auto-update, full skill folders) with a clone+point fallback |
| Stack posture | All incumbent tools stay; LGTM is additive and first-class; **stack churn is a design axiom** (GCP lands as reference files, not restructure) |
| Sister repo | `latent-sre/sde-agents` is a **harvest source** — its doctrine, agent chassis, guard philosophy, and eval machinery import; its home-lab units do not |
| Fleet size | 5 agents / **26 distributed skills** (see count correction note in Section 4) — growth from the initial estimate was accepted "for the right reason" (backend-craft, frontend-craft, service-onboarding earn slots) |

## Section 1 — Distribution: plugin-first, clone-and-point fallback

**Primary channel.** This repo becomes an **agent plugin**: `plugin.json` at the root, `agents/`, `skills/`, `hooks/`, `.mcp.json`. Each engineer adds the team repo to `chat.plugins.marketplaces` (any git remote works; private repos supported — VS Code falls back to cloning directly) and installs once from the Extensions view (`@agentPlugins` filter). Marketplace-sourced plugins auto-update every 24h under `extensions.autoUpdate`. Skills arrive as `/sre-agents:<skill>`; agents appear in the chat dropdown; hooks and MCP config ride the same bundle.
*[sourced: code.visualstudio.com/docs/agent-customization/agent-plugins, fetched 2026-07-12]*

**Gate zero (first implementation step).** `chat.plugins.enabled` defaults to false and is **org-managed**. A five-minute test on one engineer's machine answers whether the team can flip it or policy blocks it. This is the design's only admin dependency.

**Fallback (if policy blocks plugins).** Clone to a fixed path; point the GA settings `chat.agentFilesLocations` / `chat.agentSkillsLocations` into the clone; sync via scheduled `git pull --ff-only` (or a SessionStart hook, preview). **The repo layout is identical for both channels** — choosing the channel is a per-engineer setting, not a repo fork.

**Onboarding.** `setup.ps1` (one-time): preflight git/auth → write the two settings → detect the policy gate (fall back automatically if blocked) → print the one manual Install click (the trust prompt is deliberate VS Code security UX and cannot/should not be scripted). `setup.ps1 -Verify` reports: active channel, installed commit, and whether skills are actually loading. `setup.sh` twin for non-Windows.

**Rejected channels, with reasons pinned:**
- **VS Code Marketplace extension** (`chatAgents`/`chatSkills` contribution points): stable API, native auto-update — but `chatSkills` points at a single `SKILL.md`; skill folders with `references/`/`scripts/` are unsupported (microsoft/vscode **#304721**, open, assigned, no milestone). The redesign leans on references. **Revisit trigger: #304721 closes** and a private distribution channel exists.
- **Org-level agents** (`{org}/.github(-private)/agents`) and **enterprise-managed plugins**: solid mechanisms, wrong scope — this is a team, not an org, and both require org-admin control. Revisit if the org ever adopts the fleet. Org-level *skills* don't exist yet ("coming soon" per GitHub community discussion #189753).
- **`gh skill install`**: real and GA, but covers skills only and updates are manual per-engineer.

## Section 2 — Taxonomy: map the fleet onto Copilot's seven layers

Derivation rule: **each piece of the old fleet moves to the lowest layer that can carry it.**

| Copilot layer | What moves there |
|---|---|
| Custom agents (`.agent.md`) | Only lanes with a distinct **tool scope** — the agent-vs-skill rule, machine-enforced by `tools:` |
| Agent skills | Playbooks, checklists, query patterns — auto-loaded by description or `/invoked` |
| Prompt files | One-shot workflows (ADR scaffold; Bamboo walkthrough if still needed) |
| Hooks | The read-only guard, rewritten (see Section 4) |
| MCP servers | Live tooling — a Grafana MCP server is the LGTM-exploration vehicle *(existence/fit: verify during implementation)* |
| `agents:` + `handoffs:` frontmatter | The old `route-request` + `handoff-protocol` layers, dissolved into native mechanics |
| Plugin | The distribution wrapper |

**Structural consequences:**
1. **AGENTS.md dies as always-on context.** Plugins don't inject ambient instructions into arbitrary repos — which force-ends the 3.3k-token tax. Each `.agent.md` body is self-contained; the stack profile becomes a small **`stack-profile` skill** loaded on demand. The stay-in-lane rule lives *only* there, phrased as current fact ("runtime today: on-prem + TAS; GCP under evaluation late 2026"), so one file changes when the ground shifts.
2. **Read-only becomes real.** An agent whose `tools:` omits `execute`/`edit` cannot run or write, period — enforcement by absence. The hook guard survives only as an audit/deny layer on agents that genuinely need `execute`.

## Section 3 — The agent roster: 9 → 5

| Agent | Tools (GitHub alias vocabulary) | Lane | Chassis provenance |
|---|---|---|---|
| **sre** | read, search, execute, web | Triage, RCA, incident investigation | sre-agents `sre-engineer` method + sde-agents doctrine + **Tier 0–3 change authority** |
| **sde** | all | Build/fix/refactor code and ops tooling; absorbs test-writing | **sde-agents `sde-fullstack`** (forks, checkpoint contracts, red-flags table, review packet w/ worked example) |
| **reviewer** | read, search **only** | Code + security review (two lenses, one tool scope) | **sde-agents `code-reviewer`** (`[caller-flagged]`/`[independent]` + mandatory independent-P0/P1 count; evidence gate; injection rule) + sre `security-reviewer` lens |
| **observer** | read, search, edit, execute | Obs-as-code: dashboards, alerts, SLOs; LGTM home | sre-agents `sre-monitor` + Tier 0–3 + "never cut the branch you're sitting on" |
| **scribe** | read, search, edit (**no execute**) | Runbooks + postmortems; documents commands from evidence, never runs them | sre-agents `runbook-author` modes + sde-agents `runbook` leanness |

Every agent gets: a **model fallback array** (`model: ['Claude …', '…']`), an **`agents:`** allowlist encoding who may delegate to whom, **`handoffs:`** buttons for the human-driven transitions (investigate→document, review→fix), and the uniform **doctrine layer**: `[verified]/[sourced]/[unverified]` labeling, an output packet **with a worked example**, "recommend better, never silently substitute," "ask the forks, assume the details."

**Cut:** `test-engineer` (tool scope identical to sde → its content is sde's testing sections), `researcher` (Copilot `web` tool + native subagents; also held the fleet's widest egress), `prompt-engineer`-as-agent (→ authoring skill pack), `route-request` + `handoff-protocol` (→ native `agents:`/`handoffs:`), the sister repo's ladder agents (altitude stays skill-carried; their method arrives via eng-ladder references, **rewritten self-sovereign** since the agent files they defer to won't exist).

**Known trade:** merging the reviewers loses the dedicated security-review lane identity; the reviewer body carries both lenses explicitly. Reversible (one file) if it proves wrong.

## Section 4 — Skills: 37 → 26, structured for stack churn

> **Count correction (caught in spec self-review).** Conversation tallies said "~21"; the actual
> roster below is **26**. The error was arithmetic (a miscounted "16-core" baseline carried across
> turns), not scope creep — every skill below was individually argued and approved. Net change:
> 46 units → 31 (5 agents + 26 skills), a one-third cut with disjoint triggers, rather than the
> ~45% implied earlier. If the count matters more than the boundaries, the compression candidates
> are: the three gates → one `gates` skill with modes (−2, but un-fixes solved routing);
> incident-command + postmortem → one incident skill (−1); craft + eng-ladder → one engineering
> skill (−1, muddies a measured-good trigger). Default: keep 26; boundaries beat count.

**Observability by signal, not by product** (products churn; signals don't). Each skill body teaches the investigation *shape*; per-backend `references/` teach the dialect, gated by frontend-craft-style predicate tables ("if the question involves X → read references/Y **before** writing"):

| Skill | Question | References today | Later |
|---|---|---|---|
| obs-logs | "the answer is in the logs" | SPL, LogQL | Cloud Logging |
| obs-metrics | "the answer is in the metrics" | PromQL (Mimir), WQL | Managed Prometheus |
| obs-traces | "follow one request" (new capability) | TraceQL, OTel | — |
| obs-dashboards | Grafana 13.x as code | provisioning; legacy Wavefront | — |
| obs-alerting | alert, correlate, page | Grafana unified alerting; SLO burn-rate (script survives); Moogsoft; ThousandEyes | — |
| obs-pipeline | what ships telemetry where | Alloy, collectors | GCP exporters |

Boundary note: `frontend-craft/references/data-viz.md` owns **product-UI charts** (Recharts/uPlot); `obs-dashboards` owns **Grafana**. Stated in both descriptions so they never compete.

**Full skill roster** (provenance: SRE = sre-agents, SDE = sde-agents, NEW):

| Skill | Provenance / notes |
|---|---|
| stack-profile | NEW — the single stack-definition point; current-fact phrasing |
| obs-logs, obs-metrics, obs-traces, obs-dashboards, obs-alerting, obs-pipeline | SRE content restructured; LGTM references NEW |
| pcf-ops | SRE (factually clean per audit) |
| pcf-deploy | SRE, **blue-green playbook fixed** (name rotation); stays `disable-model-invocation` |
| service-onboarding | **SDE `service-onboard` reshaped for work** — the LGTM adoption playbook; audit mode from `lab-audit` (evidence rules: "no finding without the command output"; "top three fixes, not thirty"); `disable-model-invocation` |
| incident-command | SRE `incident-severity` + rollback decision content |
| postmortem | SRE `blameless-postmortem` |
| runbook | **SDE body** + SRE template as asset |
| merge-gate, release-gate, production-change-gate | SRE (eval'd well separated); prod gate gains the **Tier 0–3 model** + branch-protection check |
| craft | SRE (already the model: per-language references) |
| backend-craft | **SDE, imported whole** (6 references); `references/stack.md` rewritten for work stack; absorbs api-design/ops-stack-integration |
| frontend-craft | **SDE, imported whole** (5 references); absorbs spa-architecture |
| ops-tooling | body = **SDE `sre-tool` pipeline** (mission transaction, environment card, right-sizing, review-seeding rules); CLI patterns reference absorbs ops-cli |
| root-cause | **SDE, replaces debug-rca** (measured winner: 2/2 misroutes went *to* it) |
| eng-ladder | **SDE base** (one skill, three tier references, rewritten self-sovereign) + SRE track content |
| ci-actions | SRE `github-actions-ci`, `cf auth` argv leak fixed. Bamboo content: **default delete** (recoverable from git); becomes a prompt file only if live migrations remain — confirm in Phase 3 |
| database-reliability | SRE |
| agent-authoring | SDE `prompt-craft`/`prompt-engineer` method + SRE `agent-authoring`; references absorb tool-design, context-engineering, multi-agent-architect's "should this be multi-agent at all?"; teaches **personal-first, promote-by-PR** and compose-with-fleet-agents |
| agent-security | SRE, rewritten Copilot-native (tool-scope containment) — ships because teammates *will* build their own agents |

Prompt files: `adr` (scaffold). Old skills not named above are absorbed or deleted; the implementation plan (writing-plans phase) carries the full 37→26 disposition table naming where every old skill's content lands.

## Section 5 — Safety model

1. **Primary control: `tools:` omission.** reviewer and scribe physically cannot execute; scribe cannot run what it documents.
2. **The hook guard — allowlist, imported doctrine.** *"Enumerating the ways a command can write is unbounded and always a step behind; enumerating what an agent needs is bounded, knowable, and fails loud."* (sde-agents; sre-agents' 20+ guard-fix commits are the proof by exhaustion, capped by the live `python -m pip` bypass found 2026-07-12.) The new hook: **allowlist**; **positive-ALLOW protocol** (distinctive exit codes so a stand-in interpreter exiting 0 cannot read as ALLOW; fail closed); **parser humility** (substitution/redirection/subshell → deny by construction); **self-scoping** on the payload's agent identity because **VS Code ignores hook matchers** — hooks fire on every tool, so the script filters on `toolName` itself; **camelCase payloads**; **runs only from the plugin's installed copy**, never a workspace copy (a repo under review could supply its own guard); **never touches non-fleet sessions** — deny-for-the-guarded-agent AND never-touch-anyone-else are both tested, because getting either wrong is worse than no guard.
3. **Change authority: Tier 0–3** (observe / prepare / reversible-live / destructive-or-access-path), imported from sde-agents `homelab-platform`: classify before acting; approval covers only the commands shown; a material change re-enters the gate; independent Tier 0/1 work continues while approval pends; worked approval-request example (target, diff, exact command, blast radius, verification, rollback). Woven into sre + observer bodies and production-change-gate.
4. **Prod boundary unchanged:** GitHub branch protection + protected environments, with the gate's `gh api …/protection` check (must return `enforce_admins: true`, 404 = BLOCK).
5. **Probed, not assumed.** Platform facts the safety model rests on get **probes re-run after every VS Code/Copilot upgrade** (the sde-agents discipline: `hooks:`-on-plugin-agents silently ignored and `Bash(git diff:*)` scoping inert were both *probed*, not read). New-fleet probe list: hook payload shape (camelCase, agent identity field), plugin skill/agent loading, hook firing for plugin-shipped hooks, `disable-model-invocation` behavior.

## Section 6 — Validation & maintenance machinery

- **Validator** (rewritten for Copilot artifacts): unknown-frontmatter-key rejection (the `hooks:`→`hook:` war story — a typo silently disarms), **kebab-case name enforcement** (silent load failure class), `agents:`/`handoffs:` targets must exist, description trigger-format lint (verbatim user phrasings — the one pattern with 3/3 baselines), bundle-reference existence, `plugin.json` manifest integrity, schema-vs-policy error separation, `--write-inventory` regenerating the README fleet table.
- **Routing evals** (sde-agents format + sre-agents clean-room rig): overlap clusters, positives + **near-miss negatives** ("shares vocabulary, should route elsewhere"), graded deterministically off transcripts, reported as **rates over runs**, cases phrased to measure routing without spawning long sessions. Honest limitation carried forward: this measures **Claude Code as proxy** — nothing measures Copilot's actual routing today. **Open item:** evaluate Copilot CLI as a native headless probe.
- **Behavioral probes with canary strings** (plant a distinctive string in a skill; its appearance in output proves loading) + **tripwire tests guarding the canaries** (an innocent copy-edit would silently disarm the oracle).
- **Hook wiring tests** run the command string from `hooks.json` exactly as the runtime does — testing the script is not testing the hook.
- **CI**: the restored workflow extends to the new validator + tests. Anti-rot rule from the audit, now doctrine: **a skill never transcribes an artifact that lives in the repo — point at it.**

## Section 7 — Migration plan (phases; each independently valuable)

0. **Gate check:** `chat.plugins.enabled` flippable? (five minutes; decides channel, not layout)
1. **Scaffold:** `plugin.json`, new `agents/`/`skills/` layout at repo root (no second source of truth), validator v2 skeleton, CI extension
2. **Chassis:** 5 agents from the sde-agents bodies + doctrine layer + `agents:`/`handoffs:`/model arrays
3. **Skill harvest:** direct imports (root-cause, eng-ladder, runbook, backend/frontend-craft, ops-tooling) → then SRE domain skills with audit fixes applied (blue-green, WQL, SPL, cf auth, error_budget)
4. **Obs restructure:** six by-signal skills; LGTM references written; legacy references carried over post-fact-check
5. **Machinery:** allowlist hook + wiring tests, probes + canaries, routing evals, `setup.ps1`
6. **Pilot:** one engineer, real work repos, `-Verify` diagnostics; fix what reality finds
7. **Team rollout** + retire the old 37-skill layout (and the owner retires personal `~/.claude` duplicates: root-cause, eng-ladder, runbook — the clean-room-diagnosed shadowing)

**Migration ordering rule** (imported): fix internal contradictions first — the one class of change needing no behavioral baseline.

## Explicitly deferred / out of scope

- GCP skills (trigger: onboarding becomes real → `references/gcp.md` additions)
- Extension packaging (trigger: #304721 closes + private channel exists)
- Enterprise-managed plugins / org-level anything (trigger: org adoption)
- Copilot-native routing measurement (open research; CLI probe candidate)
- Old-fleet content not named in the disposition table (deleted, not ported "just in case")

## Risks (ranked) and open questions

1. **Agent plugins are Preview** — format churn could break the team at once. Mitigations: identical-layout fallback channel; probes catch loading regressions; pin plugin versions if churn appears.
2. **`chat.plugins.enabled` org-policy-blocked** — fallback channel exists; gate check is step 0.
3. **No Copilot routing measurement** — descriptions are grounded in the one measured pattern (verbatim triggers) and the Claude proxy; risk of silent dark skills recurring. Probe + canary loading checks partially cover.
4. **Hook payload details under-documented** — the probe list exists precisely for this; the guard fails closed if the payload shape shifts.
5. **Reviewer merge could dilute security reviews** — watch review outputs during pilot; split is one file if needed.

## Provenance summary

- **sre-agents contributes:** domain content (PCF, obs queries, incident process, gates, DB reliability), the clean-room eval rig, the restored CI, the audit's factual fixes.
- **sde-agents contributes:** the agent chassis (reviewer/sde bodies), the doctrine layer (packets + worked examples + verification labeling), allowlist guard philosophy + positive-ALLOW protocol, Tier 0–3 change authority, service-onboard/lab-audit shapes, eng-ladder, root-cause, backend/frontend-craft, canary probes, tripwire tests, cluster routing evals, validator hardening patterns, "no second source of truth."
- **New:** plugin packaging, six by-signal obs skills, LGTM references, stack-profile, setup.ps1, Copilot-native validator/hook/probes.
