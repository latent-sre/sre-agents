# Copilot fleet redesign — first-principles rebuild for VS Code / GitHub Copilot

**Date:** 2026-07-13
**Status:** approved design, pre-implementation
**Supersedes:** the Claude-Code-targeted fleet in this repo (9 agents / 37 skills) as the *distributed* artifact. This repo remains the source; the fleet it ships is rebuilt.

## Problem

The current fleet has grown to 46 units (9 agents, 37 skills) and exhibits all four failure modes the owner named:

- **Routing confusion** — one incident prompt loaded six skills at once (recorded probe trace: `incident-severity, pcf-ops, rollback-mitigation, splunk-triage, sre-ladder, …`); **three** skills have never fired on their own on-target prompts (`agent-security`, `ops-cli`, and, pre-clean-room,
  `sde-ladder`). *(An earlier draft counted four, including `pcf-deploy`. That one sets `disable-model-invocation: true`
  — its `saw: none` is the flag working as designed, not a discovery failure. Counting it inflated the problem.)*
- **Context cost** — ~8.3k tokens always-on (AGENTS.md ~3.3k + CLAUDE.md ~1k + 37 skill descriptions ~3.9k) before any work starts.
- **Maintenance rot** — prose transcribing facts that drift: a fabricated WQL clause, a blue-green playbook that inverts on its second run, a security skill wrong about its own guard. The git history is a parade of `fix(guard)`/`fix(skill)` commits patching a denylist that is permanently behind.
- **Can't hold it in your head** — 46 units defeats roster-level reasoning.

Separately, the **primary team runtime changed**: the consuming team works in **VS Code + GitHub Copilot chat**. Claude Code remains a secondary compatibility runtime for the repo owner and must load its own generated projection; it is never used as evidence for Copilot. And the **stack changed**: Grafana 13.x + Alloy/Loki/Tempo/Mimir/Prometheus (LGTM) arrives alongside the incumbent Splunk/Wavefront/Moogsoft/ThousandEyes stack (coexistence, not replacement), with a possible GCP onboarding later in 2026.

## Decisions already made (with the owner, in order)

| Decision | Choice |
|---|---|
| Depth of change | **First-principles redesign** (not prune, not consolidation-in-place) |
| Target runtime | **Primary/team:** VS Code Copilot chat (not Copilot CLI or the cloud coding agent). **Secondary compatibility:** Claude Code via its separately generated and validated projection. |
| Consumers | **A team of SREs** — not an org rollout; works in any repo they open after the selected execution mode passes its runtime gate; an installed updater follows the protected `release` ref and atomically disables brokered discovery or switches to the verified safe-recovery projection on stale or unverifiable state |
| Distribution | **Agent plugin, plugin-first** (owner-verified docs: private-repo marketplaces and full skill folders) with an exact-inventory, versioned fallback projection |
| Stack posture | All incumbent tools stay; LGTM is additive and first-class; **stack churn is a design axiom** (GCP lands as reference files, not restructure) |
| Sister repo | `latent-sre/sde-agents` is a **harvest source** — its doctrine, agent chassis, guard philosophy, and eval machinery import; its home-lab units do not |
| Fleet size | 5 agents / **26 distributed skills** (see count correction note in Section 4) — growth from the initial estimate was accepted "for the right reason" (backend-craft, frontend-craft, service-onboarding earn slots) |

### The sister repo (harvest source), located

`sde-agents` is the owner's *other* agent fleet — a leaner, newer-generation Claude Code plugin
(7 agents / 9 skills: code review, engineering ladder, root-cause debugging, backend/frontend craft,
plus home-lab operations). It is **not** part of this repository and never becomes one — it stays an
independent personal fleet; content imports here are one-way copies that this repo then owns.

- **GitHub:** https://github.com/latent-sre/sde-agents
- **Local checkout (this machine):** `C:\Users\hawkins\sde-agents`
- **Files this spec cites from it:** the plan-format template
  (`docs/superpowers/plans/2026-07-12-fleet-doctrine-alignment.md`), the allowlist guard
  (`scripts/readonly-guard.py` + `hooks/hooks.json`), the doctrine spec
  (`docs/superpowers/specs/2026-07-12-fleet-doctrine-alignment-design.md`), and the agent/skill
  bodies named in the provenance columns below.

The full harvest ledger is the Provenance summary at the end of this document; every roster table
marks imported units SDE (from sde-agents), SRE (from this repo's old fleet), or NEW.

## Section 0 — Run protocol: how every session on this spec opens and closes

This spec is built across many sessions by agents that start cold. Two things must therefore be mechanical,
not remembered.

### Open: sync from `main`, and let it fail loudly

```
git status --porcelain                   # must be empty; a dirty tree makes the next line half-fail
git fetch --prune origin                 # --prune: phase branches get merged and auto-deleted
git switch main && git pull --ff-only origin main
git log --oneline -1                     # record the SHA this phase branched from
git switch -c <phase-branch>             # branch from main, NEVER from another phase branch
```

`--ff-only` is the load-bearing flag: it **fails** rather than silently manufacturing a merge commit when
local `main` has drifted.

**The owner merges PRs mid-session, so `main` moves *under* a long-running phase.** Fetching alone does not
fix that — it updates remote-tracking refs and leaves your branch exactly where it was, so you learn `main`
moved and change nothing. Before opening each PR, actually **move the branch**:

```
git fetch --prune origin
git rebase origin/main
git log --oneline origin/main..HEAD      # assert: ONLY this phase's commits
```

That last line is the real check. The failure this prevents is not an error — it is a **silently inflated
diff**: if a PR is stacked on another phase branch and that parent merges and auto-deletes, GitHub
**re-targets the child to the parent's base rather than erroring**, absorbing the parent's commits into your
diff. Branch every phase from `main` and the mode cannot occur.

### Close: four audits, in cost order

A phase is not done until **A–C** are green. **D** runs at the end of **Phase 3** (the first point the fleet is
content-complete) and again at **Phase 6** — not at every phase boundary, because "0 dark skills" over a
half-built skill set is vacuously true, which is a green light that measured nothing.

| Audit | Catches | Cannot catch | Cost |
|---|---|---|---|
| **A — Mechanical** | broken structure: bad frontmatter, unwired hooks, dangling references, non-kebab names | anything about whether the *content* is true | free |
| **B — Content regression** | a known-bad fact ported forward verbatim | — *(once mechanized; see below)* | free |
| **C — Adversarial review** | design holes, security regressions, spec non-conformance, **unverifiable stack facts** | things no reviewer thought to look for | model |
| **D — Behavioral** | dark skills, routing fan-out, selected execution-boundary behavior, token budget | correctness of any individual answer | model + time |

**A — Mechanical.** One command. It is the same entrypoint CI runs, so the two cannot drift:

```
python scripts/gate_a.py
```

It resolves its own interpreter (`sys.executable`), which settles the `python` / `python3` / `py -3` question
by not having an opinion — `python3` on Windows is the Microsoft Store stub, the bug that once silently
disarmed the read-only guard. It preflights the pinned deps rather than letting a cold agent reach for a bare
`pip install pyyaml`. **Do not transcribe its steps back into this document**; that is how the previous draft
of this section shipped a step-list that had already dropped the dependency install.

**B — Content regression. The audit that exists because of our own history.** The Tier-2 bugs in
[`docs/AUDIT-2026-07-12.md`](../../AUDIT-2026-07-12.md) are **live on `main` right now**, and this migration's
core operation is *copying content forward* — so verbatim-move discipline will faithfully preserve every one of
them. They are not stylistic: a prod-password leak in `argv`, a blue-green playbook that pushes onto the live app
on its second run, an SPL filter that guarantees the alert under-fires, an error-budget script that prints
"within budget" at 5.50x burn, a fabricated WQL clause, and Grafana data sources needing an Enterprise license we
do not have.

> **Mechanize this gate — do not leave it as prose.** As a manual "diff each ported skill against the ledger"
> pass it is the most skippable gate in the stack, and it is the one we already know we need. All six bugs are
> **string-detectable**. **Phase 1 deliverable: `scripts/test_no_regressions.py`** — six assertions, pure stdlib,
> wired into `gate_a.py`. B then collapses into A: free, permanent, unskippable. The repo's own doctrine is
> *structural enforcement over prose*; B is currently prose.

**C — Adversarial review.** Independent eyes on the diff: `code-reviewer`, `security-reviewer`, and one reviewer
briefed only on the spec, checking conformance rather than code. **Not ceremony — it has already paid, twice.**
The independent sanity review of this spec found the hole neither the author nor the design caught (the fallback
channel shipped **no hook guard at all**, so `sre`/`observer` would have gone out with `execute` and no
allowlist). The review of *this very section* caught that Gate A, as first written, **could not run at all from
Phase 1 onward** — Phase 1's opening `git mv` moved the directories the validator hardcoded.

C also owns the one class **no other gate covers**: a stack fact we *invent* during the port. B catches
*known*-bad facts; nothing else looks at truth. Since a fabricated WQL clause is the fleet's own headline rot
mode, C carries an explicit rule: **every stack-specific command, query, or API field in a ported skill is either
executed against the real system and labeled `[verified]`, or labeled `[unverified]`.** An unlabeled claim is a
review finding.

**D — Behavioral.** Run **Section 8's acceptance table in full**, through the clean-room rig
(`evals/clean_room.py`) so the operator's personal skills cannot compete with the fleet for discovery. The table
is the source of truth; it is deliberately *not* re-listed here.

> **Gate A cannot catch a single Tier-2 bug, and that is the whole point of running four.** This is
> demonstrated, not argued. On `main` at `36812ed`, the entire mechanical suite passes — *"Validated 37 skills
> and 9 agents… VALIDATION: PASS"*, 11/11 validator tests, 505/505 guard cases, 25/25 scenarios — while
> `.claude/skills/github-actions-ci/SKILL.md:107` reads `cf auth "$CF_USERNAME" "$CF_PASSWORD"`, putting the
> production password in `argv` where any process on the box can read it. The validator is *structural*: it
> checks that a skill is well-formed, never that it is right. **A green Gate A over a leaking fleet is the
> normal case, not the edge case.** Auditing means B and C ran too, or it means nothing.

## Section 1 — Distribution: plugin-first, verified versioned fallback

**Primary channel.** This repo becomes an **agent plugin with one canonical fleet model and two generated runtime projections** plus a generated Copilot safe-recovery variant. `canonical/fleet.json` plus `canonical/agents/*.md` are the only agent-definition authoring sources; shared skills remain authored under `skills/`. The generator emits:

- root **`plugin.json`** for Copilot, whose `agents` field points to the **directory** `./generated/copilot/agents/`;
- **`.claude-plugin/plugin.json`** for Claude Code, whose `agents` field enumerates the generated Claude files under `./generated/claude/agents/` explicitly;
- **`generated/copilot-safe/agents/`**, a non-manifest recovery variant with the same names/bodies but structural execute omission for `sre`/`observer`;
- Copilot wrappers named `*.agent.md` and Claude wrappers named `*.md`;
- **`generated/runtime-tree.json`**, added in Phase 4, hashing every runtime-visible file and declaring the selected `execution_mode`.

The two manifests carry the same generated `name` and `version`, but each contains only fields documented for that runtime; canonical metadata is mapped, never copied wholesale. With zero canonical agents and commands both emit `"agents": []` and `"commands": []`, replacing those default discovery paths. With zero canonical skills both emit `"skills": []` as an explicit schema state, but Claude's `skills` field is additive: exact absence from the default `skills/` tree is enforced by canonical inventory, not by that empty field. Once nonempty, the path shapes above apply; Copilot references the command directory while Claude enumerates canonical command files. `--check` fails on manifest or wrapper drift, including the safe-recovery variant, unsafe parents/hardlinks, and nested or wrong-suffix files in generator-owned directories; `--write` uses same-directory temporary files plus atomic replacement and fails closed on links, junctions, and Windows reparse points. They are generated views, **not separate sources of truth**. All variants share the same bodies and skill bundles; only runtime frontmatter/capability projection differs. Copilot auto-discovers root `hooks.json`; Claude Code auto-discovers `hooks/hooks.json`; both stay empty. Neither manifest re-references them. The marketplace's documented refresh cadence is availability behavior, not an integrity boundary: the installed updater independently verifies protected `release`, active-tree identity, and the 26-hour freshness deadline, atomically disabling brokered discovery or switching to the verified safe-recovery projection on skew. Maintenance-deny remains a secondary fail-closed state only while the proven fleet hook is known to be live; it is never credited after client drift could stop hook invocation. Phase 4 records safe mode or a brokered candidate only after both Copilot paths pass; Phase 5 requalifies the selected channel on a team client and may only downgrade to safe. Only the final brokered Copilot setup installs the separately proven machine-local enforcement scope, and setup preinstalls the safe recovery view before brokered discovery. Claude `sre`/`observer` omit execute here.
Production canonical data also inventories every runtime-visible command, skill, and bundled reference, asset, and script; each agent names its skill dependencies. Missing or unexpected files, unlisted commands/skills, and unknown agent-to-skill dependencies fail generation before either runtime can load them. The Phase-1 spike carries one inert file of each bundled skill kind and proves exact inventory plus POSIX path containment before Task 1 ports the generator; Task 9 adds the separate Markdown-link checks.
*[sourced: code.visualstudio.com/docs/agent-customization/agent-plugins and code.claude.com/docs/en/plugins-reference, rechecked 2026-07-14]*

**The marketplace layer (was missing — a builder hits this on day one).** A git repo becomes a
marketplace via **`.claude-plugin/marketplace.json`** at its root; VS Code's plugin docs defer to this
schema *[sourced: code.claude.com/docs/en/plugin-marketplaces]*. **One repo can be both marketplace and
plugin.** Our entry:

```jsonc
// .claude-plugin/marketplace.json
{ "name": "latent-sre", "owner": { "name": "latent-sre" },
  "plugins": [ { "name": "sre-agents",
                 "source": { "source": "github", "repo": "latent-sre/sre-agents", "ref": "release" },
                 "description": "SRE + SDE fleet for VS Code Copilot" } ] }
```

**Why a `github` source with `ref`, not a relative `"./"` path — this is a security decision, not a
style one.** A relative source tracks whatever the marketplace repo is cloned at (effectively default-branch
HEAD, and the exact ref behavior is *undocumented*). Git-based sources accept **`ref`** (branch/tag/commit)
and **`sha`** (40-char, the effective pin) *[sourced: same]*. This plugin ships model-visible instructions plus
the reviewed setup/broker sources that setup installs only after the selected execution-mode gate passes; an
unreviewed source can therefore redirect agent tool use or replace lifecycle controls. VS Code's trust warning covers the general risk:
*"Plugins can include hooks and MCP servers that run code on your machine. Review the plugin contents and publisher
before installing."* With a `./` source, **ordinary work on `main` can become runtime-visible through marketplace
refresh without the protected `release` promotion and installed-source handshake.**

**Release discipline (consequence of the above).**
- The marketplace pins **`ref: release`**. `main` is the working branch; **`release` is what engineers run.**
- Promotion `main` → `release` requires green CI, human + Code Owner review, and the complete protection contract. **Every path is workstation-security input**, including future root Python startup files and default-discovery locations, so CODEOWNERS begins with `* @maintainer`; a current-path allowlist is not sufficient.
- `release` is created once, after Phase 5, at the exact clean reviewed green `origin/main` SHA under a pre-existing ruleset. It is never snapshotted from a feature branch. That protected `0.9.0` ref is what the pilot installs; later changes are ordinary reviewed `main → release` promotions.
- **Rollback/freshness:** revert on `release` and announce. Scheduled `setup --refresh` verifies protected release at least daily; brokered execution enters maintenance deny when the last successful protected fetch is older than 26 hours or when remote/active/runtime differ. An old-plugin/old-guard pair is not silently called healthy.
- Bump `version` in `canonical/fleet.json` on every promotion and regenerate both manifests + Copilot safe-recovery + runtime-tree projections; direct projection edits are forbidden.

**The gate checks (three, not one — they run in Phase 5, Distribution).** An earlier draft called `chat.plugins.enabled`
"the design's only admin dependency," and fronted the plan with it. Both were wrong: there are three gates, and none of
them gates *content* — they decide which channel delivers a fleet that is identical either way. They belong with
Distribution:
1. **`chat.plugins.enabled`** — defaults false, **org-managed**. Flippable, or policy-blocked? (Decides channel.)
2. **Copilot org policy — "Editor preview features."** Agent plugins are Preview; an org toggle can gate preview features independently of the VS Code setting. *[unverified — verify here rather than assert]*
3. **Model availability.** Section 3 pins Claude-first fallback arrays. Anthropic-model access depends on org model policy and license tier. Confirm the named models are actually selectable, and record the assumed tier (Business/Enterprise) as a stated assumption.

**The format contract is a Phase-1 blocking preflight, not an inference.** Before any fleet agent is authored, a nonempty spike must load one coordinator, one delegated terminal agent, one shared skill/reference, and one inert hook through three separately recorded paths: native Copilot plugin discovery, Copilot fallback discovery, and Claude Code. Claude evidence never substitutes for either Copilot path. The hook-payload probes for the production guard still run in Phase 4, where they are first needed. See Section 7.

**Fallback (if policy blocks plugins).** Setup materializes an exact-inventory, versioned tree under `~/.sre-agents/releases/<sha>/fleet` and points the GA agent/skill settings directly at its Copilot projection. It never loads the mutable verification clone. Scheduled `setup --refresh` verifies protected release, stages a new complete tree/runtime, and atomically switches the JSONC paths; bare `git pull` is forbidden. The plugin and fallback channels consume the **same Copilot projection**; Claude consumes its separate no-guard/no-execute-for-SRE projection.

**Onboarding — trusted bootstrap first, then one selected Copilot channel:**

- **Bootstrap:** the maintainer publishes the exact protected-release SHA and setup SHA-256 out of band. The engineer
  downloads into a fresh non-workspace directory and verifies both *before execution* with an absolute OS-owned hash
  utility under a no-profile, sanitized environment; PATH, aliases, functions, and workspace profiles are excluded.
  A checkout-local script cannot authenticate itself after it starts. Setup still refuses unless its own bytes/path
  equal the fetched release copy.
- **Preflight:** `git`/`gh auth`/settings found; absolute owner-approved outer executor, hash utility, isolated-capable
  Python, and broker tools found. The verification clone has canonical origin and clean `HEAD == origin/release`.
  The API response must prove review count, Code Owner review, exact Gate-A context, administrators enforced, and
  force-push/deletion disabled. Version text or one protection boolean is insufficient.
- **Selected execution mode:** Phase 4 records `safe` or a brokered candidate only after both Copilot delivery paths
  pass hostile-workspace precedence/location, outer-spawn, nested identity, updated-input, terminal poisoning, and
  shell-grammar probes. Phase 5 reruns the complete suite through the selected channel on a team client and may only
  downgrade to safe. Setup installs the finally proven hook scope, guard, shell-free broker, typed source adapter, and
  maintenance record before discovery. Safe mode instead verifies that `sre`/`observer` wrappers omit execute and
  installs no guard.
- **Installed updater:** setup atomically installs/hash-records itself and every helper under `~/.sre-agents/bin|lib`;
  the scheduler invokes an absolute preflight that verifies the installed updater hash. It never runs a mutable clone,
  workspace, or plugin-cache script. Python uses isolated/no-site/no-bytecode startup and sanitized environment.
- **Channel exclusivity:** setup proves the unselected plugin/fallback registration and any same-name workspace
  definitions are inactive before enabling the chosen source; `-Verify` rejects dual registration or ambiguous source.
- **Plugin channel:** additionally requires the proven adapter to identify the currently active root and verify exact
  version/SHA/runtime-tree contents, then prints the conscious Extensions trust step. A stale cache is not evidence.
  Before brokered plugin delivery is selectable, a real team client must also prove that the installed updater can
  noninteractively disable/unregister that active plugin and atomically activate/reload the preverified fallback-safe
  paths, with no duplicate definitions, and reverse the transition only after full requalification. Fixture-only
  switching cannot close this gate; if the real transition is unavailable, brokered plugin delivery is STOP.
- **Fallback channel:** installs the versioned exact-inventory tree above and changes JSONC settings only after runtime
  preparation. Comments/trailing commas are preserved by targeted edits, not `ConvertFrom-Json` rewriting.
- **Refresh transaction:** fetch/verify/stage under a lock. Remote skew, freshness expiry, plugin lag/ahead, client-version
  skew, or a partial fault switches/disables active discovery to the preverified no-execute recovery projection; plugin
  mode uses the separately acceptance-gated plugin-to-fallback-safe transition, while fallback switches versioned paths. A
  maintenance record alone is not protection if the client stopped invoking hooks. Only complete source/tree/runtime/
  updater/client convergence clears it. Safe mode still refreshes verified content, but its structural protection is
  execute omission.
- **JSONC hazard:** VS Code `settings.json` is **JSONC** — comments and trailing commas are legal. `ConvertFrom-Json`
  either fails or silently strips the engineer's comments on rewrite. Use a comment-tolerant parse + targeted key
  insertion, or instruct a manual paste and confirm with `-Verify`.
- **`setup.ps1 -Verify`** reports the bootstrap hash, channel, execution mode, full active-tree/version/SHA/freshness
  handshake, every protection field, installed updater/helper/interpreter/tool hashes, isolation state, distributed-hook
  emptiness, skills, auth, and probe skew. Brokered mode reruns boundary/liveness/current+nested-identity tests; safe mode
  reruns direct+nested execute-denial tests. Any failure exits nonzero. `setup.sh` is the POSIX behavioral twin.

**Rejected channels, with reasons pinned:**
- **VS Code Marketplace extension** (`chatAgents`/`chatSkills` contribution points): stable API, native auto-update — but `chatSkills` points at a single `SKILL.md`; skill folders with `references/`/`scripts/` are unsupported (microsoft/vscode **#304721**, open, assigned, no milestone). The redesign leans on references. **Revisit trigger: #304721 closes** and a private distribution channel exists.
- **Org-level agents** (`{org}/.github(-private)/agents`) and **enterprise-managed plugins**: solid mechanisms, wrong scope — this is a team, not an org, and both require org-admin control. Revisit if the org ever adopts the fleet. Org-level *skills* don't exist yet ("coming soon" per GitHub community discussion #189753).
- **`gh skill install`**: real and GA, but covers skills only and updates are manual per-engineer.

## Section 2 — Taxonomy: map the fleet onto Copilot's seven layers

Derivation rule: **each piece of the old fleet moves to the lowest layer that can carry it.**

| Copilot layer | What moves there |
|---|---|
| Canonical agents + generated wrappers | Only lanes with a distinct **tool scope**. Authors edit `canonical/fleet.json` + `canonical/agents/*.md`; Copilot consumes generated `.agent.md`, Claude consumes generated `.md`. |
| Agent skills | Playbooks, checklists, query patterns — auto-loaded by description or `/invoked` |
| Slash commands (`commands/`) | One-shot workflows (the `adr` scaffold; a Bamboo walkthrough if any migration remains) |
| Hooks | Portable files stay empty; Copilot gets a machine-local guard+broker only if the hostile-runtime viability gate passes, otherwise execute is omitted (Section 5) |
| MCP servers | Live tooling — a Grafana MCP server is the LGTM-exploration vehicle *(existence/fit: verify during implementation)* |
| Delegation + handoff projections | Canonical `delegates_to` maps to Copilot `agents:` and Claude `Agent(target)`; `handoffs:` is emitted for Copilot only. |
| Plugin | The distribution wrapper |

**Structural consequences:**
1. **AGENTS.md dies as always-on context.** Plugins don't inject ambient instructions into arbitrary repos — which force-ends the 3.3k-token tax. Each canonical agent body is self-contained and projected into both runtimes; the stack profile becomes a small **`stack-profile` skill** loaded on demand. The stay-in-lane rule lives *only* there, phrased as current fact ("runtime today: on-prem + TAS; GCP under evaluation late 2026"), so one file changes when the ground shifts.
2. **Read-only is intended to become structural.** An agent whose accepted runtime `tools:` projection omits `execute`/`edit` should be unable to run or write; the Phase-1 behavior probes must prove that omission fails closed before this becomes a fact. The hook guard survives only as an audit/deny layer on agents that genuinely need `execute`.

## Section 3 — The agent roster: 9 → 5

| Agent | Tools (GitHub alias vocabulary) | Lane | Chassis provenance |
|---|---|---|---|
| **sre** | read, search, execute*, web, **agent** (generated from delegation) | Triage, RCA, incident investigation | sre-agents `sre-engineer` method + sde-agents doctrine + **Tier 0–3 change authority** |
| **sde** | read, search, execute, edit, web, agent | Build/fix/refactor code and ops tooling; absorbs test-writing | **sde-agents `sde-fullstack`** (forks, checkpoint contracts, red-flags table, review packet w/ worked example) |
| **reviewer** | read, search **only** | Code + security review (two lenses, one tool scope) | **sde-agents `code-reviewer`** (`[caller-flagged]`/`[independent]` + mandatory independent-P0/P1 count; evidence gate; injection rule) + sre `security-reviewer` lens |
| **observer** | read, search, edit, execute*, **agent** (generated from delegation) | Obs-as-code: dashboards, alerts, SLOs; LGTM home | sre-agents `sre-monitor` + Tier 0–3 + "never cut the branch you're sitting on" |
| **scribe** | read, search, edit (**no execute**) | Runbooks + postmortems; documents commands from evidence, never runs them | sre-agents `runbook-author` modes + sde-agents `runbook` leanness |

### Tool and schema mappings are runtime-specific and acceptance-gated

The table shows the expected **Copilot projection**. Canonical capabilities are `read`/`search`/`execute`/`edit`/`web` plus a separate `delegates_to` graph; authors do not hand-grant `agent`. The generator
owns the mapping to each runtime's accepted syntax; authors never copy one runtime's frontmatter into the other.
`execute*` is conditional: Task 38 retains it in Copilot only if the hostile-runtime broker gate passes; otherwise it
is omitted. Claude omits execute for these two agents in this design. The selected `execution_mode` is canonical and
drift-tested, so safety cannot depend on an installer's memory.
Every generated agent has an explicit `name`. For Copilot, a nonempty canonical `delegates_to` list emits both
`agents:` and the `agent` tool automatically; generation fails if those could drift. Phase 1 pins the exact Copilot
tool spellings only after the nonempty native-plugin and fallback spike passes read, search, execute-denial, and
delegation assertions. If an unknown or omitted tool fails open, stop and amend Section 5 before any fleet agent is
authored.

### The delegation graph (was unspecified — Phase 1 cannot start without it)

Canonical `delegates_to` is the graph. In the Copilot projection it becomes `agents:` plus the required `agent` tool;
canonical handoffs become Copilot `handoffs:` buttons. In the Claude projection each edge becomes `Agent(target)` in
`tools`, and handoffs are omitted because they are Copilot-only UI. Claude's restriction is weaker for nested
delegators: `Agent(target)` restricts types when the definition is launched as the main `--agent`, but current Claude
Code ignores the parenthesized target list when that definition is itself a nested subagent. The projection and
compatibility report must label that degradation; terminal agents remain terminal by omitting `Agent` entirely.
Default-deny claims are runtime claims and stay `[unverified]` until the matching Phase-1 probe proves them.

| Agent | `agents:` (may delegate to) | `handoffs:` (human-clickable) |
|---|---|---|
| **sre** | `observer` (pull a dashboard/alert), `scribe` (read an existing runbook) | → `scribe` *"write this up"* (investigate→document) · → `sde` *"fix the root cause"* |
| **sde** | `reviewer` (pre-merge self-check) | → `reviewer` *"review this diff"* · → `scribe` *"document the new ops steps"* |
| **reviewer** | *(none — it is terminal and read-only)* | → `sde` *"apply these findings"* |
| **observer** | `scribe` (link the runbook a new alert requires) | → `sre` *"this signal is now an incident"* · → `scribe` *"runbook for this alert"* |
| **scribe** | *(none)* | → `sde` *"automate this instead of documenting it"* |

No other edges. `reviewer` and `scribe` deliberately delegate to nobody: a read-only reviewer that can spawn a
write-capable agent is not read-only, and that is the "delegation is not isolation" rule the old fleet learned the
hard way (see `docs/AUDIT-2026-07-12.md`, Tier 4).

### Model policy is projected per runtime

The canonical manifest records runtime-specific model policy, not one polymorphic `model:` value. Copilot receives a
prioritized array such as `['Claude Sonnet 5 (copilot)', 'Claude Opus 4.8 (copilot)', 'GPT-5.4 (copilot)']`; Claude
receives one Claude-valid model value or omits `model` to inherit the session. A Copilot display-name array must never
be copied into a Claude wrapper. **Selection rule** (so this survives lineup churn): Copilot primary = the strongest
Claude model exposed in the team's picker at ship time; final fallback = the org's default non-Claude model. The
chosen policy is recorded once in canonical data and summarized in `stack-profile`, not hand-copied into five files.

**Timing (the model check is free, and earlier than Phase 5).** Agents are authored in Phase 1 but model availability
is formally checked in Phase 5 — which sounds like a hole and is not: the array is a *prioritized fallback*, so an
unavailable model degrades to the next entry rather than failing. In practice you learn the answer in Phase 1 for
nothing: **loading the first agent shows you which model it actually picked.** Phase 5 only confirms it for the whole
team under their license tier.

Every agent also gets the uniform **doctrine layer**: `[verified]/[sourced]/[unverified]` labeling, an output packet
**with a worked example**, "recommend better, never silently substitute," "ask the forks, assume the details."

### `stack-profile` must actually load — or the stay-in-lane rule silently dies

Today "do **not** suggest Kubernetes / cloud-managed services; escalate platform-internal problems" is **always-on**
(AGENTS.md). Moving it into an on-demand skill removes that guarantee, and the failure is invisible until an SRE is
told to use Kubernetes. Two mechanisms, both required:
1. **Every agent body carries one line:** *"Before recommending a runtime, tool, or infrastructure change, load
   `stack-profile`."*
2. **A canary probe** whose prompt invites an off-stack recommendation and asserts the skill loaded. It is in the
   canary set built in Phase 4 alongside the other content probes — but it is a **required** canary, not an optional one:
   an unloaded `stack-profile` is a silent correctness regression, so the Acceptance bar (Section 8) fails without it.

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
| obs-traces | "follow one request" (new capability — **NEW**, no SRE feeder) | TraceQL; OTel *trace semantics* (span/attr conventions) | — |
| obs-dashboards | Grafana 13.x as code | provisioning; legacy Wavefront | — |
| obs-alerting | alert, correlate, page | Grafana unified alerting; SLO burn-rate (script survives); Moogsoft; ThousandEyes | — |
| obs-pipeline | what ships telemetry where | Alloy, collectors; OTel *instrumentation/SDK* (from instrument-service) | GCP exporters |

Boundary note: `frontend-craft/references/data-viz.md` owns **product-UI charts** (Recharts/uPlot); `obs-dashboards` owns **Grafana**. Stated in both descriptions so they never compete.

**Full skill roster** (provenance: SRE = sre-agents, SDE = sde-agents, NEW):

| Skill | Provenance / notes |
|---|---|
| stack-profile | NEW — the single stack-definition point; current-fact phrasing |
| obs-logs, obs-metrics, obs-dashboards, obs-alerting, obs-pipeline | SRE content restructured; LGTM references NEW |
| obs-traces | **NEW** — no SRE feeder (the old fleet had no tracing skill) |
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
| ci-actions | SRE `github-actions-ci`, `cf auth` argv leak fixed. Bamboo content: **default delete** (recoverable from git); becomes a prompt file only if live migrations remain — confirmed in **Phase 2** (an earlier draft said Phase 3, which no longer exists) |
| database-reliability | SRE |
| agent-authoring | SDE `prompt-craft`/`prompt-engineer` method + SRE `agent-authoring`; references absorb tool-design, context-engineering, multi-agent-architect's "should this be multi-agent at all?"; teaches **personal-first, promote-by-PR** and compose-with-fleet-agents |
| agent-security | SRE, rewritten Copilot-native (tool-scope containment) — ships because teammates *will* build their own agents |

Prompt files: `adr` (scaffold). The complete fate of every existing unit is the **Disposition ledger** (appendix at the end of this document); the implementation plan turns that ledger into dependency-ordered tasks.

## Section 5 — Safety model

1. **Primary control, conditional on the Phase-1 runtime gate: `tools:` omission.** The intended contract is that reviewer and scribe cannot execute and scribe cannot run what it documents. Treat that as `[unverified]` until the native-plugin, fallback, and Claude denial probes each pass for their own projection; if omission fails open anywhere, stop and amend this safety model before authoring the fleet. The same omission is the mandatory fallback for `sre` and `observer`: Phase 4 may retain their Copilot execute tool only after the execution-boundary viability gate passes through **both** native-plugin and fallback delivery in a hostile workspace, and Phase 5 requalifies the selected channel on a team client's real policy before setup. That later gate may only downgrade brokered to safe. Their Claude projections omit execute; this design does not claim a non-managed Claude hook can survive project-level hook disabling.
**The VS Code hook contract differs from Claude Code — do not port the exit codes.** VS Code: **exit 0 means stdout is parsed as JSON** (`permissionDecision`: `allow` | `deny` | `ask`); **exit 2 is a blocking error**; other codes are non-blocking warnings; and **"most restrictive wins"** among hooks that actually run *[verified: hooks reference, fetched 2026-07-14]*. The sister repo's 42/43 outcomes may survive only as an internal guard-to-launcher protocol explicitly mapped to VS Code output. The outer boundary comes first: VS Code also documents workspace-hook precedence and configurable hook locations, and no launcher can emit deny if VS Code never starts it. Therefore a user-hook smoke test is not an enforcement proof. Phase 4 must show that an agent-scoped hook—or managed scope proven to invoke only for source-qualified fleet definitions—cannot be suppressed by hostile workspace hooks/settings, that same-name workspace definitions cannot impersonate it, that an outer spawn failure blocks, and that `updatedInput` is applied exactly. A global hook that sees unrelated sessions fails the non-fleet contract. Any failure selects safe mode (`execute` omitted); it never degrades silently to audit-only.

2. **The hook + broker — allowlist doctrine without shell-name theater.** *"Enumerating the ways a command can write is unbounded and always a step behind; enumerating what an agent needs is bounded, knowable, and fails loud."* The sister guard is evidence and a regression corpus, not a parser to copy: its POSIX `shlex` model accepts PowerShell array subexpressions, and its name-only reader bucket admits execution/write flags. In brokered mode, the guard strictly parses JSON and a tiny cross-platform token grammar, identifies the **current nested agent**, applies a positive per-command argv grammar, and replaces tool input with one absolute installed broker plus a base64url argv payload. The broker revalidates, verifies absolute tool hashes, strips helper/config/Python-startup environment, and calls an argv array with `shell=False`. It never resolves PATH, aliases, functions, pagers, preprocessors, compressors, external diffs, or terminal profiles. Any inability to prove this exact transformation selects safe mode.

3. **Installed/runtime integrity.** The portable hook files remain empty. In brokered mode setup installs the guard, broker, renderer/updater helpers, and runtime record under `~/.sre-agents/`; Python runs isolated/no-site/no-bytecode. The generated runtime-tree manifest inventories and hashes every active agent/skill/reference/asset/script/command/hook/manifest file and rejects unexpected default-discovery content. Every execute decision checks that tree—not just Git HEAD—plus fleet version, protected `release` SHA, installed component/tool hashes, and a successful protected fetch no older than 26 hours. Once the proven outer executor starts, missing/tampered state, audit I/O failure, source/tree/freshness skew, or an unexpected internal outcome denies every invocation within the fleet scope. If the client or outer executor drifts so the hook might not start, the updater atomically disables brokered discovery or selects the preinstalled safe-recovery projection; if that transition cannot be proved, fleet discovery stays disabled. If the outer executor itself cannot be made blocking when absent, brokered mode is unavailable.
4. **Change authority: Tier 0–3** (observe / prepare / reversible-live / destructive-or-access-path), imported from sde-agents `homelab-platform`: classify before acting; approval covers only the commands shown; a material change re-enters the gate; independent Tier 0/1 work continues while approval pends; worked approval-request example (target, diff, exact command, blast radius, verification, rollback). Woven into sre + observer bodies and production-change-gate.
5. **Prod boundary unchanged:** GitHub branch protection + protected environments, with the gate's `gh api …/protection` check. The verifier checks required review count, Code Owner review, the exact Gate-A context, `enforce_admins`, and force-push/deletion prohibitions; one `enforce_admins` boolean is not the whole control.

### 5a. The allowlist, actually enumerated (doctrine is not a list)

Importing "allowlist, not denylist" without writing the list leaves the builder to invent the guard. **Conditionally
brokered: `sre` and `observer`; otherwise both are safe-mode/no-execute.** **`sde` is unguarded by design** — it holds `all` tools and its whole job is running builds
and tests; a guard there would be theater. That is a **trust decision, stated**: `sde` is for code the team authored
(the untrusted-diff refusal rule from the audit's Tier 4 lives in its body).

| Agent | Allowed (seed set — Phase 4 finalizes against real use) |
|---|---|
| **sre** | `cf` read verbs (`app`, `apps`, `events`, `logs`, `curl`-free), `git log/diff/show/blame/status`, `gh run/pr view|list`, `rg`/`grep`, `ls`/`cat`/`head`/`find`, `jq`, `dig`, display-only `ss` |
| **observer** | (`sre` set **minus** `dig` and `ss`) **plus** config validators it genuinely needs (`promtool check`, `jq empty`, `grafana` CLI lint). `dig` is removed because observer has no web egress but an allowlisted DNS query would recreate it; `ss` is not needed in observer's steady-state lane. The audit proved the old guard denied the validators, which is why `sre-monitor` could never take it. |

Each table cell is shorthand for a positive argv grammar plus an absolute hash-pinned binary, never permission by
executable name. Unknown flags/actions deny. Required regression denials include `rg --pre/--search-zip`, Git pagers/
external diffs/textconv/helpers, every `find` exec/delete/file-output action, output/compile/interactive reader modes,
and `ss --kill/--diag`. Everything else is denied, including all interpreters, local scripts, and build/test runners.
`cf env` stays denied (it leaks credentials to an agent with egress). A blocked read is loud; a missed helper is silent.

### 5b. Precedence when trust or agent identity is indeterminate

The spec promises both *fail closed* and *never touch non-fleet sessions*. Those guarantees apply at distinct layers:

1. **Hook discovery + outer spawn are a go/no-go gate, not launcher logic.** Both native-plugin and fallback delivery
   are tested against hostile workspace precedence/location settings, plain non-fleet sessions, and an absent outer
   executable. If either delivery path can skip/non-block the guard or cannot distinguish fleet scope from a missing
   identity, execute is removed. Code that never starts cannot manufacture a deny response.
2. **After the proven outer executor starts but before Python parses input, fail closed for every invocation inside the
   fleet-only hook scope.** A missing/tampered runtime, interpreter, guard, broker, hash utility, active-tree/source/
   freshness mismatch, or unflushable audit sink produces the runtime deny result without matching identity in raw
   stdin. Unrelated sessions never enter this scope; a global managed hook cannot satisfy this design.
3. **After strict Python starts but before identity scoping, malformed/duplicate-key/wrong-typed JSON denies.** This is
   parser rejection, not a shell-preflight claim.
4. **After integrity and strict parsing succeed, preserve only positively identified non-fleet sessions.** An explicit,
   structurally valid non-fleet identity is a no-op. Inside the proven fleet hook scope, a missing or renamed identity
   is contract drift: append and flush `identity-missing`, atomically enter maintenance-deny, and deny the command.
   `setup -Verify` exits non-zero and the client payload must be requalified before maintenance can clear. If the runtime
   cannot distinguish an ordinary non-fleet session from that condition, brokered mode fails its Step-1 viability gate.

Thus explicit non-fleet identity is no-op-after-parse; missing fleet identity, parser ambiguity, and post-launch
integrity failure deny; and an unshadowable/blocking outer boundary is a prerequisite. None is implemented by
raw-string matching.

### 5c. `web` is egress, and the new `sre` agent holds the full trifecta

The old fleet documented this and refused to hide it; the redesign must not regress it. In brokered mode, `sre` =
`read` (repo/secrets) + untrusted input (logs, PR bodies, alert payloads) + brokered `execute` + **`web`** — all three
legs, and `web` is an egress channel **the broker cannot see** (it governs commands, not tool calls). In safe mode the
execute leg is absent. Deleting `researcher` for holding "the widest
egress" and then handing `web` to `sre` without saying so would be exactly the drift the audit condemned.

**Decision (recommend, owner may overrule): keep `web` on `sre`, contain it at the boundary.** Rationale: an SRE mid-
incident genuinely needs to look up a vendor status page or an error code, and routing that through a human is a real
cost at 3am. Containment is the **outbound network allowlist** (the load-bearing control, unchanged from the old
fleet) plus the trifecta note in the agent body. **The alternative** — strip `web` from `sre`, look-ups go to the human
— is one line to apply if you'd rather not carry the risk. Either way it is now *recorded*, not silent.
5. **Probed, not assumed—and no live brokered auto-upgrade.** Platform facts the safety model rests on get re-run through both delivery paths after every VS Code/Copilot upgrade. Brokered mode requires the exact client/extension versions to be managed and pinned with automatic updates blocked; if that cannot be enforced, safe mode is mandatory. The upgrade procedure first switches/disables brokered discovery and proves the safe projection while the old client still runs, then updates and requalifies before restoring brokered mode. The list includes payload/tool fields; current direct+nested/source-qualified identity; same-name workspace collisions; hostile workspace/settings and hook-disable precedence; fleet-invocation-scoped hook behavior; outer spawn failure; exact `updatedInput`; PowerShell/cmd/POSIX parsing; terminal PATH/profile/environment poisoning; active plugin root/tree and fallback installed tree; plugin/fallback skill and agent loading; distributed-hook emptiness; and `disable-model-invocation`. A scheduled maintenance record is not credited as protection after a client stops invoking the hook.

## Section 5d — Reference files: the pattern is right for Claude Code and BROKEN for VS Code

The whole design leans on progressive disclosure — 26 lean skills whose depth lives in `references/`, loaded on
demand. It is why we rejected the Marketplace-extension channel (it cannot ship skill folders). So the mechanism has
to actually work, and **as imported, it would not.**

**The rule.** VS Code loads bundled files in three levels — name+description, then the `SKILL.md` body, then
*"as Copilot works through the instructions, it accesses additional files"* — and pointers must use
**Markdown link syntax with relative paths**, e.g. `[test template](./test-template.js)`. The doc is blunt about the
failure mode: **"If a file isn't referenced in the instructions, it won't be loaded."**
*[verified: code.visualstudio.com/docs/agent-customization/agent-skills, fetched 2026-07-13]*

**What we were about to ship.** Both source fleets point at bundled files with **bare code-spans**, not links:

| Repo | Markdown links | Bare code-spans |
|---|---|---|
| `sde-agents` (the harvest source) | 3 | **19** |
| old `sre-agents` fleet | 21 | **26** (14 skills affected) |

`frontend-craft`'s predicate table — the exact mechanism the six observability skills copy — is entirely
code-spans: `` | a form or any user input to submit | `references/forms.md` | ``. **In Claude Code that works**, because
the model simply calls Read on the path. **In VS Code the file is never loaded at all**, and the failure is *silent*:
the model answers from memory of what `forms.md` probably says. That is precisely the failure sde-agents' own
doctrine-alignment spec diagnosed — *"every branch is a chance to skip the read, hallucinate it, or answer from
memory"* — reproduced in a runtime where it is worse, because the file is not merely un-read but un-loaded.

**This is the one place the verbatim-move discipline must NOT apply.** Section 7 tells the porter to relocate prose
unchanged, precisely to avoid transcription drift. Reference *pointers* are the stated exception: **every bundled-file
pointer is rewritten to Markdown-link syntax during the move.** A verbatim port would faithfully preserve the bug.

**Rules for every skill in the new fleet:**
1. **Every** pointer to `references/`, `assets/`, or `scripts/` is a **relative Markdown link**:
   `[forms](./references/forms.md)`, never `` `references/forms.md` ``.
2. **Predicate tables keep their shape**, but the right-hand cell becomes a link:
   `| a form or any user input to submit | [forms](./references/forms.md) |`
3. **Every bundled file is linked from the body.** An unlinked file is dead weight that never loads — so if it
   isn't worth linking, delete it.
4. **The skill body names the trip condition and orders the read**: *"read it **before** writing that code, and name
   what you read in your packet."* Progressive disclosure is not just "the file exists"; the model must be told when
   to open it and be held to having done so.

**Validator v2 enforces this (new rules, both errors — not warnings):**
- A bundled-file path appearing as a **code-span rather than a link** in a `SKILL.md` body → **error**. This is the
  rule that would have caught the bug above, and no existing validator has it: sde-agents' validator existence-checks
  reference links but never their *syntax*, because in Claude Code the syntax does not matter.
- A **linked file that does not exist** → error (existence check, imported).
- A **bundled file that nothing links to** → error (it can never load).

**And a probe (Phase 4), because the validator only proves the link is well-formed:** trip a predicate and assert the
reference was actually read — sde-agents does this for exactly one of its eleven routing rows and openly flags the
other ten as unverified. In the new fleet **every predicate row gets a canary**: a distinctive string in each
reference file, asserted to appear when its condition trips. That is the only thing that distinguishes "the model read
the file" from "the model guessed what was in it."

## Section 6 — Validation & maintenance machinery

- **Validator + generator drift gate:** validate the canonical schema first, then both generated projections. Reject unknown canonical keys; missing/duplicate/non-kebab explicit names; dangling delegation/handoff targets; a Copilot `agents:` list without `agent`; Claude delegation not mapped to `Agent(target)`; Copilot handoffs leaked into Claude; runtime-invalid model shapes; manifest name/version skew; manifest agent-path shape drift (Copilot directory versus Claude explicit files); wrapper body drift; and stale/unexpected generated files. Also retain description trigger lint, bundle-reference existence, schema-vs-policy separation, doctrine checks, and `--write-inventory`. Hook checks are runtime-specific: root `hooks.json` and `hooks/hooks.json` are auto-discovered and must not appear in either manifest. Broken-fleet fixtures cover both schemas. Platform evidence also stays split: Claude strict validation validates Claude only; native Copilot plugin and fallback probes validate Copilot.
- **Canonical skill inventory:** require exact parity between the canonical runtime-visible skill/bundled-file inventory and the filesystem, and require every agent skill dependency to resolve to an inventoried skill. Missing and unexpected entries fail before content linting.
- **Routing evals** (sde-agents format + sre-agents clean-room rig): overlap clusters, positives + **near-miss negatives** ("shares vocabulary, should route elsewhere"), graded deterministically off transcripts, reported as **rates over runs**, cases phrased to measure routing without spawning long sessions. Two refinements from the completion sweep: **negatives are cross-cluster positives**, and routing evals run **manually, before/after description edits — never as a CI gate**. A Claude run measures the generated Claude projection only. Copilot routing evidence is gathered separately in native Copilot; neither result is labeled a proxy for the other.
- **Behavioral probes with canary strings** (plant a distinctive string in a skill; its appearance in output proves loading) + **tripwire tests guarding the canaries** (an innocent copy-edit would silently disarm the oracle).
- **Execution-boundary tests** first decide brokered versus safe mode in real VS Code and run through both native-plugin and fallback delivery. Brokered mode must survive hostile workspace/settings precedence, hook-disable attempts, nested identity, missing/renamed-identity maintenance denial, conflicting allows, outer-spawn failure, poisoned terminal/Python environment, PowerShell/cmd/POSIX syntax, and exact `updatedInput` transport. Unit/wiring suites then test strict JSON, per-command argv grammars, shell-free absolute broker execution, durable audit failures, runtime-tree/source/freshness skew, path injection, and installed updater transactions. Safe mode instead proves execute omission directly and when nested. Distributed hooks remain empty; no Claude guard is inferred from Copilot evidence.
- **CI**: the restored workflow extends to the new validator + tests. Anti-rot rule from the audit, now doctrine: **a skill never transcribes an artifact that lives in the repo — point at it.**

## Section 7 — Migration plan (phases; each independently valuable)

> **Ordering rule: prove the cross-runtime boundary once, then build the product content-first.**
> The format spike is not a standalone phase or an empty scaffold. It is a blocking, nonempty Phase-1 acceptance gate
> containing an agent, a delegated terminal agent, a shared skill/reference, and an inert hook. It must pass native
> Copilot plugin discovery, Copilot fallback discovery, and Claude Code separately before any fleet agent is authored.
> Its result is the canonical-manifest/two-projection architecture in Section 1; Claude output is never Copilot
> evidence. After that boundary is fixed, content still precedes the machinery that protects it: canaries, routing
> evals, the selected execution boundary, and validator v2 are written against artifacts that exist. The positive
> command grammar for a brokered candidate—or the evidence that safe-mode omission is required—is only knowable after
> observing `sre` and `observer` work.
> Content also carries standalone value: if distribution turns out policy-blocked, a finished fleet still ships via
> the fallback channel. A finished validator with no fleet is worth nothing.

**Phase 1 — THE AGENTS (5).** The first phase, and the first one that produces the product.

*Opens with the scaffolding, which is minutes of work, not a phase of its own:*
- `canonical/fleet.json`, empty `canonical/agents/`, `generated/{copilot,claude}/agents/`, root `plugin.json`, and `.claude-plugin/plugin.json`. Both manifests are generated from canonical metadata and drift-checked. Empty `agents` and `commands` arrays suppress those default discovery paths; an explicit empty `skills` array is only a schema marker for Claude, whose additive default `skills/` scan is controlled by exact empty-tree inventory. Once populated, root Copilot points at the Copilot agent/command directories, Claude enumerates explicit Claude agent/command files, and both register the shared `skills/` tree. Add shared `skills/`, `commands/`, root `hooks.json`, `hooks/hooks.json`, `.mcp.json`, and `.claude-plugin/marketplace.json`. The generator owns and drift-checks both empty hook projections; the runtimes auto-discover them, so they are never manifest entries. Phase 4 adds the always-no-execute `generated/copilot-safe/` recovery variant and runtime-tree manifest, then chooses safe mode or a brokered candidate; Phase 5 installs the safe recovery plus only the selected active runtime.
- **`git mv .claude/{agents,skills} legacy/claude-fleet/`** — *not cosmetic.* VS Code discovers skills from
  `.claude/skills/` **in any open workspace**, so leaving the old fleet in place means anyone opening this repo
  double-loads **37 old + 26 new** skills — the exact routing confusion the redesign exists to kill, at its worst
  during the phases used to judge whether it worked. Frozen, not deleted (git-recoverable). The
  `.claude-plugin/plugin.json` keeps the generated Claude projection loadable in Claude Code (`--plugin-dir .`),
  while root `plugin.json` and fallback settings load the generated Copilot projection.
- **`cp AGENTS.md CLAUDE.md legacy/claude-fleet/`** — **the root docs must be preserved *beside* the fleet, not left
  to git archaeology.** They sit at the repo root, so the `git mv` above does *not* capture them, and both are
  slated for rewrite-in-place (Appendix 2). But they carry content the new agent bodies must **absorb, not lose**:
  the stack profile, the roster and routing tables, the read-only-agent doctrine, the egress/trifecta census, the
  gate layering, and the shared conventions. A rewrite that silently drops them is exactly the failure this
  redesign exists to prevent. **Phases 1–3 mine `legacy/claude-fleet/AGENTS.md` while authoring; the rewrite of the
  live `AGENTS.md` happens last, once its content has a new home.**

*Then the five agents* — canonical sde-agents-derived bodies + doctrine layer, projected through the delegation, tool,
handoff, and model rules in Section 3. Generated wrappers are never authoring surfaces.

**The nonempty format gate runs before the first fleet agent.** Its coordinator/worker pair must exercise four
assertions in each applicable runtime. "It couldn't run a command" is **not** a pass on its own: that is equally
consistent with the vocabulary being wrong and the agent getting **nothing at all**.

| # | Assertion | If it fails |
|---|---|---|
| 1 | terminal worker **can read** the linked reference | grants or shared-skill paths are not landing. **Stop.** |
| 2 | coordinator **can delegate** to the named worker | runtime mapping is wrong (`agent` + `agents:` for Copilot; `Agent(worker)` for Claude). **Stop.** |
| 3 | terminal worker **cannot run a shell command** | omission fails **open**, so read-only-by-absence is dead. **Stop and amend Section 5.** |
| 4 | terminal worker **cannot delegate** | terminal omission fails **open**; the read-only model is decorative. **Stop.** |

Assertion 4 exists because this spec refuses to infer default-deny behavior from schema shape. Claude's nested
target-list degradation is recorded separately and is not misreported as an exact nested allowlist.

**Where it runs.** Record three independent evidence packets: (1) native Copilot loads root `plugin.json`, the
coordinator delegates, the skill/reference marker appears, and root `hooks.json` fires; (2) fallback settings load
`generated/copilot/agents/` + `skills/` and the same agent/skill behavior passes, with the fallback hook registered
through its documented channel; (3) `claude plugin validate . --strict` plus a Claude CLI run loads the explicit
Claude wrappers, delegates, reads the shared reference, and observes `hooks/hooks.json`. A Claude pass cannot close
either Copilot row, and a fallback pass cannot close native-plugin discovery.

**Done when:** the spike's three evidence packets are green, generation is drift-clean, and the five agents load and
work against a real repo through the native Copilot plugin and fallback projection; the Claude projection also loads
through `--plugin-dir .` as its own supported runtime.
**The fleet is test-usable here only in the sacrificial fleet-development checkout**, unguarded — and using it there
teaches Phase 4 the candidate broker grammar and canary prompts. It is not opened in production or an untrusted repo;
Phase 4 either establishes a brokered candidate or removes execute; Phase 5 requalifies the chosen channel on a team
client and can only downgrade before distribution.

**Phase 2 — THE SKILLS (harvest + fix).** Direct imports (root-cause, eng-ladder, runbook, backend/frontend-craft,
ops-tooling) → SRE domain skills **with the audit's Tier-2 fixes applied — blue-green name rotation, the WQL `by`
deletion, SPL `timechart` bucketing, `cf auth` argv, error_budget severity, Grafana licence notes. Every fix is
specified in [`docs/AUDIT-2026-07-12.md`](../../AUDIT-2026-07-12.md); none may be ported as-is.** Confirm the Bamboo
decision, and the `adr` home (if plugins can't ship prompt files, `adr` becomes a skill — a one-line disposition
change, not a design change).

**Phase 3 — THE OBSERVABILITY SKILLS.** Six by-signal skills; LGTM references written; legacy references carried over
post-fact-check. **End of Phase 3 the fleet is content-complete:** 5 agents, 26 skills, working.

**Phase 4 — Machinery** *(written against artifacts that exist, and against usage observed in Phases 1–3 — no churn)*:
validator v2 · the hostile-runtime execution viability gate · safe-mode omission **or** strict guard + shell-free absolute
command broker with bounded argv grammars · runtime-tree/freshness checks · canary/tripwire probes · routing evals · CI.
The payload, nested identity, workspace precedence, outer spawn, updated-input, and terminal-shell facts are probed here.

**Phase 5 — Distribution** *(and only here do the org gates matter — they decide which Copilot channel delivers the
same generated Copilot projection, never the canonical content)*:
- **The three gate checks**, on one engineer's machine: `chat.plugins.enabled` flippable, or policy-blocked? The
  Copilot org **"Editor preview features"** policy? Are the named Claude **models** selectable under the team's
  license tier? *(Whatever the answers, the fleet built above still ships — plugin channel or fallback.)*
- **A separate plugin-safety prerequisite:** prove that setup can read the currently active plugin's manifest version
  protected SHA + full runtime tree, not merely find a stale cache. Without that fingerprint, plugin delivery is STOP and
  fallback is used. Both channels update only through serialized installed `setup --refresh`.
- Land wildcard CODEOWNERS + full ruleset on reviewed `main`; then create protected `release` once at that exact green
  Phase-5 SHA (`0.9.0`), publish bootstrap hashes, and run the first real setup/Verify. The branch does not predate setup.
- `setup.ps1|sh`, deterministic refresh tests, README, and rollback runbook (Section 1).

**Phase 6 — Pilot:** one engineer, real work repos. Exit only on the Acceptance bar (Section 8) — not "fix what
reality finds."

**Phase 7 — Team rollout** (promote reviewed `1.0.0` from `main` → existing `release`), then retire `legacy/claude-fleet/` and the owner's personal
`~/.claude` duplicates (`root-cause`, `eng-ladder`, `runbook` — the shadowing the clean-room rig diagnosed).

### Routing evidence is runtime-specific

The existing harness shells out to `claude -p` and reads `Skill(...)` events. It remains useful, but it measures the
generated **Claude projection only**. It is not a Copilot proxy and cannot close a Copilot acceptance row. Copilot
routing and reference-read cases run through native Copilot (manual while no documented headless interface exists),
using the same case corpus where semantics match. Reports keep the runtime in every result and never combine the two
rates. Agent-level cases target the matching generated wrappers; per-case dispositions remain explicit.

**Migration ordering rule** (imported): fix internal contradictions first — the one class of change needing no behavioral baseline.

**Implementation-plan format** (imported from sde-agents' plan doc, found in the completion sweep): dependency-ordered tasks with explicit **Interfaces** between them ("Task 5's probe asserts this path — do not rename it"); a **Global Constraints** block carrying machine-specific gotchas (on this machine: **Python is `py -3`, not `python3`** — bakes into setup.ps1, the validator shebang strategy, and CI matrix); **verbatim-move discipline** for content relocations (the plan names the section to move, never re-types it — re-typing invites silent transcription drift), **with one stated exception: bundled-file pointers are rewritten to Markdown-link syntax (Section 5d), because a verbatim port would faithfully preserve a bug that silently breaks every reference in VS Code**; and probes/tests written **first and failing** before the change that makes them pass — **scoped to the artifact under change.** That discipline governs each phase's *internal* task order (write the failing canary, then the skill); it does **not** mean writing the whole test suite before the whole fleet, which is the loop the ordering rule above forecloses.

## Section 8 — Acceptance: how we know it worked

The problem was quantified; success must be too. Without a bar, Phase 6 can't end and Phase 7 is a judgment call
dressed as a milestone — and "silent dark skills" (Risk 3) goes unmeasured, which is precisely how the old fleet rotted.

| Dimension | Bar | How measured |
|---|---|---|
| **Format boundary** | native Copilot plugin, Copilot fallback, and Claude Code each load the nonempty coordinator/worker + shared skill/reference + inert hook; generated files are drift-clean | three separately labeled Phase-1 evidence packets; **no runtime is a proxy for another** |
| **No dark skills** | **0 of 24 model-invocable skills** fail to fire on their own on-target prompt | discovery canary per skill |
| **Side-effect skills load when called** | `pcf-deploy` and `service-onboarding` (both `disable-model-invocation`) load via `/sre-agents:<name>` and their canary appears | **invocation** canary. By design they *cannot* fire on a prompt, so a discovery bar over all 26 would be unsatisfiable and Phase 6 could never exit. |
| **Routing precision** | no near-miss negative fires **at all**; positives ≥ old-fleet clean-room baseline | cluster routing evals, rates over runs |
| **Fan-out** | a single incident prompt loads **≤ 2** fleet skills | routing eval with a `max_skills` assertion (the old fleet loaded **6**) |
| **Always-on context** | **≤ 4.5k tokens** before any work (was ~8.3k) — and **≤ 150 tokens per description**, so it cannot creep | measured in a real Copilot session |
| **Execution boundary** | brokered mode: 0 unresolved false denies, 0 silent boundary/load failures, freshness ≤26h; safe mode: direct + nested execute denial | `setup -Verify`, native-plugin + fallback hostile-workspace probes, broker audit/runtime tree; or structural tool-omission probes. |
| **Pilot exit** | one engineer, **one week** touching **≥ 3 agents**, no unrecovered routing failure; brokered mode has no unresolved false deny, safe mode has no execute exposure | pilot log |
| **Rollout safety** | any acceptance regression in week one → **revert `release`**, team announce | Section 1 rollback runbook |

**The token bar, honestly (an earlier draft said ≤3k, which this design makes impossible).** The always-on cost is
31 descriptions (26 skills + 5 agents) — and the discoverability fix *requires them to be longer*: verbatim user
phrasings plus boundary clauses are what makes a skill fire at all. Measured against the old fleet (37 descriptions,
avg 426 chars ≈ 106 tokens), 31 descriptions at the same length already cost ~3.3k, and with the added triggers
~4.0–4.6k. **So there is a real trade this design makes and must name: better routing costs context.** The structural
saving is not the descriptions — it is `AGENTS.md` + `CLAUDE.md` no longer being injected into every session
(−4.3k). Net ~8.3k → ~4.5k, a ~45% cut, with the routing failure mode fixed rather than traded away. A bar set below
what the roster can achieve would simply be ignored.

## Section 9 — Ownership and lifecycle

**Ownership.** The fleet needs a named maintainer — the person who gets pinged when an update breaks the team.
**OWNER DECISION, not a builder guess: CODEOWNERS, the README, and the rollback announcement all block on this name.**

**CODEOWNERS protects the whole repository by default:** `* @<maintainer>`. A path census cannot own a future root
`sitecustomize.py`, new workflow, dependency file, or default-discovery directory that does not exist yet. Optional
exceptions are allowed only after proving the path is neither execution, prompt, runtime, setup, nor gate input; the
initial design has none. This single rule includes canonical/generated artifacts, `.github/`, tests/evals/spikes,
dependencies, auto-loaded instructions, skills/references/assets/scripts, commands, hooks, manifests, and future files.

**Protection on `main` and `release` is a complete asserted contract:** required review count, Code Owner review, exact
Gate-A status context, administrators enforced/no bypass, force-push disabled, and deletion disabled. Setup and refresh
query every field. The marketplace pins a branch, so a partial ruleset or one checked boolean is not a security boundary.

**Contribution: personal-first, promote-by-PR.** Teammates build in `~/.copilot/{agents,skills}` (VS Code reads them
per-user, so this is free). When a second person wants one, it graduates into the fleet by PR. This is **repo policy in
CONTRIBUTING**, not merely content the `agent-authoring` skill teaches.

**Renames and version skew.** Installed setup checks protected `release` at least daily, while marketplace availability
can lag. Teammates can therefore be on different active versions during a bounded refresh window; in brokered mode,
remote skew or freshness beyond 26 hours atomically disables brokered discovery or switches to the verified
safe-recovery projection instead of leaving stale execute enabled. Maintenance-deny is sufficient only while the
proven fleet hook remains live. Consequence:
mid-incident, one teammate may temporarily be on `/incident-severity` while the runbook says `/incident-command`. Rules:
- A rename ships with a **one-release stub** at the old name whose description redirects to the new one.
- Renames on the **incident path** need a team ack before merge.
- The marketplace's `renames` map handles *plugin* renames automatically — **not skill renames**, which is why the
  stub is needed.
- Onboarding states the 26-hour freshness boundary explicitly. The installed `-Refresh`/`-Verify` path is authoritative;
  *Extensions: Check for Extension Updates* may accelerate plugin availability but cannot clear maintenance by itself.

## Glossary (terms this spec uses that are not self-evident)

- **Clean-room rig** — `evals/clean_room.py` (merged in PR #52). Runs an eval trial with `CLAUDE_CONFIG_DIR` relocated
  so the operator's personal `~/.claude` skills/agents/plugins can't compete with the fleet for discovery. It proved
  every pre-2026-07-13 baseline described *the laptop*, not the fleet — and that the contamination cut **both ways**
  (it suppressed `sde-ladder` and *flattered* `sre-ladder`).
- **Shadowing** — the above: a personal global skill out-competing a fleet skill of similar purpose.
- **The audit** — [`docs/AUDIT-2026-07-12.md`](../../AUDIT-2026-07-12.md). Five parallel reviewers, every load-bearing
  claim hand-reproduced. Source of every "audit fix" this spec names.
- **Dark skill** — a skill that never fires on its own on-target prompt (`saw: none` in a probe). The old fleet had four.
- **Trifecta / lethal trifecta** — an agent holding all three of: sensitive data · untrusted input · egress. Any one leg
  broken defeats a prompt injection. See Section 5c.
- **Ralph** — an unattended agent-loop pattern (`scripts/ralph-loop.sh`) the old `self-improve-loop` skill taught.
  Claude-Code-specific; deleted (Machinery ledger).
- **Canary / tripwire** — a distinctive string planted in a skill; its presence in a transcript proves the skill loaded.
  A *tripwire test* guards the canary so an innocent copy-edit can't silently disarm the probe.

## Explicitly deferred / out of scope

- GCP skills (trigger: onboarding becomes real → `references/gcp.md` additions)
- Extension packaging (trigger: #304721 closes + private channel exists)
- Enterprise-managed plugins / org-level anything (trigger: org adoption)
- Automated/headless Copilot routing measurement (native manual probes remain required; revisit if a documented CLI interface lands)
- Old-fleet content named **deleted** in either ledger (Appendix 1 = agents/skills, Appendix 2 = machinery). Nothing is dropped by silence — the catch-all is gone.

## Risks (ranked) and open questions

1. **Agent plugins are Preview** — format churn could break the team at once. Mitigations: one canonical model, generated/drift-checked runtime projections, native-plugin + fallback probes, and pinned plugin versions if churn appears.
2. **`chat.plugins.enabled` org-policy-blocked** — fallback channel consumes the same generated Copilot projection; checked in Phase 5, because it changes the channel and never the canonical content.
3. **No automated Copilot routing measurement** — native Copilot routing/canary runs remain manual and runtime-labeled. Claude runs cover Claude only; treating them as Copilot evidence is prohibited.
4. **Copilot's command/hook boundary may be unenforceable** — workspace precedence can suppress user hooks; outer spawn
   failure may be nonblocking; nested identity and PowerShell command strings are under-documented; an uncontrolled
   client update can stop invoking the guard while wrappers still expose execute. Phase 4 treats all of these as a
   viability gate and requires both a managed version pin and a real-client atomic plugin-to-fallback-safe recovery proof
   for brokered plugin mode. Failure is not audit-only: execute is omitted. If brokered mode passes, post-launch
   integrity/parser ambiguity denies before scope, while a well-formed missing fleet identity enters maintenance-deny
   with durable audit and makes `setup -Verify` fail. Section 5b defines the layer ordering.
5. **Reviewer merge could dilute security reviews** — watch review outputs during pilot; split is one file if needed.

## Provenance summary

- **sre-agents contributes:** domain content (PCF, obs queries, incident process, gates, DB reliability), the clean-room eval rig, the restored CI, the audit's factual fixes.
- **sde-agents contributes:** the agent chassis (reviewer/sde bodies), doctrine layer, allowlist philosophy/fixtures (not its name-only POSIX parser), Tier 0–3 change authority, service-onboard/lab-audit shapes, eng-ladder, root-cause, backend/frontend-craft, canary/tripwire patterns, routing evals, validator hardening, and "no second source of truth."
- **New:** plugin packaging, six by-signal obs skills, LGTM references, stack-profile, setup.ps1, Copilot-native validator/hook/probes.

## Appendix — Disposition ledger (every existing unit, old → new)

Verbs: **survives** (ported, possibly renamed/fixed) · **merges into** (content combined with another unit) · **reference under** (demoted to a `references/` file, loaded on demand) · **dissolves** (replaced by a native platform mechanism) · **deleted** (content dropped; recoverable from git history).

### Skills (37 → 26)

| Old skill | Disposition |
|---|---|
| adr-template | → **prompt file `adr`** (template asset kept) |
| agent-authoring | survives, rebuilt on the sde-agents method (prompt-craft/prompt-engineer) |
| agent-security | survives, rewritten Copilot-native; per-agent census dropped (anti-rot: point at `tools:` frontmatter, not prose) |
| api-design | → reference content under **backend-craft** (`references/stack.md` work rewrite; OpenAPI asset rides along) |
| bamboo-to-actions-migration | **deleted** (default; prompt file only if live migrations remain — Phase 3 confirms) |
| blameless-postmortem | survives as **postmortem** (renamed) |
| context-engineering | → reference under **agent-authoring** |
| craft | survives as-is (per-language references) + gains process references from safe-refactor/tdd-workflow |
| database-reliability | survives |
| debug-rca | **replaced by root-cause** (sde-agents; measured routing winner) |
| github-actions-ci | survives as **ci-actions** (`cf auth` argv leak fixed) |
| grafana-dashboards | merges into **obs-dashboards** (Grafana 13 rewrite; Enterprise-plugin licensing facts added) |
| handoff-protocol | **dissolves** → `handoffs:` frontmatter + packet templates in agent bodies (SHA-pinning + taint doctrine woven in) |
| incident-severity | survives as **incident-command** |
| instrument-service | → OTel reference under **obs-pipeline** |
| merge-gate | survives (AGENTS.md-duplication cut; severity rubric added per audit) |
| moogsoft-correlation | → reference under **obs-alerting** |
| ops-cli | → CLI reference under **ops-tooling** |
| ops-stack-integration | → reference content under **backend-craft** (`consuming-apis` + stack) |
| pcf-deploy | survives (blue-green name-rotation fix; stays `disable-model-invocation`) |
| pcf-ops | survives (audit-clean) |
| production-change-gate | survives (+ Tier 0–3 model; branch-protection check already merged) |
| release-gate | survives |
| rollback-mitigation | merges into **incident-command** (the reversible-action decision table) |
| route-request | **dissolves** → native model-initiated delegation + `agents:` allowlists |
| runbook-template | merges into **runbook** (sde-agents body; this template becomes its asset) |
| safe-refactor | → process reference under **craft** |
| sde-ladder | merges into **eng-ladder** (sde-agents base) |
| self-improve-loop | **deleted** (Ralph/Claude-specific machinery; its move-failures-left principle survives in agent doctrine) |
| slo-error-budget | merges into **obs-alerting** (burn-rate patterns; `error_budget.py` ported with severity fixes) |
| spa-architecture | → reference content under **frontend-craft** |
| splunk-triage | → SPL reference under **obs-logs** (3-sigma bucketing fix applied) |
| sre-ladder | merges into **eng-ladder** (responder/investigator/elite as the SRE-track tier references) |
| tdd-workflow | → sde agent body (tests-first discipline) + process reference under **craft** |
| thousandeyes-network | → synthetics reference under **obs-alerting** |
| tool-design | → reference under **agent-authoring** |
| wavefront-queries | → WQL reference under **obs-metrics** (fabricated `by`-clause fixed) |

### Agents (9 → 5)

| Old agent | Disposition |
|---|---|
| sde-engineer | → **sde** (chassis replaced by sde-agents `sde-fullstack`; domain content carried) |
| code-reviewer | → **reviewer** (chassis: sde-agents `code-reviewer`) |
| security-reviewer | merges into **reviewer** (its threat lens = review dimension 2; split back is one file if pilot shows dilution) |
| test-engineer | **deleted** (tool scope identical to sde; testing method → sde body; untrusted-code refusal doctrine kept) |
| sre-engineer | → **sre** (+ Tier 0–3 change authority; compromise-handling rules kept) |
| sre-monitor | → **observer** (+ "never cut the branch you're sitting on") |
| runbook-author | → **scribe** (loses `execute` entirely — cleaner than the guard it wore) |
| researcher | **deleted** (native `web` tool + subagents; also held the fleet's widest egress) |
| prompt-engineer | **deleted as agent** → **agent-authoring** skill carries the method |

Count check: survivors + merges + new = 26 skills (roster table, Section 4); 5 agents (Section 3). Nothing in the old fleet is unaccounted for.

## Appendix 2 — Machinery ledger (everything that is not an agent or a skill)

The first ledger claimed "nothing in the old fleet is unaccounted for" while covering only the 37 skills and 9 agents.
That claim was false: the machinery, the eval corpus, the root docs, and the in-skill assets were all unnamed — and the
"Explicitly deferred" catch-all would have **deleted them silently**. Same verbs as Appendix 1.

### Evals (the largest omission — 70 case files)

| Item | Disposition |
|---|---|
| `evals/discovery/*.yaml` (**45 cases**) | **Rewritten, not ported.** Every case names an old skill/agent (`craft-sde-ladder`, `agent-sre-engineer`). Rewrite one per surviving unit as the **canary set** that Section 8's "0 dark skills" bar is measured against. The 2 unpassable cases (`disable-model-invocation` targets) are **deleted** — they measure the flag, not discovery. |
| `evals/scenarios/*.yaml` (**25 cases**) | **Port per surviving unit.** These are the behavioral regression tests — the gates' blocking behavior, injection refusal, handoff taint. Section 4 justifies keeping three separate gates *because they "eval'd well separated"*; dropping their evidence machinery would gut that argument. Cases for deleted units (`researcher`, `route-request`) are deleted with them. |
| `evals/clean_room.py` | **Survives, load-bearing.** Merged PR #52; it is what makes any eval number trustworthy. |
| `evals/run_evals.py`, `discovery_probe.py`, `graders.py` | **Survive, adapted.** They measure the generated Claude projection (Section 7), never Copilot by proxy. The same case corpus also drives separately recorded native Copilot runs. Graders gain the `max_skills` fan-out assertion (Section 8). |
| `evals/test_graders.py`, `test_discovery_probe.py` | **Survive** — including the adversarial `_BLOCK_CASES` the audit's Tier-1 #3 hardened. |
| `evals/README.md` | **Rewritten** for the new rig; keeps the "manual, never a CI gate" discipline. |

### Scripts, CI, hooks

| Item | Disposition |
|---|---|
| `scripts/readonly-guard.py` + `readonly-guard-hook.sh` | **Not ported.** Its corpus informs Task 38, but name admission and POSIX shell parsing are unsafe on the Windows target. Task 38 either proves a strict Copilot guard + shell-free absolute broker or structurally removes execute. Old files are deleted in Phase 4. |
| `scripts/test_readonly_guard.py` | **Replaced** by viability, strict-guard, shell-free-broker, runtime-wiring, and setup-refresh suites. The old corpus is retained as regression input; PowerShell/name/PATH bypasses are added first. |
| `scripts/validate_fleet.py` | **Rewritten** = validator v2 (Section 6). |
| `scripts/ralph-loop.sh` | **Deleted.** Claude-Code-specific unattended-loop machinery; its owning skill (`self-improve-loop`) is deleted, and nothing in the Copilot fleet drives it. |
| `.github/workflows/validate.yml` | **Survives, extended** to validator v2 + the new tests. Gains the `main` → `release` promotion gate (Section 1). |
| `requirements-dev.txt` | **Survives.** Machine constraint: on Windows `python3` is the Microsoft Store stub, not an interpreter — use `python` or `py -3`. **Moot in practice:** every gate goes through `scripts/gate_a.py`, which re-invokes its sub-steps under `sys.executable` and is therefore correct under all three. Don't reintroduce a hardcoded interpreter name. |

### Root docs

| Item | Disposition |
|---|---|
| `AGENTS.md` | **Preserved to `legacy/claude-fleet/` in Phase 1 before any rewrite** (see Phase 1 — it is at the repo root, so the fleet `git mv` misses it, and its content must be *absorbed* into the new agent bodies, not lost). Then **split — it has two roles the spec previously conflated.** (a) *Shipped fleet context* → **dies** (its stack profile becomes `stack-profile`; its roster/routing become native `agents:`/`handoffs:`; its egress census becomes Section 5c). (b) *This repo's own project instructions*, for people working **on** the fleet → **survives, rewritten** and much shorter. Note VS Code also reads `AGENTS.md` from any open workspace, so it must not carry shipped-fleet content once the plugin exists. |
| `CLAUDE.md` | **Preserved to `legacy/claude-fleet/` in Phase 1**, then **survives, minimal** — the Claude Code entrypoint for developing the fleet (`@AGENTS.md`), matching the sister repo's convention. |
| `README.md` | **Rewritten** — install (marketplace + the trust prompt), the maintainer name, `--write-inventory` fleet table. |
| `docs/RESEARCH.md` | **Survives, updated** — retarget from Claude Code sources to the VS Code/Copilot doc set (the five pages this design is built on). |
| `docs/AUDIT-2026-07-12.md` | **Survives** — the evidence base for every "audit fix" in Appendix 1. |
| `docs/superpowers/{specs,plans}/` | **Survive** — decision history (this document included). |
| `LICENSE` | Survives. |

### In-skill assets and references (the strays)

| Item | Disposition |
|---|---|
| `ops-cli/assets/cli_skeleton.py` | → asset under **ops-tooling**. |
| `api-design/assets/openapi.starter.yaml` | → asset under **backend-craft**. |
| `pcf-deploy/assets/*`, `github-actions-ci/assets/*` | Survive with their skills (CI asset gains the `cf auth` fix). |
| `runbook-template/assets/*`, `adr-template/assets/*` | → assets under **runbook** and the `adr` prompt file. |
| `route-request/references/fan-out.md` | **Deleted** with `route-request` — but its cost model (fan-out ≈ 15× tokens; right-sizing band) moves into **agent-authoring**'s multi-agent reference. |
| `sre-ladder/references/golden-signals.md` | **Survives** → reference under **eng-ladder** (SRE track). *(Named because the first ledger listed only the three tier files and would have dropped it.)* |
| `craft/references/{python,bash,powershell,go,typescript,react}.md` | Survive under **craft** — **but see the boundary note below.** |
| `pcf-ops/{references,scripts}/*`, `splunk-triage/references/*`, `wavefront-queries/references/*`, `grafana-dashboards/references/*`, `moogsoft-correlation/references/*`, `thousandeyes-network/references/*` | Survive as the per-backend references of the six by-signal obs skills. `pcf-ops/scripts/triage.{sh,ps1}` survive (human-run). |
| `slo-error-budget/scripts/error_budget.py` | **Survives with fixes** → **obs-alerting** (severity ladder + window-pair binding; audit Tier-2 #4). |
| `agent-authoring/references/*`, `sde-ladder/references/*`, `route-request/references/*` (others) | Fold per Appendix 1. |

### Two skill boundaries that must be pinned (or they become the next six-skill pile-up)

Routing confusion is failure mode #1; only one boundary (data-viz vs obs-dashboards) was pinned. Two more overlap:
1. **`craft` vs `backend-craft`/`frontend-craft`.** `craft` = *per-language* conventions (Python/Bash/PowerShell/Go/TS/React).
   `backend-craft`/`frontend-craft` = *per-layer* design (contracts, resiliency, layout, state). **Decision: `craft` keeps
   only the languages the layer skills don't cover** — Python, Bash, PowerShell, Go. **Its `react.md` and `typescript.md`
   are deleted**, since `frontend-craft` owns that layer whole. Each description states the split.
2. **`backend-craft/references/persistence.md` vs `database-reliability`.** persistence = *writing* the data layer
   (drivers, pools, migrations, transactions). `database-reliability` = *operating* it (slow queries, lock contention,
   replication lag, connection-pool exhaustion during an incident). Build vs. debug. Both descriptions say so.
