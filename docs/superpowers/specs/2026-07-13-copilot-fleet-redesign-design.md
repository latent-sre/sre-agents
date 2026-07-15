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

- **GitHub identity:** `https://github.com/latent-sre/sde-agents`
- **Local operator input:** configurable `SDE_AGENTS_SOURCE`; a path such as `C:\Users\hawkins\sde-agents` is illustrative only and carries no provenance. At each phase open, normalize/verify its `origin`, fetch `origin`, pin the full `origin/main` SHA once, record URL+SHA, and read only that Git object (`git show` or detached read-only archive)—never mutable worktree bytes or stale local `HEAD`.
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

**Primary channel.** This repo becomes an **agent plugin with one canonical fleet model and two generated runtime projections** plus a generated Copilot safe-recovery variant. `canonical/fleet.json` plus `canonical/agents/*.md` are the only agent-definition authoring sources; `canonical/commands/*.md` is the only command-body source; shared skills remain authored under `skills/`. During construction, canonical definitions may exist before their mandatory skills, but an incomplete definition is never a runtime artifact. The generator emits:

- root **`plugin.json`** for Copilot, whose `agents` field points to the **directory** `./generated/copilot/agents/`;
- **`.plugin/plugin.json`** as a generator-owned exact-byte alias of root `plugin.json`, used only to make current VS Code native plugin selection resolve the Copilot projection when the Claude marker coexists;
- **`.claude-plugin/plugin.json`** for Claude Code, whose `agents` field enumerates the generated Claude files under `./generated/claude/agents/` explicitly;
- **`generated/copilot-safe/agents/`**, a non-manifest recovery variant with the same names/bodies but structural execute omission for `sre`/`observer`;
- Copilot wrappers named `*.agent.md` and Claude wrappers named `*.md`;
- native-plugin commands under **`generated/copilot/commands/*.md`**, fallback prompt wrappers under **`generated/copilot/prompts/*.prompt.md`**, and explicit Claude command files under **`generated/claude/commands/*.md`**, all generated from one canonical command semantic contract;
- **`generated/runtime-tree.json`**, added in Phase 4, hashing every runtime-visible file and declaring the selected `execution_mode`.

The two semantic manifests carry the same generated `name` and `version`, but each contains only fields documented for that runtime; canonical metadata is mapped, never copied wholesale. `.plugin/plugin.json` is not a third manifest contract: its bytes must equal root `plugin.json`, the generator owns the entire `.plugin/` directory, and missing, stale, linked, hardlinked, or unexpected selector content fails closed. This compatibility alias responds to an observed VS Code 1.128.1 selector rule: with `.claude-plugin/plugin.json` present and no `.plugin/plugin.json`, the client selected the Claude format. Installed-loader inspection predicts that adding `.plugin/plugin.json` will classify the plugin as OpenPlugin and retain the Copilot agent/command paths, but that prediction is not accepted until a replacement immutable native smoke demonstrates it. Native evidence must record that classification and diagnose only `generated/copilot/` sources. OpenPlugin hook/MCP lookup is not inferred from root-Copilot behavior and must be re-probed before Phase-4 machinery relies on it. With zero **runtime-ready** agents and commands both semantic manifests emit `"agents": []` and `"commands": []`, replacing those default discovery paths even when canonical agent bodies already exist. With zero **active** catalog skills both emit `"skills": []` as an explicit schema state, but Claude's `skills` field is additive: exact absence from the default `skills/` tree is enforced by canonical inventory, not by that empty field. Once nonempty, root Copilot points `agents` and `commands` at the generated Copilot directories; Claude explicitly enumerates generated Claude agent and command files. VS Code fallback does not consume the native-plugin command directory: it uses `chat.promptFilesLocations` pointed at the generated `.prompt.md` view. `--check` fails on manifest, selector, wrapper, or command drift, including a wrapper for an unready agent, wrong command suffix/frontmatter/body, unsafe parents/hardlinks, and nested or wrong-suffix files in every generator-owned directory that exists at the current phase; after Task 38 this includes the safe-recovery variant. `--write` removes obsolete safe regular files from every generator-owned manifest/agent/command/prompt directory (including the selector and safe variant once present), then uses same-directory temporary files plus atomic replacement; links, junctions, Windows reparse points, and hardlinked targets fail closed and are never followed or deleted. Convergence tests cover both ready-agent removal and canonical-command removal from all three generated command views. They are generated views, **not separate sources of truth**. All variants share the same bodies and skill bundles; only runtime frontmatter/capability projection differs. Copilot auto-discovers root `hooks.json`; Claude Code auto-discovers `hooks/hooks.json`; both stay empty. Neither manifest re-references them. The marketplace's documented refresh cadence is availability behavior, not an integrity boundary: the installed updater independently verifies protected `release`, active-tree identity, and the 26-hour freshness deadline, atomically disabling brokered discovery or switching to the verified safe-recovery projection on skew. Maintenance-deny remains a secondary fail-closed state only while the proven fleet hook is known to be live; it is never credited after client drift could stop hook invocation. Phase 4 records safe mode or a brokered candidate only after both Copilot paths pass; Phase 5 requalifies the selected channel on a team client and may only downgrade to safe. Only the final brokered Copilot setup installs the separately proven machine-local enforcement scope, and setup preinstalls the safe recovery view before brokered discovery. Claude `sre`/`observer` omit execute here.

Every canonical command record has exactly six keys: `name`, `source`, nonblank `description`, `argument_mode` (`required` or `none`), `argument_usage` (nonblank iff required), and `invocation_mode: manual`. A required-argument body contains `{{arguments}}` exactly once; a no-argument body contains none. The Phase-1 spike empirically pins each runtime's supported description metadata, invocation/selection identity, source attribution, argument expression, and manual-only control. The generator maps only documented metadata, translates the sentinel, and emits `disable-model-invocation: true` where supported; VS Code fallback prompt files are inherently manual and receive no invented field. After exact generated-frontmatter removal and reverse normalization to `{{arguments}}`, all non-runtime body bytes must equal the canonical source. Artifact-writing commands (`adr` and conditional `bamboo-to-actions`) carry a body-level fail-closed lane preflight: they write only with `sde` selected; under a read-only agent they create nothing and tell the user to select `sde`, without requesting or granting tools. Blank or unaccounted description loss, wrong sentinel count, unsupported required-argument transport, unprovable manual-only behavior, command/body drift, or a prompt that widens the selected agent's capability is blocking. A checked-in `compatibility.schema.json` uses `additionalProperties: false` at every object; the repo's stdlib-only restricted-schema validator implements only the declared keyword subset and rejects unsupported schema keywords rather than claiming generic JSON-Schema support. `compatibility.json` has exact top-level keys `schema_version`, `status`, `model_projection`, `delegation_projection`, and `command_boundary`; version is `1`, status moves exactly once from `pending` to `accepted`, and the accepted gate rejects pending/null/false evidence. Model rows have exact `configured`, `emitted`, `status`, and `evidence_locator` fields; delegation rows have exact `configured_targets`, `emitted_form`, `observed_behavior`, `status`, and `evidence_locator` fields. `command_boundary` has exact rows `native_copilot`, `fallback_copilot`, and `claude`, each with exact keys `client_version`, `view_path_suffix`, `frontmatter_shape`, `description_mapping`, `argument_expression`, `argument_transport`, `observed_identity`, `identity_template`, `invocation_affordance`, `manual_invocation_control`, `resolved_source`, `source_commit`, `source_tree`, `runtime_tree_sha256`, `bound_input_locator`, `argument_echo`, `auto_invocation_negative`, `command_decoy_result`, `skill_decoy_result`, and `evidence_locator`. Both locator types are contained repo-relative `{path, sha256}` objects. The shared bound input points at a checked-in exact path→SHA-256 runtime manifest, so current runtime bytes can be proven equal even if squash/rebase later discards the intermediate test commit; the full source SHA remains provenance, not a permanent ancestry requirement. Each runtime row records repeated slash-free on-target non-invocation, exact `fmt_arg_7c91` echo, observed description/manual affordance, decoy-alone controls followed by diagnosed two-candidate command/prompt and skill collisions, and hashed sanitized evidence. `observed_identity` is spike-specific; `identity_template` is the tested production substitution rule. The accepted description/argument/identity/manual/collision mapping is copied into generator constants/tests rather than read as mutable runtime configuration. Client upgrades produce versioned hashed requalification packets, update the affected accepted client/evidence row, and rerun schema, mapping, collision, manual-negative, and projection checks; mapping drift regenerates affected runtime bytes and gets new bindings/review/canary evidence.

Production canonical data carries one exact 26-name skill catalog. During construction each record is either `planned` (name + activation task, with no directory) or `active` (name + exact directory and bundled reference/asset/script inventory). A planned directory on disk, an active record without exact filesystem parity, missing/unexpected content, or an unknown catalog name fails generation. Each agent carries one fixed `required_skills` list. That list is hard-dependency integrity metadata—not a relevance catalog, per-agent allowlist, or preload request. An agent is skill-ready only when every required catalog record is active; the runtime-ready set is the greatest skill-ready set closed over every delegation and handoff target. Only runtime-ready agents get wrappers or manifest entries. `required_skills` is never copied into Copilot metadata and never emitted as Claude `skills:`; a ready Claude wrapper instead receives the generic `Skill` tool for on-demand loads. Each canonical agent body also carries one machine-checked marked dependency block: every canonical name is paired with its bare Copilot identity and exact Claude plugin identity `sre-agents:<name>`. Generic `Skill` therefore does not authorize a bare-name guess or a competing project/personal skill; a missing, extra, duplicate, or wrongly namespaced pair fails generation. A separate canonical `skill_dependencies` map pins two rows/seven mandatory loads: `ops-tooling → eng-ladder`, plus `service-onboarding → production-change-gate, obs-pipeline, obs-dashboards, obs-alerting, ci-actions, runbook`. A planned owner may declare planned targets during construction, but an active owner requires every target active and an exact marked dependency block in its `SKILL.md`. Mandatory-load lint scans every strict-UTF-8-decodable file in the owner's complete inventory—not only `SKILL.md`, and including Markdown, YAML/JSON/text assets, scripts, comments, and emitted guidance—and treats `load`, `invoke`, `read`, `use this skill`, `see`, `consult`, `follow`, or `switch to` plus a fleet-unit name as action-bearing. A non-UTF-8 file is classified binary and may not carry linked instruction guidance. Every such load is attributed to that owner and must match the canonical row with an active target and both runtime identities. A bare sibling name is non-action only in the exact ownership/handoff form containing literal `not a load`; typed lint rejects handoff-to-skill and load-from-agent confusion. Relative internal guidance links are not dependency edges. Canonical command bodies are self-contained and may contain no action-bearing cross-skill reference. Skill frontmatter uses the exact allowlist `name`, `description`, `argument-hint`, `disable-model-invocation`, and `compatibility`; optional `argument-hint` is a nonblank string, never a YAML list. This map is integrity metadata, never runtime manifest preload metadata.

`assembly_state` is `boundary-only` in Phase 1, `content-building` while Phases 2–3 activate catalog records, and `content-complete` only when all 26 are active, all five agents are runtime-ready, all seven skill-dependency edges resolve, and both projections have exact parity. `boundary-only` additionally requires canonical `commands: []`, no canonical command bodies, absent/empty generated command and prompt views, and `commands: []` in both production manifests; only the isolated format spike is nonempty. Task 33 adds a permanent `--require-content-complete` Gate-A assertion plus an always-run contract test in `scripts/test_generate_fleet.py` for its exact Gate-A tuple, so later work cannot legitimize missing dependencies by downgrading construction state or deleting the gate. The Task-1 generator enforces this throughout Phases 1–3; validator v2 later repeats rather than first introducing it. The Phase-1 spike carries one inert file of each bundled skill kind and proves exact inventory plus POSIX path containment before Task 1 ports the generator; Task 9 adds the separate Markdown-link checks.

**Construction is not publication.** No mutable checkout path is registered through Tasks 1–39. Per-file atomic replacement prevents torn files but cannot publish a multi-file cohort atomically, so production discovery stays disabled while authoring/generation runs. A runtime checkpoint finishes drift checks, binds one exact commit/tree, copies it to an immutable disposable snapshot outside the authoring path, records source-tree and runtime-tree digests, enables exactly one channel in a neutral profile/workspace, proves the selected manifest format and source path plus absence of duplicate definitions, then unregisters and removes it before the next channel. Native VS Code evidence must bind the selected `.plugin/plugin.json` bytes to root `plugin.json` and show that all resolved agent/command sources are Copilot projections despite the client's OpenPlugin classification. Because the snapshot also contains the optional Grafana `.mcp.json`, the Task-33 native sacrificial profile fails closed unless `GRAFANA_*` is absent, `uvx` is unresolvable, MCP access/autostart/discovery/gallery/apps are disabled, no external MCP registration exists, and before/during/after Diagnostics plus process censuses show no MCP, hook, or `uvx` event/process. That containment is a smoke precondition, not evidence about OpenPlugin MCP semantics; Phase 4 must still re-probe those semantics before enabling machinery. Intentional hostile-workspace collisions are consumer fixtures and must be explicitly accounted for; they never mutate the plugin snapshot. Any tested-input or runtime-visible byte change requires a new snapshot and invalidates affected evidence. Append-only sanitized/hash-bound evidence outside the runtime inventory may be added later only when it names the durable tested tree/bound-input manifest and the final runtime digest remains identical; this is the sole non-runtime exception. Before the protected canary harness exists, this is construction evidence only, not release/promotion evidence.
*[sourced: code.visualstudio.com/docs/agent-customization/agent-plugins; code.visualstudio.com/docs/agent-customization/prompt-files; docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference; code.claude.com/docs/en/plugins-reference; and code.claude.com/docs/en/slash-commands, rechecked 2026-07-14]*

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
- Task 40 authors and hermetically tests the trusted harness on the Phase-4 branch; it cannot claim a protected-main dispatch before that workflow exists on the default branch. Task 41 merges it, then blocks Phase 5 on the first three-OS protected-`main` validation/cleanup dispatch against the exact merged main SHA. Only after that bootstrap gate may unpublished plugin/runtime/setup behavior used as release-bound evidence be tested from unique immutable `canary/<phase>/<full-sha>` refs registered in a sacrificial profile with full SHA pins. All earlier local snapshots—Tasks 26, 33, and every runtime/eval checkpoint in Tasks 35–39—are construction evidence only and never promotion evidence. Canary CI is a workflow definition dispatched from protected `main` with the candidate SHA; it checks out unreviewed code without persisted credentials, secrets, OIDC, or a writable token, and records its own trusted workflow blob. Candidate-authored workflow YAML is never the harness. Controlled refresh evidence uses two distinct green SHA/version states A→B (or protected release A→canary B), not a self-refresh. The production marketplace remains `ref: release`; setup/refresh rejects canary sources. Changed bytes get a new ref/evidence. Pre-merge canaries provide review evidence; because merge/squash/rebase may change SHA, **every promotion** freezes reviewed `main` and runs/cleans a final canary at that exact merged-main commit. Final Phase-5, pilot fixes, rollback, and 1.0 all follow both stages. After probes, disable/unregister every state, prove no active source points at it, retain evidence, and delete every ref. Canary evidence never substitutes for reviewed-main CI.
- Promotion requires green CI and current human + Code Owner review on `main`. **Every path is workstation-security input**, including future root Python startup files and default-discovery locations, so CODEOWNERS begins with `* @maintainer`; a current-path allowlist is not sufficient. `main` dismisses stale approvals and requires approval of the latest reviewable push.
- `release` is a derived exact-SHA ref, not a second authoring/review branch. A Code-Owned manual promotion workflow, dispatched by a named release operator and separately approved by the maintainer through a protected environment, creates or fast-forwards it to the **identical current reviewed green `origin/main` SHA** with `force: false`. One ruleset restricts release/version-tag creation and update with the dedicated GitHub App as its sole bypass; a separate no-bypass invariant ruleset denies force-push/deletion even to the App. The repository-scoped App token unavoidably needs `Contents: write` and is not ref-scoped, so it is short-lived, absent from `main` bypass, denied workflow/admin/secrets/environment permissions, and other refs are protected against it. Common checks bind current main SHA/tree, final review/check, and generation. **Canary evidence is mandatory for every promotion.** The workflow queries a protected-main canary run and later cleanup run, requires the recorded canary commit SHA **equal current reviewed `origin/main`**, verifies harness blob/run/green matrix/full-tree/runtime digests and authenticated inactive-profile evidence, and rechecks remote ref deletion. There is no documentation classifier bypass because every promotion bumps version and changes generated runtime state; pure documentation may remain unpromoted on `main`. Bootstrap is an explicit `expected_old_release_sha=ABSENT` branch: it twice proves release ref/version tag/release object absence, version `0.9.0`, the Phase-1–5 merged-PR/audit ledger, Gate A/C, and maintainer bootstrap approval; it never dereferences an old ref. Normal promotion requires the expected old full SHA, twice-fetched equality, old→candidate ancestry/range provenance, a version increase, and absence of the new version tag/release. The workflow re-fetches/asserts final equality and creates no merge/squash/rebase commit. Humans/admins have no release-update bypass. `release` is created once after Phase 5 at `0.9.0`; promoted pilot fixes, rollbacks, and later releases use the same pre-review canary → reviewed `main` → exact-main canary → workflow path. *[sourced: GitHub ruleset bypass applies only within that ruleset; Git ref writes require `Contents: write`; normal PR merge methods do not provide an exact-SHA ref-move invariant]*
- Every successful transition has a durable machine-verifiable record: deterministic `promotion-record.json` is bound to repository/ref, old and candidate SHAs, version/tag, source PR/final review, check, runtime digest, exact workflow blob/run, environment/approver, App identity, final remote equality, and mandatory validation/cleanup run IDs, protected-main harness blob, canary SHA, tree/runtime digests, matrix results, cleanup identity/result, and ref-absence observation. A full-SHA-pinned GitHub attestation action signs it with a custom predicate; the asset is published in an immutable `fleet-v<version>` GitHub Release whose tag/assets also receive GitHub's release attestation. Setup independently verifies release, asset, signer workflow, signature, and every field. Mutable repository JSON and expiring Actions artifacts are not authoritative. Records remain for the supported-client lifetime plus rollback window; missing/deleted/conflicting evidence fails safe. A ref move followed by record-finalization failure is not blessed in place—clients stay disabled/safe and recovery is a new reviewed version fast-forward. Availability of immutable releases and custom attestations on the repository's actual GitHub plan is a Phase-5 STOP gate; an unavailable feature requires an approved durable external signer/store and a design amendment, not a silent weakening.
- **Rollback/freshness:** roll forward a revert/fix through reviewed `main` and the same promotion workflow; never reset, force-push, directly revert, or create a release-only commit. Disable discovery for prompt/control-plane compromise, or select the verified safe projection for an execution-boundary failure, while the reviewed rollback is prepared. Freeze unrelated merges to `main` until rollback promotion; after merge run/clean the exact-main canary, then re-fetch before dispatch. If main moves, repeat exact-main evidence; changed bytes also require rebase/review/version/pre-review-canary again. Scheduled `setup --refresh` independently verifies protected release and its immutable/custom-attested promotion record at least daily; stale, missing, or mismatched state switches/disables discovery rather than calling an old-plugin/old-guard pair healthy.
- Bump `version` in `canonical/fleet.json` on every promotion and regenerate both manifests + Copilot safe-recovery + runtime-tree projections; direct projection edits are forbidden.

**The distribution gates (two product/channel gates, one model-configuration gate, plus two client-policy admission gates).** An earlier draft called
`chat.plugins.enabled` "the design's only admin dependency." It is not. These gates do not change canonical content;
they independently select delivery channel and execution mode:
1. **`chat.plugins.enabled`** — defaults false, **org-managed**. Flippable, or policy-blocked? (Decides channel.)
2. **Copilot org policy — "Editor preview features."** Agent plugins are Preview; an org toggle can gate preview features independently of the VS Code setting. *[unverified — verify here rather than assert]*
3. **Model availability.** Section 3 pins Claude-first fallback arrays. Anthropic-model access depends on org model policy and license tier. Confirm the named models are actually selectable, and record the assumed tier (Business/Enterprise) as a stated assumption.
4. **Client pin + plugin refresh.** Brokered mode requires the exact VS Code build and Copilot extension managed/pinned, effective `update.mode: none`, enterprise policy `ExtensionsAutoUpdate` producing effective `extensions.autoUpdate: "off"`, the Copilot extension's distinct per-extension Auto Update off, and attempted updates unable to replace either. Boolean `false` is not the documented current string-valued setting, and `extensions.autoCheckUpdates` is not a substitute. Every plugin delivery mode independently requires managed global auto-update off so background plugin checks cannot race the updater, plus a controlled noninteractive A→B refresh that reaches protected release within 26 hours while pins remain. If global off cannot be enforced or A→B cannot be proven, plugin delivery is STOP/fallback. *[sourced: VS Code documents application, global extension, and per-extension update controls separately, and agent-plugin automatic update checks depend on `extensions.autoUpdate`; rechecked 2026-07-14]*
5. **Hook policy.** Brokered mode requires managed `ChatHooks=true` actually applied/enforced, locked effective `chat.useHooks: true`, known policy provenance, and an observed marker event. If agent-scoped hooks are used, `chat.useCustomAgentHooks: true` must also be policy-manageable/locked against the hostile workspace and client-drift model; a mutable local true setting does not qualify. False, absent/not-applied, unknown, policy-unresolved, mutable custom-hook state, or liveness failure selects a separately proven hook scope or safe mode before discovery. A named policy owner switches clients safe before changing either control; scheduled detection cannot protect the interval after hooks stop running. *[sourced: VS Code enterprise AI settings says `ChatHooks=false` ignores hook configurations; hooks docs require `chat.useCustomAgentHooks` for agent-scoped hooks; rechecked 2026-07-14]*

Model availability is separate from both decisions. If canonical model fallbacks are not selectable, correct canonical configuration, regenerate, and repeat runtime evidence—or STOP. Safe mode cannot repair an unavailable model.

**The format contract is a Phase-1 blocking preflight, not an inference.** Before any fleet agent is authored, a nonempty spike must load one coordinator, one delegated terminal agent, one shared skill/reference, one canonical command projected into all three runtime views, and one inert hook through three separately recorded paths: native Copilot plugin discovery, Copilot fallback discovery, and Claude Code. Each row invokes the command/prompt with `fmt_arg_7c91` and requires exact echo; first, in an ordinary context where automatic invocation is available, a near-miss prompt must produce no command/Skill expansion event, marker, or artifact. Exact command/prompt and skill decoys are introduced one at a time and must be rejected, explicitly disambiguated, or source-diagnosed to the immutable snapshot. Claude evidence never substitutes for either Copilot path. The hook-payload probes for the production guard still run in Phase 4, where they are first needed. See Section 7.

**Fallback (if policy blocks plugins).** Setup materializes an exact-inventory, versioned tree under `~/.sre-agents/releases/<sha>/fleet` and atomically sets all three GA discovery keys: `chat.agentFilesLocations` to its generated Copilot agent view, `chat.agentSkillsLocations` to shared `skills/`, and `chat.promptFilesLocations` to `generated/copilot/prompts/`. It never loads the mutable verification clone. Scheduled `setup --refresh` verifies protected release, stages a new complete tree/runtime, and atomically switches or removes all three JSONC paths together; bare `git pull` is forbidden. Native plugin and fallback share canonical agent bodies and skills, but fallback consumes the `.prompt.md` command view rather than the native-plugin command directory. Claude consumes its separate generated agents/commands and no-guard/no-execute-for-SRE projection.

**Onboarding — trusted bootstrap first, then one selected Copilot channel:**

- **Bootstrap:** the maintainer publishes the exact protected-release SHA and setup SHA-256 out of band. The engineer
  downloads into a fresh non-workspace directory and verifies both *before execution* with an absolute OS-owned hash
  utility under a no-profile, sanitized environment; PATH, aliases, functions, and workspace profiles are excluded.
  A checkout-local script cannot authenticate itself after it starts. Setup still refuses unless its own bytes/path
  equal the fetched release copy.
- **Preflight:** `git`/`gh auth`/settings found; absolute owner-approved outer executor, hash utility, isolated-capable
  Python, and broker tools found. The verification clone has canonical origin and clean `HEAD == origin/release`;
  canary/feature/local sources are rejected. The immutable-release asset and custom promotion attestation must
  independently verify and bind release to the reviewed-main SHA with no release-only commit. API responses prove
  current `main` review/latest-push/Gate-A rules, every layered `release`/version-tag ruleset, immutable-release state,
  App/environment contract, and force-push/deletion denial including the App, with human/admin bypass denied.
- **Selected execution mode:** Phase 4 records `safe` or a brokered candidate only after both Copilot delivery paths
  pass hostile-workspace precedence/location, outer-spawn, nested identity, updated-input, terminal poisoning, and
  shell-grammar probes. Phase 5 reruns the complete suite through the selected channel on a team client and may only
  downgrade to safe. Brokered admission also requires the exact client pin/update and hook-policy gates above. Setup installs the finally proven hook scope, guard, shell-free broker, typed source adapter, and
  maintenance record before discovery. Safe mode instead verifies that `sre`/`observer` wrappers omit execute and
  installs no guard.
- **Installed updater:** setup atomically installs/hash-records itself and every helper under `~/.sre-agents/bin|lib`;
  the scheduler invokes an absolute preflight that verifies the installed updater hash. It never runs a mutable clone,
  workspace, or plugin-cache script. Python uses isolated/no-site/no-bytecode startup and sanitized environment.
- **Channel exclusivity:** setup proves the unselected plugin/fallback registration and any same-name workspace
  definitions are inactive before enabling the chosen source; `-Verify` rejects dual registration or ambiguous source.
- **Plugin channel:** additionally requires managed global `extensions.autoUpdate: "off"`, the proven adapter to identify
  the currently active root and verify exact version/SHA/runtime-tree contents, plus a controlled noninteractive A→B
  refresh while background extension auto-update is disabled, then prints the conscious Extensions trust step. A
  self-refresh, stale cache, or manual update hope is not evidence. Before **any** plugin delivery is selectable, a real
  team client must also prove that the installed updater can
  noninteractively disable/unregister that active plugin and atomically activate/reload the preverified fallback-safe
  paths, with no duplicate definitions, and reverse the transition only after full requalification. Fixture-only
  switching cannot close this gate; if the real transition is unavailable, plugin delivery is STOP and fallback is used.
- **Fallback channel:** installs the versioned exact-inventory tree above and atomically changes the fleet entries in
  `chat.agentFilesLocations`, `chat.agentSkillsLocations`, and `chat.promptFilesLocations` only after runtime
  preparation; reverse/channel-failure transitions remove or roll back all three together. Comments/trailing commas
  are preserved by targeted edits, not `ConvertFrom-Json` rewriting.
- **Refresh transaction:** fetch/verify/stage under a lock. It independently verifies the immutable release asset and
  custom promotion attestation. Remote/promotion skew, missing/conflicting evidence, freshness expiry, plugin lag/ahead,
  client-version/global-or-per-extension-update-policy skew, hook-policy/setting/liveness drift, or a partial fault switches/disables active discovery to the preverified no-execute recovery projection; plugin
  mode uses the separately acceptance-gated plugin-to-fallback-safe transition, while fallback switches versioned paths. A
  maintenance record alone is not protection if the client stopped invoking hooks or background updates ceased to be
  policy-disabled. Only complete source/tree/runtime/
  updater/client convergence clears it. Safe mode still refreshes verified content, but its structural protection is
  execute omission.
- **JSONC hazard:** VS Code `settings.json` is **JSONC** — comments and trailing commas are legal. `ConvertFrom-Json`
  either fails or silently strips the engineer's comments on rewrite. Use a comment-tolerant parse + targeted key
  insertion, or instruct a manual paste and confirm with `-Verify`.
- **`setup.ps1 -Verify`** reports the bootstrap hash, channel, execution mode, full active-tree/version/SHA/freshness/
  promotion handshake, every protection field/actor, installed updater/helper/interpreter/tool hashes, isolation state,
  exact client/extension versions, effective update settings, controlled plugin-refresh result, applied hook-policy source/settings/liveness, distributed-hook
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
| Canonical commands + generated runtime views | Manual-only one-shot workflows authored once in `canonical/commands/`: the `adr` scaffold and, conditionally, a Bamboo walkthrough. Both require `sde` for writes and fail closed without widening a read-only agent. Native Copilot consumes `generated/copilot/commands/*.md`; fallback consumes `generated/copilot/prompts/*.prompt.md`; Claude consumes `generated/claude/commands/*.md`. |
| Hooks | Portable files stay empty; Copilot gets a machine-local guard+broker only if the hostile-runtime viability gate passes, otherwise execute is omitted (Section 5) |
| MCP servers | Live tooling — a Grafana MCP server is the LGTM-exploration vehicle *(existence/fit: verify during implementation)* |
| Delegation + handoff projections | Canonical `delegates_to` maps to Copilot `agents:` and Claude `Agent(target)`; `handoffs:` is emitted for Copilot only. |
| Plugin | The distribution wrapper |

**Structural consequences:**
1. **AGENTS.md dies as always-on context.** Plugins don't inject ambient instructions into arbitrary repos — which force-ends the 3.3k-token tax. Each canonical agent body is self-contained for its lane, method, safety doctrine, and output contract, but deliberately **not dependency-free**: its machine-checked block names the active skills it must load on demand. The stack profile becomes a small **`stack-profile` skill** rather than ambient context. The stay-in-lane rule lives *only* there, phrased as current fact ("runtime today: on-prem + TAS; GCP under evaluation late 2026"), so one file changes when the ground shifts.
2. **Read-only is intended to become structural.** An agent whose accepted runtime `tools:` projection omits `execute`/`edit` should be unable to run or write; the Phase-1 behavior probes must prove that omission fails closed before this becomes a fact. The hook guard survives only as an audit/deny layer on agents that genuinely need `execute`.

## Section 3 — The agent roster: 9 → 5

| Agent | Tools (GitHub alias vocabulary) | Lane | Chassis provenance |
|---|---|---|---|
| **sre** | read, search, execute*, web, **agent** (generated from delegation) | Triage, RCA, incident investigation | sre-agents `sre-engineer` method + sde-agents doctrine + **Tier 0–3 change authority** |
| **sde** | read, search, execute, edit, web, agent | Build/fix/refactor code and ops tooling; absorbs test-writing | **sde-agents `sde-fullstack`** (forks, checkpoint contracts, red-flags table, review packet w/ worked example) |
| **reviewer** | read, search **only** | Code + security review (two lenses, one tool scope) | **sde-agents `code-reviewer`** (`[caller-flagged]`/`[independent]` + mandatory independent-P0/P1 count; evidence gate; injection rule) + sre `security-reviewer` lens |
| **observer** | read, search, edit, execute*, **agent** (generated from delegation) | Obs-as-code: dashboards, alerts, SLOs; LGTM home | sre-agents `sre-monitor` + Tier 0–3 + "never cut the branch you're sitting on" |
| **scribe** | read, search, edit (**no execute**) | Runbooks + postmortems; documents commands from evidence, never runs them | sre-agents `runbook-author` modes + sde-agents `runbook` leanness |

**Hard skill dependencies (the exact canonical `required_skills` matrix):** an edge appears here only when the agent body mandates loading that skill. This is not a relevance catalog, a runtime allowlist, or Claude preload policy. Routing-only/invoke-only skills and skills that merely consume an agent's output are not dependencies.

| Agent | Mandatory on-demand loads |
|---|---|
| **reviewer** | `stack-profile` |
| **sde** | `stack-profile`, `root-cause`, `eng-ladder`, `craft`, `backend-craft`, `frontend-craft` |
| **sre** | `stack-profile`, `root-cause`, `eng-ladder`, `pcf-ops`, `database-reliability`, `incident-command`, `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting` |
| **observer** | `stack-profile`, `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`, `obs-pipeline` |
| **scribe** | `stack-profile`, `runbook`, `postmortem` |

This is 28 pinned agent edges. `obs-traces` is deliberate for both signal-owning agents because their lanes promise trace work even though the legacy fleet had no trace skill. `ops-tooling`, `ci-actions`, the three gates, `pcf-deploy`, `service-onboarding`, `agent-authoring`, and `agent-security` remain discoverable/invoke-only from the agent-routing perspective; they do not become agent hard dependencies merely because they are relevant or consume a packet. Every agent body carries exactly one `## Required on-demand skills` block delimited by `<!-- required-skills:start/end -->`; each bullet pairs canonical/Copilot `<name>` with Claude `sre-agents:<name>`. The generator requires exact set equality with the row above and rejects marker, name, or namespace drift. A new mandatory agent `load` sentence changes this table, canonical data, body block, and generator fixture in the same commit.

**Skill-to-skill dependencies (separate canonical graph):** only mandatory method loads appear here. This is not runtime manifest preload metadata.

| Skill owner | Mandatory on-demand loads |
|---|---|
| **ops-tooling** | `eng-ladder` |
| **service-onboarding** | `production-change-gate`, `obs-pipeline`, `obs-dashboards`, `obs-alerting`, `ci-actions`, `runbook` |

These are seven pinned edges. Each active owner carries one `<!-- required-skill-dependencies:start/end -->` block with canonical, Copilot, and Claude identities; an active owner with a planned target, body/map drift, or a bare/one-runtime-only action instruction fails generation. The `ops-tooling` edge closes in Phase 2 after `eng-ladder`; the six-edge onboarding slice closes in Task 32.

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

**Timing (the model check is free, and earlier than Phase 5).** Agent bodies are authored in Phase 1 but deliberately
not projected until their dependency/edge cohort is ready. Model availability is formally checked in Phase 5 — which
sounds like a hole and is not: the array is a *prioritized fallback*, so an unavailable model degrades to the next
entry rather than failing. The first observed answer is Task 26, after the Phase-2 cohort is copied into an immutable,
channel-isolated snapshot: **loading that first runtime-ready production agent shows which model it actually picked.**
Phase 5 confirms it for the whole team under their license tier.

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
| ci-actions | SRE `github-actions-ci`, `cf auth` argv leak fixed. Bamboo content: **default delete** (recoverable from git); if live migrations remain, Task 20/Phase 2 creates one canonical command and all three generated runtime views |
| database-reliability | SRE |
| agent-authoring | SDE `prompt-craft`/`prompt-engineer` method + SRE `agent-authoring`; references absorb tool-design, context-engineering, multi-agent-architect's "should this be multi-agent at all?"; teaches **personal-first, promote-by-PR** and compose-with-fleet-agents |
| agent-security | SRE, rewritten Copilot-native (tool-scope containment) — ships because teammates *will* build their own agents |

Canonical commands: `adr` (scaffold), generated into native Copilot `.md`, fallback `.prompt.md`, and Claude `.md` views; optional `bamboo-to-actions` follows the same three-view projection only if Task 20 records live migrations. The complete fate of every existing unit is the **Disposition ledger** (appendix at the end of this document); the implementation plan turns that ledger into dependency-ordered tasks.

## Section 5 — Safety model

1. **Primary control, proved in two gates: `tools:` omission.** Task 2b's self-contained spike must prove the generic native-plugin, fallback, and Claude schema/tool behavior before any production body is authored; failure stops Phase 1 and amends this safety model. That evidence does **not** prove a production definition. Reviewer/scribe omission remains `[unverified]` until Task 26 loads the first complete production cohort from isolated immutable snapshots and passes the same denial tests before normal use. The same omission is the mandatory fallback for `sre` and `observer`: Phase 4 may retain their Copilot execute tool only after the execution-boundary viability gate passes through **both** native-plugin and fallback delivery in a hostile workspace, and Phase 5 requalifies the selected channel on a team client's real policy before setup. That later gate may only downgrade brokered to safe. Their Claude projections omit execute; this design does not claim a non-managed Claude hook can survive project-level hook disabling.
**The VS Code hook contract differs from Claude Code — do not port the exit codes.** VS Code: **exit 0 means stdout is parsed as JSON** (`permissionDecision`: `allow` | `deny` | `ask`); **exit 2 is a blocking error**; other codes are non-blocking warnings; and **"most restrictive wins"** among hooks that actually run *[verified: hooks reference, fetched 2026-07-14]*. The sister repo's 42/43 outcomes may survive only as an internal guard-to-launcher protocol explicitly mapped to VS Code output. The outer boundary comes first: VS Code also documents workspace-hook precedence and configurable hook locations, and no launcher can emit deny if VS Code never starts it. Organization policy is earlier still: `ChatHooks=false` makes VS Code ignore hook configurations. Brokered admission therefore requires applied/enforced `ChatHooks=true`, locked `chat.useHooks`, and—when agent-scoped—policy-manageable/locked `chat.useCustomAgentHooks`; absent/not-applied, mutable, false/unknown policy, or a failed live marker forces a separately proven scope or safe mode before discovery. Therefore a user-hook smoke test is not an enforcement proof. Phase 4 must show that an agent-scoped hook—or managed scope proven to invoke only for source-qualified fleet definitions—cannot be suppressed by hostile workspace hooks/settings, that same-name workspace definitions cannot impersonate it, that an outer spawn failure blocks, and that `updatedInput` is applied exactly. A global hook that sees unrelated sessions fails the non-fleet contract. Any failure selects safe mode (`execute` omitted); it never degrades silently to audit-only.

2. **The hook + broker — allowlist doctrine without shell-name theater.** *"Enumerating the ways a command can write is unbounded and always a step behind; enumerating what an agent needs is bounded, knowable, and fails loud."* The sister guard is evidence and a regression corpus, not a parser to copy: its POSIX `shlex` model accepts PowerShell array subexpressions, and its name-only reader bucket admits execution/write flags. In brokered mode, the guard strictly parses JSON and a tiny cross-platform token grammar, identifies the **current nested agent**, applies a positive per-command argv grammar, and replaces tool input with one absolute installed broker plus a base64url argv payload. The broker revalidates, verifies absolute tool hashes, strips helper/config/Python-startup environment, and calls an argv array with `shell=False`. It never resolves PATH, aliases, functions, pagers, preprocessors, compressors, external diffs, or terminal profiles. Any inability to prove this exact transformation selects safe mode.

3. **Installed/runtime integrity.** The portable hook files remain empty. In brokered mode setup installs the guard, broker, renderer/updater helpers, and runtime record under `~/.sre-agents/`; Python runs isolated/no-site/no-bytecode. The generated runtime-tree manifest inventories and hashes every active agent/skill/reference/asset/script/command/hook/manifest file and rejects unexpected default-discovery content. Every execute decision checks that tree—not just Git HEAD—plus fleet version, the independently verified immutable-release asset/custom promotion attestation, installed component/tool hashes, enforced client/update/hook-policy state, and a successful protected fetch no older than 26 hours. Canary/feature sources and release-only commits are invalid. Once the proven outer executor starts, missing/tampered state, audit I/O failure, source/tree/freshness/policy skew, or an unexpected internal outcome denies every invocation within the fleet scope. If the client, policy, or outer executor drifts so the hook might not start, the updater atomically disables brokered discovery or selects the preinstalled safe-recovery projection; if that transition cannot be proved, fleet discovery stays disabled. If the outer executor itself cannot be made blocking when absent, brokered mode is unavailable.
4. **Change authority: Tier 0–3** (observe / prepare / reversible-live / destructive-or-access-path), imported from sde-agents `homelab-platform`: classify before acting; approval covers only the commands shown; a material change re-enters the gate; independent Tier 0/1 work continues while approval pends; worked approval-request example (target, diff, exact command, blast radius, verification, rollback). Woven into sre + observer bodies and production-change-gate.
5. **Prod boundary:** `main` is the sole review boundary: current Code Owner review, stale-approval dismissal, latest-push approval, exact Gate-A context, administrators included/no bypass, and force-push/deletion denial. `release` is a derived exact-SHA ref: one ruleset restricts creation/update to the dedicated promotion App through a distinctly dispatched/maintainer-approved environment, while a second no-bypass ruleset denies force-push/deletion even to that App. The App is absent from `main` and holds short-lived repository-level `Contents: write` only in the privileged job because GitHub cannot natively scope ref-write permission to one branch. Humans/admins cannot write release. The verifier checks all matching contracts plus the immutable release/custom attestation; one `enforce_admins` boolean or one ruleset is not the whole control.

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
5. **Probed, not assumed—and no live brokered auto-upgrade.** Platform facts the safety model rests on get re-run through both delivery paths after every VS Code/Copilot upgrade and through Claude after every Claude version change. Brokered mode requires exact managed/pinned editor and Copilot-extension versions, effective `update.mode: none`, managed global `extensions.autoUpdate: "off"`, Copilot per-extension Auto Update off, applied/enforced `ChatHooks=true`/locked `chat.useHooks` (plus policy-manageable custom-agent hooks when used), known policy sources, and a live marker; failure or ambiguity selects safe mode. Every plugin channel separately requires globally enforced auto-update-off and a controlled noninteractive A→B refresh; otherwise fallback is mandatory. The named policy owner/change procedure first switches/disables brokered discovery and proves the safe projection while the old client/hook still runs, then changes app, extension, plugin, or hook policy and requalifies before restoring brokered mode. The list includes payload/tool fields; current direct+nested/source-qualified identity; same-name workspace collisions; hostile workspace/settings and hook-disable precedence; fleet-invocation-scoped hook behavior; outer spawn failure; exact `updatedInput`; PowerShell/cmd/POSIX parsing; terminal PATH/profile/environment poisoning; active plugin root/tree and fallback installed tree; plugin/fallback skill and agent loading; controlled A→B plugin refresh; distributed-hook emptiness; and the **complete command boundary**: `disable-model-invocation`, repeated slash-free on-target non-auto-invocation, exact argument echo, description/manual affordance/source identity, valid decoy-alone controls followed by two-candidate command/prompt and skill collisions, `sde` artifact write, and reviewer fail-closed/no-write. Production and nested format snapshots carry separate source/runtime digest pairs and mismatch tests. Requalification writes versioned hashed evidence, updates accepted compatibility client/evidence rows even when mappings are unchanged, and regenerates/rebinds/reviews/canaries any mapping-driven runtime change. A scheduled maintenance record is not credited as protection after a client stops invoking the hook or background plugin updates cease to be policy-disabled.

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

- **Validator + generator drift gate:** validate the canonical schema/readiness state first, then both generated projections. Reject unknown canonical keys; missing/duplicate/non-kebab explicit names; catalog-name, 28-edge agent-dependency, or two-row/seven-edge skill-dependency drift; a planned record with a directory; an active record without exact inventory; missing/duplicate agent or skill dependency-block markers; a body↔canonical dependency mismatch; a missing/wrong Copilot-bare or Claude-`sre-agents:` identity; an undeclared/bare-only/Claude-only mandatory load anywhere in an owner's complete inventoried UTF-8 text tree (including YAML comments and script output), or a binary file linked as instruction guidance; a wrapper/manifest entry outside the greatest edge-closed ready set; construction-state downgrade after Task 33; dangling delegation/handoff targets; a Copilot `agents:` list without `agent`; Claude delegation not mapped to `Agent(target)`; canonical dependencies leaked as Claude `skills:` preloads; a ready Claude agent without generic `Skill`; Copilot handoffs leaked into Claude; any direct or nested Claude `sre`/`observer` execute alias; runtime-invalid model shapes; manifest name/version skew; manifest agent-path shape drift (Copilot directory versus Claude explicit files); wrapper body drift; and stale/unexpected generated files. Command checks require the exact six-key record (`name`, `source`, nonblank `description`, `argument_mode`, `argument_usage`, `invocation_mode: manual`), correct `{{arguments}}` count, Task-2b-pinned per-runtime description/argument/identity/manual-control mapping, root Copilot command-directory shape, explicit generated-Claude files, fallback `.prompt.md` shape, and byte parity after exact frontmatter removal plus reverse argument normalization. Validate the restricted checked-in schema and exact five-key compatibility top level with `status: accepted`; exact nested model/delegation rows; three exact runtime rows including full source SHA/tree/runtime digest, shared hashed bound-input locator, and contained hashed evidence; current runtime path→hash equality; `fmt_arg_7c91` echo; production identity substitution; repeated slash-free on-target non-auto-invocation; observed description/manual affordance; and valid decoy-alone controls followed by diagnosed command/prompt and skill collision results. Do not require the intermediate source commit to remain resolvable after squash/rebase; the durable bound-input manifest is the invariant. Generator constants must equal accepted evidence. Blank/unaccounted metadata loss, unsupported required arguments, wrong expressions, absent/wrong manual control, auto-invocation, spike-literal production identity, silent collision precedence, missing/bad/escaping evidence or bound input, source/runtime mismatch, missing/rogue/stale outputs, and non-argument body drift fail in all three views. Command-specific fixtures also prove `sde` positive writes and read-only-agent fail-closed/no-write behavior without tool widening. Also retain ≤600-UTF-8-byte/2–4-trigger description lint, string-only `argument-hint`, bundle-reference existence, action-bearing hidden-dependency/type lint, schema-vs-policy separation, doctrine checks, `--write-inventory`, and the independent persistent `--require-content-complete` Gate-A assertion plus its exact-tuple contract test in the always-run generator suite. Closure fixtures prove recursive elimination, all-ready cycles, handoff-only and mixed chains, and stale-wrapper removal on a ready→unready transition. Hook checks are runtime-specific: root `hooks.json` and `hooks/hooks.json` are auto-discovered and must not appear in either manifest. Broken-fleet fixtures cover both schemas. Platform evidence also stays split: Claude strict validation validates Claude only; native Copilot plugin and fallback probes validate Copilot.
- **Canonical skill catalog:** throughout construction, require exact parity between every **active** catalog record and the runtime-visible skill/bundled-file tree, require a planned record's directory to be absent, and require every agent hard dependency and skill-dependency owner/target to name a catalog entry. An active skill owner requires every declared skill dependency active and an exact marked body block. Runtime agent projection additionally requires every agent dependency active and the ready set closed over runtime edges. At `content-complete`, all 26 entries are active, all five agents are ready, the pinned two-row/seven-edge skill-dependency map resolves, and planned state is forbidden. Missing and unexpected entries fail before content linting.
- **Routing evals** (sde-agents format + sre-agents clean-room rig): overlap clusters, positives + **near-miss negatives** ("shares vocabulary, should route elsewhere"), graded deterministically off transcripts, reported as **rates over runs**, cases phrased to measure routing without spawning long sessions. Two refinements from the completion sweep: **negatives are cross-cluster positives**, and routing evals run **manually, before/after description edits — never as a CI gate**. The historical `36812ed` clean-room baseline is explicitly Claude-only and compares only to new Claude discovery under the recorded rename/max/carve-out rules. Native-plugin and fallback Copilot each must meet the absolute 0.5 positive threshold with zero negative fires on its first accepted run; that run becomes a separate runtime-specific baseline. New clusters likewise create per-runtime baselines. No Claude result is labeled a Copilot proxy, and runtime rates are never combined.
- **Behavioral probes with canary strings** (plant a distinctive string in a skill; its appearance in output proves loading) + **tripwire tests guarding the canaries** (an innocent copy-edit would silently disarm the oracle).
- **Execution-boundary tests** first decide brokered versus safe mode in real VS Code and run through both native-plugin and fallback delivery. Brokered mode must survive hostile workspace/settings precedence, hook-disable attempts, nested identity, missing/renamed-identity maintenance denial, conflicting allows, outer-spawn failure, poisoned terminal/Python environment, PowerShell/cmd/POSIX syntax, and exact `updatedInput` transport. Unit/wiring suites then test strict JSON, per-command argv grammars, shell-free absolute broker execution, durable audit failures, runtime-tree/source/freshness skew, path injection, and installed updater transactions. Safe mode instead proves execute omission directly and when nested. Distributed hooks remain empty; no Claude guard is inferred from Copilot evidence.
- **CI**: the restored workflow extends to the new validator + tests. Anti-rot rule from the audit, now doctrine: **a skill never transcribes an artifact that lives in the repo — point at it.**

## Section 7 — Migration plan (phases; each independently valuable)

> **Ordering rule: prove the cross-runtime boundary once, then build the product content-first.**
> The format spike is not a standalone phase or an empty scaffold. It is a blocking, nonempty Phase-1 acceptance gate
> containing an agent, a delegated terminal agent, a shared skill/reference, and an inert hook. It must pass native
> Copilot plugin discovery, Copilot fallback discovery, and Claude Code separately before any fleet agent is authored.
> Its result is the canonical-manifest/two-projection architecture in Section 1; Claude output is never Copilot
> evidence. After that boundary is fixed, canonical production bodies may be authored ahead of their dependencies,
> but the generator withholds them from every manifest and wrapper directory until their hard-skill and graph cohort
> is ready. No mutable production checkout path is registered during construction; runtime checkpoints use complete
> immutable disposable snapshots with one delivery channel enabled at a time. Content still precedes the machinery that protects it: canaries, routing
> evals, the selected execution boundary, and validator v2 are written against artifacts that exist. The positive
> command grammar for a brokered candidate—or the evidence that safe-mode omission is required—is only knowable after
> observing `sre` and `observer` work.
> Content also carries standalone value: if distribution turns out policy-blocked, a finished fleet still ships via
> the fallback channel. A finished validator with no fleet is worth nothing.

**Phase 1 — AGENT BOUNDARIES (5 canonical definitions; not task-usable).** This phase authors the product definitions but exposes none of them as runtime agents.

*Opens with the scaffolding, which is minutes of work, not a phase of its own:*
- `canonical/fleet.json`, conceptually empty canonical agent/command trees, conceptually empty generated agent/command/prompt trees, root `plugin.json`, and `.claude-plugin/plugin.json`. An empty owned tree may be absent in a fresh clone; no `.gitkeep` or other placeholder is permitted. `--check` treats a missing directory as exact-empty only while its expected inventory is empty, and `--write` creates parents immediately before the first real file. The canonical skill catalog starts with the exact 26 names in `state: planned`; the active runtime skill inventory is empty. Both manifests are generated from canonical metadata and drift-checked. Empty runtime-ready `agents` and commands suppress those default discovery paths; an explicit empty runtime `skills` array is only a schema marker for Claude, whose additive default `skills/` scan is controlled by exact empty-tree inventory. As dependencies activate, root Copilot points at the ready-agent and native-command directories; Claude explicitly enumerates ready generated Claude agents/commands; fallback points its agent, skill, and prompt settings only at an immutable snapshot. Add shared `skills/`, `canonical/commands/`, `generated/copilot/{commands,prompts}/`, `generated/claude/commands/`, root `hooks.json`, `hooks/hooks.json`, `.mcp.json`, and `.claude-plugin/marketplace.json` as their first real files require. The generator owns and drift-checks both empty hook projections and every command view; hooks are runtime-auto-discovered and never manifest entries. Phase 4 adds the always-no-execute `generated/copilot-safe/` recovery variant and runtime-tree manifest, then chooses safe mode or a brokered candidate; Phase 5 installs the safe recovery plus only the selected active runtime.
- **`git mv .claude/{agents,skills} legacy/claude-fleet/`** — *not cosmetic.* VS Code discovers skills from
  `.claude/skills/` **in any open workspace**, so leaving the old fleet in place means anyone opening this repo
  double-loads **37 old + 26 new** skills — the exact routing confusion the redesign exists to kill, at its worst
  during the phases used to judge whether it worked. Frozen, not deleted (git-recoverable). The
  `.claude-plugin/plugin.json` and root `plugin.json` keep both projections structurally loadable, but Tasks 1–39
  load only immutable disposable copies. Fallback settings likewise point only at a snapshot, never this checkout.
- **`cp AGENTS.md CLAUDE.md legacy/claude-fleet/`** — **the root docs must be preserved *beside* the fleet, not left
  to git archaeology.** They sit at the repo root, so the `git mv` above does *not* capture them, and both are
  slated for rewrite-in-place (Appendix 2). But they carry content the new agent bodies must **absorb, not lose**:
  the stack profile, the roster and routing tables, the read-only-agent doctrine, the egress/trifecta census, the
  gate layering, and the shared conventions. A rewrite that silently drops them is exactly the failure this
  redesign exists to prevent. **Phases 1–3 mine `legacy/claude-fleet/AGENTS.md` while authoring; the rewrite of the
  live `AGENTS.md` happens last, once its content has a new home.**

*Then the five canonical agent definitions* — sde-agents-derived bodies + doctrine layer, with the exact 28-edge
`required_skills` matrix and final delegation/handoff graph in Section 3. They are validated but not projected:
all catalog skills are planned, so the derived ready set is empty, both manifests retain `agents: []`, and both
generated agent directories remain empty. Generated wrappers are never authoring surfaces.

**The nonempty format gate runs before the first fleet agent.** Its coordinator/worker pair plus canonical command must exercise five
assertions in each applicable runtime. "It couldn't run a command" is **not** a pass on its own: that is equally
consistent with the vocabulary being wrong and the agent getting **nothing at all**.

| # | Assertion | If it fails |
|---|---|---|
| 1 | terminal worker **can read** the linked reference | grants or shared-skill paths are not landing. **Stop.** |
| 2 | coordinator **can delegate** to the named worker | runtime mapping is wrong (`agent` + `agents:` for Copilot; `Agent(worker)` for Claude). **Stop.** |
| 3 | terminal worker **cannot run a shell command** | omission fails **open**, so read-only-by-absence is dead. **Stop and amend Section 5.** |
| 4 | terminal worker **cannot delegate** | terminal omission fails **open**; the read-only model is decorative. **Stop.** |
| 5 | in an ordinary invocation-capable context, the slash-free **on-target** `fmt_auto_2d41` prompt does not auto-invoke across repeated trials; explicit invocation with `fmt_arg_7c91` returns the marker plus exact token from the diagnosed snapshot source; valid decoy-alone controls followed by same-name two-candidate command/prompt and skill collisions cannot win silently | manual-only control, argument transport, identity/source mapping, collision handling, projection, manifest path, fallback registration, or body parity is wrong. **Stop.** |

Assertion 4 exists because this spec refuses to infer default-deny behavior from schema shape. Claude's nested
target-list degradation is recorded separately and is not misreported as an exact nested allowlist.

**Where it runs.** First verify `spikes/copilot-claude-format/`, create a real pending candidate commit, and export that
commit to an immutable disposable snapshot outside the checkout. Record its full source commit/tree, runtime digest,
and a checked-in hashed `evidence/bound-input.json` containing the exact runtime path→SHA-256 inventory; every row and
three independent evidence packets bind that same manifest. In each row, before selecting the coordinator, run the
exact slash-free on-target prompt *"Use the format-boundary workflow to process token `fmt_auto_2d41` and return its
distinctive result."* in an ordinary context where automatic invocation is available and require no expansion event,
marker, or artifact across repeated trials. Then: (1) native
Copilot loads the snapshot's `plugin.json`, the coordinator delegates, the skill/reference marker appears, explicit
invocation with `fmt_arg_7c91` returns the marker plus exact token from the diagnosed snapshot source, and root
`hooks.json` fires; test `.github/prompts/format-boundary-command.prompt.md` and
`.github/skills/format-boundary-command/SKILL.md` sequentially as minimally valid distinct-marker decoys: disable the
snapshot, prove each decoy alone loads from its diagnosed source, re-enable the snapshot, diagnose both candidates,
select, then remove the decoy and prove a clean baseline before the next; repeat through applicable profile-level
stores. (2) Fallback settings load the
snapshot's `generated/copilot/agents/` + `skills/` + `generated/copilot/prompts/` through
`chat.agentFilesLocations`, `chat.agentSkillsLocations`, and `chat.promptFilesLocations`; the same agent/skill/token
behavior passes, the same exact workspace/profile decoys cannot win silently, and the fallback hook is registered
through its documented channel. (3) `claude plugin validate <spike-snapshot> --strict` plus a Claude CLI run with
`--plugin-dir <spike-snapshot>` runs under `clean_room.clean_env()` and a newly created disposable `CLAUDE_CONFIG_DIR`
whose resolved command/skill roots are proved outside the real home. It loads the explicit Claude wrappers and generated Claude command, delegates, reads the
shared reference, returns exact `fmt_arg_7c91`, and observes the snapshot's `hooks/hooks.json`; sequentially test and
remove `.claude/commands/format-boundary-command.md`, `.claude/skills/format-boundary-command/SKILL.md`,
`<disposable-claude-config>/commands/format-boundary-command.md`, and
`<disposable-claude-config>/skills/format-boundary-command/SKILL.md`, using the same decoy-alone control and diagnosed
two-candidate sequence. Every collision must be rejected, explicitly disambiguated, or source-diagnosed to the snapshot.
The real home remains untouched and the disposable root is deleted. The mutable spike directory remains
unregistered. The other two channels are disabled for each row. A Claude pass cannot close either Copilot row, and a
fallback pass cannot close native-plugin discovery.

**Done when:** the spike's three evidence packets are green; the restricted exact schema validates the five-key
`compatibility.json` with `status: accepted`; every row binds the same hashed bound-input manifest and shows token
echo/repeated on-target manual-negative/observed description and affordance/source/decoy-control/collision PASS; current
runtime bytes equal the tested path→hash map; and generator mapping constants equal that evidence. The intermediate
source SHA is retained as provenance but need not remain resolvable after an allowed squash/rebase integration.
Generation is drift-clean; five canonical production
definitions, the 28 agent hard edges, and the declared two-row/seven-edge skill-dependency map validate; all 26 catalog records remain planned; the derived production ready set,
both generated production wrapper directories, canonical production commands/bodies, all generated production command
and fallback-prompt views, and both production manifest agent and command lists are empty. The empty Claude
production projection also passes strict/plugin smoke. **No production agent is selected or given a domain prompt in
Phase 1.** Phase-1 production artifacts prove definition completeness and non-discovery only. The spike proves runtime schema/tool/delegation/skill/reference/command/hook behavior; calling the production fleet “working” or “test-usable” here is an error.

**Phase 2 — THE SKILLS (harvest + fix).** At phase open, state changes to `content-building`. Every skill task
finishes its body/description/bundle first, then changes its catalog record from planned to active with exact inventory,
regenerates, and runs the checks; a directory that remains planned at a task boundary fails generation. Direct imports (root-cause, eng-ladder, runbook, backend/frontend-craft,
ops-tooling) → SRE domain skills **with the audit's Tier-2 fixes applied — blue-green name rotation, the WQL `by`
deletion, SPL `timechart` bucketing, `cf auth` argv, error_budget severity, Grafana licence notes. Every fix is
specified in [`docs/AUDIT-2026-07-12.md`](../../AUDIT-2026-07-12.md); none may be ported as-is.** Confirm the Bamboo
decision and the `adr` canonical-command home plus all three generated views. If any runtime cannot ship that command, implementation **stops and amends
the command-distribution design**; `adr` cannot silently become a 27th skill. `service-onboarding` remains planned because
its mandatory observability methods are not active yet. When `postmortem` activates, the edge-closed `reviewer`/`sde`/`scribe` cohort becomes
the first production projection, but stays unregistered until the Task-26 snapshot checks. Phase 2 closes at exactly
19 active / 7 planned catalog records only after runtime-separated terminal/default-deny and normal core smokes pass;
`sre`/`observer` remain structurally undiscoverable.

**Phase 3 — THE OBSERVABILITY SKILLS.** Six by-signal skills; LGTM references written; legacy references carried over
post-fact-check. After every method it names is active (`production-change-gate`, `obs-pipeline`, `obs-dashboards`, `obs-alerting`, `ci-actions`,
and `runbook`), the invoke-only `service-onboarding` skill is created with a canonical six-edge `skill_dependencies` row and both runtime identities for each load; then
both remaining records activate in one closed slice. `obs-pipeline` closes the `sre`/`observer`
dependency/edge cohort. **End of Phase 3 the fleet is
structurally content-complete and runtime-smoke-clean:** 5 ready agents, 26 active skills, zero planned records, exact
projection parity, and the permanent `--require-content-complete` Gate-A assertion. It is eligible for Gate D;
behavioral routing/effectiveness is not called “working” until Task 36 records runtime-separated measurements.

**Phase 4 — Machinery** *(written against Phase-1 boundary evidence, Phase-2 core-cohort use, and the dependency-complete/runtime-smoke-clean Phase-3 tree — no incomplete-agent usage is credited)*:
validator v2 · the hostile-runtime execution viability gate · safe-mode omission **or** strict guard + shell-free absolute
command broker with bounded argv grammars · runtime-tree/freshness checks · canary/tripwire probes · routing evals · CI.
The payload, nested identity, workspace precedence, outer spawn, updated-input, and terminal-shell facts are probed here.
Task 40 may prove the new canary workflow only with hermetic fixtures and ordinary branch CI. After the Phase-4 PR merges,
Task 41's post-merge opening gate dispatches that now-default-branch workflow from protected `main` against the exact
merged SHA, requires the three-OS validation plus cleanup record, and blocks Phase 5 on any failure.

**Phase 5 — Distribution** *(and only here do the org gates matter — plugin/update policy chooses Copilot channel,
client/hook policy chooses safe/brokered execution, and failed model availability corrects canonical config or stops)*:
- Run the two product/channel gates, independent model-configuration gate, and client-pin/plugin-refresh + hook-policy admission gates on a team
  engineer's machine. A structurally safe fallback can ship only after the independent model gate passes.
- Publish unpublished plugin evidence from full-SHA-pinned disposable `canary/phase-5/<sha>` sources in a sacrificial
  profile, validated by a protected-main workflow rather than candidate YAML. Use distinct A→B states for refresh;
  repeat after the Phase-5 PR merges with a final canary at the exact merged-main SHA that promotion consumes.
  Production marketplace stays on `release`, setup rejects canary, and every canary is proven inactive/deleted after evidence.
- Prove active-plugin fingerprint, managed global auto-update-off, controlled A→B refresh, and plugin↔fallback-safe
  recovery. Without any one, plugin delivery is STOP and fallback is used. Both channels update only through serialized
  installed `setup --refresh`.
- Land wildcard CODEOWNERS, current-review protection on `main`, the Code-Owned exact-SHA promotion workflow, protected
  environment, layered update/no-bypass rulesets, immutable releases, and promotion App. After the Phase-5 PR merges,
  run the exact-main canary/cleanup, multi-path Code Owner, and effective-App-denial probes; then let the workflow create
  `release` at that identical green reviewed `origin/main` Phase-5 SHA (`0.9.0`) and publish its immutable custom-attested promotion record. Publish
  bootstrap hashes and run the first real setup/Verify.
- `setup.ps1|sh`, deterministic refresh tests, README, and rollback runbook (Section 1).

**Phase 6 — Pilot:** one engineer, real work repos. Exit only on the Acceptance bar (Section 8) — not "fix what
reality finds." Every promoted fix uses a short-lived branch from current `main`, mandatory pre-review and exact-merged-main
canaries with no documentation classifier bypass, a version bump/regeneration, current Code-Owner-reviewed PR to `main`,
exact-main-SHA workflow plus attested record,
refresh/Verify, and restart of the affected pilot interval. Unrelated main merges pause for the short promotion window;
if main moves, exact-main evidence repeats, and changed bytes also repeat review/version/pre-review canary. No direct release edit or long-lived pilot branch exists.

**Phase 7 — Team rollout:** prepare `1.0.0`, retire the legacy repo artifacts, and record outcomes on `phase-7-rollout`;
run a pre-review canary, merge the current Code-Owner-approved PR to `main`, then run/clean a second canary and controlled
`0.9.x`→`1.0.0` fingerprint test at the exact merged-main SHA. Promote that identical reviewed green SHA through the
protected workflow and independently verify its immutable attestation. Announce, retire the owner's personal `~/.claude` duplicates (`root-cause`, `eng-ladder`,
`runbook`—the shadowing the clean-room rig diagnosed), and instrument the week-one watch.

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
| **Format boundary** | native Copilot plugin, Copilot fallback, and Claude Code each load the nonempty coordinator/worker + shared skill/reference + canonical command + inert hook; each exact compatibility row proves `fmt_arg_7c91` echo, repeated slash-free on-target non-auto-invocation, observed description/manual affordance, diagnosed source, valid decoy-alone controls, and no silent same-name command/prompt or skill precedence; generated files equal the tested path→hash manifest and are drift-clean | three separately labeled hashed Phase-1 evidence packets with restricted-schema-valid five-key `compatibility.json` at `status: accepted` plus shared bound-input manifest; **no runtime is a proxy for another** |
| **No dark skills** | **0 of 24 model-invocable skills** fail to fire on their own on-target prompt | discovery canary per skill |
| **Side-effect skills load when called** | `pcf-deploy` and `service-onboarding` (both `disable-model-invocation`) load via the runtime's exact identity—Copilot `/<name>`, Claude `/sre-agents:<name>`—and their canary appears | runtime-specific **invocation** canary. By design they *cannot* fire on a prompt, so a discovery bar over all 26 would be unsatisfiable and Phase 6 could never exit. |
| **Routing precision** | no near-miss negative fires **at all**; Claude discovery positives ≥ the Claude-only old-fleet baseline under the recorded mapping; native/fallback Copilot and new clusters each meet the absolute 0.5 positive threshold and establish separate future baselines | runtime-separated cluster/discovery evals, rates over runs; no combined/proxy rate |
| **Fan-out** | a single incident prompt loads **≤ 2** fleet skills | routing eval with a `max_skills` assertion (the old fleet loaded **6**) |
| **Always-on context** | **≤ 4.5k runtime tokens** before any work (was ~8.3k), plus the deterministic **≤600 UTF-8 bytes per description** drift gate | real Copilot diagnostics for the total; Gate A for each description. Token estimates are labeled and cannot replace unavailable diagnostics. |
| **Execution boundary** | brokered mode: 0 unresolved false denies, 0 silent boundary/load failures, freshness ≤26h; safe mode: direct + nested execute denial | `setup -Verify`, native-plugin + fallback hostile-workspace probes, broker audit/runtime tree; or structural tool-omission probes. |
| **Pilot exit** | one engineer, **one week** touching **≥ 3 agents**, no unrecovered routing failure; brokered mode has no unresolved false deny, safe mode has no execute exposure | pilot log |
| **Rollout safety** | any acceptance regression in week one → disable/safe first, then roll-forward revert/fix through reviewed `main` + exact-SHA promotion; team announce | Section 1 rollback runbook |

**The token bar, honestly (an earlier draft said ≤3k, which this design makes impossible).** The always-on cost is
31 descriptions (26 skills + 5 agents) — and the discoverability fix *requires them to be longer*: verbatim user
phrasings plus boundary clauses are what makes a skill fire at all. Measured against the old fleet (37 descriptions,
avg 426 chars ≈ 106 tokens), 31 descriptions at the same length already cost ~3.3k, and with the added triggers
~4.0–4.6k. **So there is a real trade this design makes and must name: better routing costs context.** The structural
saving is not the descriptions — it is `AGENTS.md` + `CLAUDE.md` no longer being injected into every session
(−4.3k). Net ~8.3k → ~4.5k, a ~45% cut, with the routing failure mode fixed rather than traded away. A bar set below
what the roster can achieve would simply be ignored.

## Section 9 — Ownership and lifecycle

**Ownership.** The fleet needs a named maintainer — the person who gets pinged when an update breaks the team — and a
distinct release operator. **OWNER DECISION, not a builder guess:** CODEOWNERS, protected-environment self-review
prevention, the README, and rollback announcement block on both identities. The operator dispatches promotion; the
maintainer separately approves the environment.

**CODEOWNERS protects the whole repository by default:** `* @<maintainer>`. A path census cannot own a future root
`sitecustomize.py`, new workflow, dependency file, or default-discovery directory that does not exist yet. The initial
design has no exceptions; Gate A rejects any later rule that removes the maintainer from a prompt/control-plane input.
This explicitly includes `canonical/fleet.json`, canonical agent bodies/capability graphs, and `canonical/commands/**`; generated wrappers/runtime manifests plus `generated/copilot/commands/**`, `generated/copilot/prompts/**`, and `generated/claude/commands/**`; complete skill
trees (`SKILL.md`, references, assets, executable scripts); hooks; plugin/marketplace/MCP manifests; setup,
updater, generator, validator, guard, broker and probes; `.github/` workflows/CODEOWNERS; tests/evals/spikes; dependencies,
startup and auto-loaded instruction files; and future discovery paths. A representative multi-path probe PR proves the
effective owner after `main` activates the rule; a root-test-only probe is insufficient.

**`main` and `release` have distinct complete protection contracts.** `main` requires a PR, current Code Owner review,
stale-approval dismissal, approval of the latest reviewable push, exact Gate-A success on final bytes, administrators
included/no human bypass, and force-push/deletion denial. For `release` and `fleet-v*`, one ruleset restricts
creation/update to the dedicated promotion App; a separate no-bypass ruleset denies force-push/deletion even to that
App. Its repository-scoped `Contents: write` token is minted only after the distinct operator/maintainer environment
handshake, and the App is not a `main` bypass actor. Humans/admins/teams cannot write release. The Code-Owned workflow
alone verifies reviewed-main identity, fast-forwards without a commit, and publishes an immutable release plus custom
attested promotion record. Setup/refresh query every matching rule/actor/environment and independently verify release,
asset, signer workflow, and record fields. A partial ruleset, mutable record, or one boolean is not a security boundary.

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
- Onboarding states the 26-hour freshness boundary explicitly. The installed controlled `-Refresh`/`-Verify` path and
  active fingerprint are authoritative; background or manual extension/plugin checks cannot clear maintenance by themselves.

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
- Org-wide managed distribution beyond the required policy diagnostics, client pins, and release-promotion App/environment (trigger: org adoption)
- Automated/headless Copilot routing measurement (native manual probes remain required; revisit if a documented CLI interface lands)
- Old-fleet content named **deleted** in either ledger (Appendix 1 = agents/skills, Appendix 2 = machinery). Nothing is dropped by silence — the catch-all is gone.

## Risks (ranked) and open questions

1. **Agent plugins are Preview** — format/update churn could break the team at once. Mitigations: one canonical model, generated/drift-checked runtime projections, native-plugin + fallback probes, mandatory pinned client/extension versions for brokered mode, managed global extension auto-update-off for every plugin mode, controlled A→B plugin refresh with active fingerprinting, and fallback-safe recovery.
2. **`chat.plugins.enabled` org-policy-blocked** — fallback consumes the same canonical agent bodies and skills through the generated Copilot agent view, but commands through the separate generated `.prompt.md` view; checked in Phase 5 because it changes delivery, never canonical content.
3. **No automated Copilot routing measurement** — native Copilot routing/canary runs remain manual and runtime-labeled. Claude runs cover Claude only; treating them as Copilot evidence is prohibited.
4. **Copilot's command/hook boundary may be unenforceable** — workspace precedence can suppress user hooks; outer spawn
   failure may be nonblocking; nested identity and PowerShell command strings are under-documented; an uncontrolled
   client update or `ChatHooks=false` policy can stop invoking the guard while wrappers still expose execute. Phase 4 treats runtime mechanics and Phase 5 treats effective client/update/hook policy as
   a viability gate and requires applied/enforced hook policy, locked settings, and managed version/update controls.
   Every plugin mode separately requires a real-client atomic plugin-to-fallback-safe recovery proof. Failure is not
   audit-only: policy failure omits execute; plugin-control failure selects fallback. If brokered mode passes, post-launch
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
| adr-template | → canonical command `adr`; template content is embedded in `canonical/commands/adr.md` (the legacy asset is not shipped), then generated into native Copilot, fallback `.prompt.md`, and Claude command views |
| agent-authoring | survives, rebuilt on the sde-agents method (prompt-craft/prompt-engineer) |
| agent-security | survives, rewritten Copilot-native; per-agent census dropped (anti-rot: point at `tools:` frontmatter, not prose) |
| api-design | → reference content under **backend-craft** (`references/stack.md` work rewrite; OpenAPI asset rides along) |
| bamboo-to-actions-migration | **deleted** by default; if live migrations remain, Task 20/Phase 2 creates one canonical command and its three generated runtime views |
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
| merge-gate | survives (AGENTS.md-duplication cut; P0–P3 severity rubric added as new content—the audit specifies no rubric) |
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
| `.github/workflows/validate.yml` | **Survives, extended** to validator v2 + the new tests and reviewed `main`/`release` triggers. Unreviewed refs never supply their own CI definition: a separate `validate-canary.yml` dispatched with `ref: main` checks out a full candidate SHA without persisted credentials/secrets/writable token. A separate Code-Owned `promote-release.yml` performs the sole exact-main-SHA transition and publishes its immutable attested record (Section 1). |
| `requirements-dev.txt` | **Survives.** Machine constraint: on Windows `python3` is the Microsoft Store stub, not an interpreter — use `python` or `py -3`. **Moot in practice:** every gate goes through `scripts/gate_a.py`, which re-invokes its sub-steps under `sys.executable` and is therefore correct under all three. Don't reintroduce a hardcoded interpreter name. |
| `.mcp.json` | **Adopted in Task 30** as an optional, read-only Grafana operator aid: official `grafana/mcp-grafana` v0.17.2, reviewed 2026-07-14 and pinned as `mcp-grafana@0.17.2` through `uvx` with `--disable-write`. The skill remains complete without MCP. The subprocess inherits operator-set `GRAFANA_URL` and a least-privilege `GRAFANA_SERVICE_ACCOUNT_TOKEN`; no credential is tracked in this repository. Primary evidence: [Grafana MCP documentation](https://grafana.com/docs/grafana/latest/developer-resources/mcp/) and the [v0.17.2 release](https://github.com/grafana/mcp-grafana/releases/tag/v0.17.2), whose security fix prevents environment credentials from being sent to a caller-selected Grafana URL. |

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
| `runbook-template/assets/*` | → assets under **runbook**. |
| `adr-template/assets/adr-template.md` | Content is embedded in canonical `adr`; no separate ADR asset ships. The three runtime command/prompt views are generated from that single body. |
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
