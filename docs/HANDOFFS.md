# Handoff map

A "handoff" here means: a specialist finishes, returns a **structured summary**, and names **who picks
up next**. Routing and incident-command are **skills** (`route-request`, `incident-severity`) the main
session loads to emit an *ordered plan* (see [ARCHITECTURE.md](ARCHITECTURE.md) and [CLAUDE.md](../CLAUDE.md)'s
*Subagent dispatch* note), then it routes between agents. They stay skills on **cost, not capability**:
even though Claude Code now supports nested subagent dispatch, a coordinator subagent would double-pay
the routing round-trip and discard the main session's live context the work needs (see
[adr/0001](adr/0001-routing-and-incident-command-as-skills.md)). Each agent's body lists its own handoff
targets; this is the fleet-wide picture. Package context with `handoff-protocol`.

## Principles
- **Hand off, don't sprawl.** When work leaves your lane, name the target agent and give them what they
  need to start cold: intent, what's done, what you found, current state, success criteria.
- **Parallelize independent work** (research ∥ a second review lens ∥ investigation); keep tightly-
  coupled coding **sequential** in one agent.
- **Right-size the fan-out:** 1 agent for a simple lookup, 2–4 for a comparison or multi-lens review,
  more only for genuinely complex, decomposable work. Extra agents cost coordination and tokens — add
  them when parallelism pays, not by default.
- **Gates are checkpoints, not agents** — insert `merge-gate` / `release-gate` / `production-change-gate`
  on the path, don't "hand off" to them.

---

## Build → review → ship

```
                 (multi-step / ambiguous?)
   request ───────▶ /route-request (main session) ──(plan)──┐
      │  (single obvious task: route directly)              │
      ▼                                                     ▼
  sde-engineer ──(load sde-ladder by altitude)──▶ code-reviewer ──▶ [merge-gate] ──▶ release-engineer
   │   │   │   ▲                                        │                                  │
   │   │   │   └────────── fix findings ───────────────┘                          [release-gate]
   │   │   │                                                                               │
   │   │   └─▶ security-reviewer (auth / secrets / input / crypto / deps)         [production-change-gate]
   │   ├─▶ test-engineer        (coverage thin / dedicated test focus)                     │
   │   └─▶ database-reliability (schema/migration; writes fwd+rollback scripts)            ▼
   │            └─▶ release-engineer runs the migration under [production-change-gate]
   └─▶ researcher (unknown API/spec/lib)                                    pcf-deploy ──▶ runbook-author
                                                                                       (if new ops steps)
```

- **route-request (main session) → everyone:** produces the plan, then the main session executes it. Skip planning for one obvious task.
- **sde-engineer → code-reviewer:** every non-trivial change before merge (this *is* the `merge-gate`).
- **sde-engineer → security-reviewer:** auth, crypto, input handling, deserialization, dependency changes.
- **sde-engineer ⇄ test-engineer:** hand off when coverage is thin; test-engineer hands a *real bug* back.
- **sde-engineer → database-reliability:** for schema changes / migrations / slow queries. DBRE designs
  and **writes** the expand→contract migration + rollback, then hands those scripts to `release-engineer`
  to **execute under `production-change-gate`** — DBRE does not touch a prod database itself.
- **code-reviewer → sde-engineer:** apply fixes. **→ security-reviewer:** when depth is needed.
- **release-engineer:** owns CI/Actions + PCF deploy; **prod is gated** (`release-gate` →
  `production-change-gate`) and needs explicit human sign-off.
- **→ runbook-author:** when a change introduces new operational steps.

### Worked example — "ship feature X with tests and a runbook" (where to parallelize)

The flow above is a **sequential spine** with **one parallel burst**. The main session (via `route-request`) loads
[`parallelization`](../.claude/skills/parallelization/SKILL.md) to decide what runs at once:

```
 research (unknown API?) ─┐
                          ▼
              build feature X  (sde-engineer)            ── SEQUENTIAL (coupled; never fan out coding)
                          │  produces a diff
                          ▼
   ┌──────────── on the finished diff (sectioning) ───────────┐
   │  code-reviewer  ∥  security-reviewer  ∥  test-engineer    │ ── PARALLEL (independent lenses)
   └───────────────────────────┬──────────────────────────────┘
                               ▼  main session merges findings → one fix list
                       sde-engineer applies fixes  → re-verify   (evaluator-optimizer loop)
                               ▼
                          [merge-gate] ─▶ release-engineer ([release-gate] → [production-change-gate] → pcf-deploy)
                               ▼
                         runbook-author    (after final behavior + deploy steps are known)
```

- **Sequential** because it's coupled: the build (each edit depends on the last — *don't* fan out
  coding), and the gates (pass/fail checkpoints, prod needs human sign-off).
- **Parallel** because they're independent: 3 review lenses on the *same* diff (+ `researcher` up front
  if an API/spec is unknown). That's 3–4 strands — the right-sized band, run as fan-out **inside the
  main session**, not a costly multi-agent swarm.
- **Each strand** gets an isolated context + a bounded mandate and returns a **short summary**
  ([`context-engineering`](../.claude/skills/context-engineering/SKILL.md)); the main session does a
  **merge pass** (dedupe/reconcile) before routing one consolidated fix list back — the
  [`self-improve-loop`](../.claude/skills/self-improve-loop/SKILL.md) generate→evaluate→revise cycle.
- **runbook-author is downstream-gated**, not parallel with the build — it documents the *final*
  shipped behavior and real ops steps (it may draft once the design is frozen).

---

## Operate → mitigate → learn

```
  alert / "X is broken/slow" ─▶ sre-engineer ──(Sev1/Sev2)──▶ incident-command (incident-severity)
                                  │  │  │                          │ (process, severity, comms, timeline)
        researcher ◀─────────────┘  │  └─▶ release-engineer       ├─▶ main session runs strands:
        (unknown error / CVE,        │      (rollback-mitigation;   │    sre-engineer ∥ researcher ∥
         KEV first)                   │       deploy = cause)        │    release-engineer ∥ sde-engineer
                                      ▼                              ▼
                              sde-engineer                    runbook-author  ◀── capture what was learned
                              (durable root-cause fix)              ▲
                                      │                             │
                                      └──────────▶ sre-monitor ─────┘  (close the detection gap:
                                                   SLOs / alerts / dashboards)
```

- **sre-engineer** loads `sre-ladder` by depth (responder → investigator → elite) and
  `triage-golden-signals` to frame the signals; it **investigates and recommends**, it does **not**
  change prod.
- **sre-engineer + incident-command (`incident-severity`):** declare/run a major incident; technical RCA
  and process/comms run *in parallel*. `incident-severity` sizes severity, assigns roles, and owns the
  timeline + comms cadence — loaded in the main session.
- **sre-engineer → release-engineer:** to execute a mitigation (`rollback-mitigation`) — **with human
  confirmation**.
- **sre-engineer → database-reliability:** when the incident is DB-driven (slow queries, lock/connection-
  pool saturation, replication lag) — DBRE diagnoses and recommends; prod changes still go via
  `release-engineer` under `production-change-gate`.
- **sre-engineer → sde-engineer:** to implement the confirmed root-cause fix.
- **incident → runbook-author:** capture the procedure the incident exposed (with `blameless-postmortem`).
- **→ sre-monitor:** close the detection gap so the failure class can't recur silently.

### App vs. platform boundary (escalate out of the fleet)
We are an **application** team. When the root cause is **platform-side** — BOSH, Ops Manager, Diego
cells, Gorouter, the foundation itself, or certs/NTP — `sre-engineer` hands off to the **platform /
infrastructure team** (a human team outside this roster) **with evidence**: timestamps, scope, and `cf`
output showing our app is healthy. We recognize and escalate platform problems; we don't operate the
platform.

---

## Researcher supports everyone

```
  any agent ──(unknown: API contract, spec, lib behavior, CVE, version diff)──▶ researcher
                                                                                    │
                                          cited summary (labels sourced/unverified) │
  calling agent (or a human) acts ◀─────────────────────────────────────────────────┘
```

`researcher` is read-only and **hands back** — it doesn't write code, edit runbooks, push changes, or
make the decision. It absorbs expensive fact-finding and returns a brief, keeping the caller's context lean.

---

## The knowledge loop (how operational maturity compounds)

Incidents and postmortems feed **`runbook-author`**, who keeps runbooks current and linked to the alerts
(Splunk / Wavefront / Grafana / Moogsoft) that trigger them — and **`sre-monitor`** turns each detection
gap into an SLO/alert. So the next on-call starts from a better place than the last. This loop is the
team's main mechanism for getting more reliable over time.
