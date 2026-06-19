# Architecture & design rationale

This explains *why* the fleet is built the way it is. The "what/who" lives in
[`AGENTS.md`](../AGENTS.md) (the cross-tool source of truth); this is the "why."

> **Scope reminder:** we work the **application operations** lane — on-prem servers + **PCF (Tanzu
> Application Service)**, **no Kubernetes**, no cloud-managed infra. Every decision below is made for
> that reality, not Google-scale SRE.

---

## 1. One source of truth under `.claude/`, portable to Copilot

**Decision:** author everything once as Claude Code **subagents** (`.claude/agents/*.md`) and **Agent
Skills** (`.claude/skills/<name>/SKILL.md`); both Claude Code and VS Code / GitHub Copilot read
`.claude/` natively.

**Why:** lowest duplication, widest reach. The only non-portable seam is the agent `tools:` field
(Claude uses `Read, Grep`; Copilot wants arrays). We resolve that with a generator
(`scripts/sync-copilot.{sh,ps1}`) that emits `.github/agents/*.agent.md` + mirrors skills — those
outputs are **generated, not hand-edited**. `AGENTS.md` stays canonical; `CLAUDE.md` imports it.

---

## 2. Agents vs. skills — who vs. how

- **Agent** = a *specialist with its own isolated context*, system prompt, tool allowlist, and model.
  It owns one **lane** and returns a distilled summary. (11 agents.)
- **Skill** = a *reusable procedure / reference / template* that loads on demand via progressive
  disclosure (only its `description` is resident until a task matches). (36 skills.)

Agents reference skills by name, so methodology stays DRY across the fleet.

---

## 3. Seniority is a **skill (altitude)**, not a separate agent

**Decision:** there is **one** `sde-engineer` and **one** `sre-engineer`. They scale altitude by
loading a **ladder skill**, not by being cloned into junior/senior/principal agents.

- SDE: `sde-ladder-senior` → `sde-ladder-principal` → `sde-ladder-distinguished`
- SRE: `sre-ladder-responder` → `sre-ladder-investigator` → `sre-ladder-elite`

**Why:** the alternative (a `senior-developer` + `principal-developer` + … agent each) multiplies the
roster, duplicates lane knowledge across persona files, and forces the picker to guess seniority up
front. One agent that *reads the task's ambiguity and blast radius and picks the tier* is more flexible,
keeps the roster small, and means a craft/stack improvement is written once. Trade-off: the altitude is
less visible in a Copilot agent-dropdown than a named agent would be — we accept that for DRYness and
document the tiers in [`AGENT-CATALOG.md`](AGENT-CATALOG.md).

---

## 4. Routing & orchestration is **plan-output**, executed by the main thread

**Decision:** the `coordinator` agent (backed by the `route-request` skill) and `incident-commander`
produce an **ordered delegation plan** — which agent, what context to pass, success criteria,
sequencing, gates. The **main session executes** that plan.

**Why:** classic Claude Code subagents **cannot spawn other subagents** — only the main session
delegates. So a coordinator that *tried* to dispatch would just add a hop. Emitting a plan keeps the
pattern portable (it also works in Copilot) and keeps the main thread as the supervisor. (Newer "agent
teams" can dispatch directly; we keep plan-output for portability.) Use the coordinator only for
multi-step/ambiguous work — for a single obvious task, route directly.

---

## 5. Read-only is **enforced**, not just promised

Six agents are read-only by charter: `coordinator`, `code-reviewer`, `security-reviewer`,
`sre-engineer`, `incident-commander`, `researcher`. The four that still need `Bash` for *observation*
(`code-reviewer`, `security-reviewer`, `sre-engineer`, `incident-commander`) run behind a `PreToolUse`
hook — [`scripts/readonly-guard.py`](../scripts/readonly-guard.py) — that **blocks state-changing shell
commands**. `coordinator` and `researcher` get no `Bash` at all.

**Why:** "read-only" written in a prompt is a hope; a hook is a control. For an ops-maturity-focused
team, the difference matters — an investigator must not mutate prod while triaging. This is our single
biggest advantage over a prose-only design.

---

## 6. Gates protect quality and prod

Three pass/fail checklist skills sit on the critical path:
- **`merge-gate`** — before a change merges (review clean, tests green, security reviewed if sensitive).
- **`release-gate`** — before a deploy (change record, rollback written, health checks, comms).
- **`production-change-gate`** — change-management checkpoint for *any* prod-facing/destructive action.

**Why:** they make safety a checkpoint, not a vibe. They're portable Markdown by default; in Claude Code
they can be **hardened with hooks** (e.g. block the `pcf-deploy` skill until `release-gate` passes); in
GitHub, back them with branch protection + environment reviewers.

---

## 7. Fresh-context review (why reviewers are separate, read-only agents)

`code-reviewer` and `security-reviewer` are distinct agents, not a mode of `sde-engineer`. A reviewer in
a fresh context sees only the diff and the criteria — not the reasoning that produced the change — so it
judges the result on its own terms and isn't biased toward code it just wrote. That's the
generate-then-critique loop, and it's why the reviewers stay read-only.

---

## 8. Model & tool matrix

Heavy-reasoning lanes run `opus`; higher-volume specialists run `sonnet`. (Accurate as of this commit —
keep in sync with the agent frontmatter.)

| Agent | Model | Tools | Mutating? |
|---|---|---|---|
| `coordinator` | sonnet | Read, Grep, Glob, TodoWrite | no (plan only) |
| `sde-engineer` | opus | Read, Write, Edit, Grep, Glob, Bash, TodoWrite, Web* | yes (code) |
| `code-reviewer` | opus | Read, Grep, Glob, Bash, TodoWrite | **no — guarded** |
| `security-reviewer` | opus | Read, Grep, Glob, Bash, Web*, TodoWrite | **no — guarded** |
| `test-engineer` | sonnet | Read, Write, Edit, Grep, Glob, Bash, TodoWrite | yes (tests) |
| `sre-engineer` | opus | Read, Grep, Glob, Bash, Web*, TodoWrite | **no — guarded** |
| `sre-monitor` | sonnet | Read, Write, Edit, Grep, Glob, Bash, Web*, TodoWrite | yes (obs-as-code) |
| `incident-commander` | sonnet | Read, Grep, Glob, Bash, WebFetch, TodoWrite | **no — guarded** |
| `release-engineer` | sonnet | Read, Write, Edit, Grep, Glob, Bash, Web*, TodoWrite | yes (CI/PCF — prod needs sign-off) |
| `runbook-author` | sonnet | Read, Write, Edit, Grep, Glob, Bash, WebFetch, TodoWrite | yes (docs) |
| `researcher` | sonnet | Read, Grep, Glob, WebSearch, WebFetch, TodoWrite | no (read-only, no Bash) |

"**guarded**" = read-only enforced by `scripts/readonly-guard.py`. `Web*` = `WebSearch` + `WebFetch`.

---

## 9. Validate & extend

- **Validate:** `pwsh scripts/validate-fleet.ps1` checks every skill/agent against the Agent Skills spec
  (name charset, name == directory, description ≤ 1024 chars, referenced bundle files exist). Run before
  committing or in CI.
- **Add an agent:** new `.claude/agents/<name>.md` with `name` + a trigger-style `description`; scope
  `tools`; pick a `model`; add it to the `AGENTS.md` roster and [`AGENT-CATALOG.md`](AGENT-CATALOG.md).
- **Add a skill:** `.claude/skills/<name>/SKILL.md` with a "what + when" `description`; register it in
  `AGENTS.md`, `README.md`, and (if it changes routing) `route-request`.
- Candidate future agents are tracked in [`AGENT-CATALOG.md`](AGENT-CATALOG.md); handoff edges in
  [`HANDOFFS.md`](HANDOFFS.md).
