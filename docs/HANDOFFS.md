# Handoff map

A "handoff" here means: a specialist finishes, returns a **structured summary**, and names **who picks
up next**. Classic Claude Code subagents **cannot call each other** — only the main session delegates —
so the `coordinator` and `incident-commander` emit an *ordered plan* (see
[ARCHITECTURE.md §4](ARCHITECTURE.md)) and the main thread routes between agents. Each agent's body
lists its own handoff targets; this is the fleet-wide picture. Package context with `handoff-protocol`.

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
   request ─────────────▶ coordinator ──(delegation plan)──┐
      │  (single obvious task: route directly)              │
      ▼                                                     ▼
  sde-engineer ──(load sde-ladder-* by altitude)──▶ code-reviewer ──▶ [merge-gate] ──▶ release-engineer
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

- **coordinator → everyone:** produces the plan; the main session executes it. Skip it for one obvious task.
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

---

## Operate → mitigate → learn

```
  alert / "X is broken/slow" ─▶ sre-engineer ──(Sev1/Sev2)──▶ incident-commander
                                  │  │  │                          │ (process, severity, comms, timeline)
        researcher ◀─────────────┘  │  └─▶ release-engineer       ├─▶ coordinates strands:
        (unknown error / CVE,        │      (rollback-mitigation;   │    sre-engineer ∥ researcher ∥
         KEV first)                   │       deploy = cause)        │    release-engineer ∥ sde-engineer
                                      ▼                              ▼
                              sde-engineer                    runbook-author  ◀── capture what was learned
                              (durable root-cause fix)              ▲
                                      │                             │
                                      └──────────▶ sre-monitor ─────┘  (close the detection gap:
                                                   SLOs / alerts / dashboards)
```

- **sre-engineer** loads `sre-ladder-*` by depth (responder → investigator → elite) and
  `triage-golden-signals` to frame the signals; it **investigates and recommends**, it does **not**
  change prod.
- **sre-engineer ⇄ incident-commander:** declare/run a major incident; technical RCA and process/comms
  run *in parallel*. The commander sizes severity with `incident-severity` (SEV1–4 + comms cadence).
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
