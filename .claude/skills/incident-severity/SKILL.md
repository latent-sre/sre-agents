---
name: incident-severity
description: >-
  Severity rubric, communications cadence, and the incident-command process for running a live incident —
  classify SEV1–SEV4 by user impact × scope × trend; decide what each level triggers (declare, paging,
  comms cadence, postmortem); assign roles, keep the authoritative timeline, drive to mitigation, and send
  the initial/update/resolution updates. Use the moment you must assign a severity, run the incident
  (who's doing what), or send a status update. Pairs with sre-ladder (responder tier) and
  blameless-postmortem.
metadata:
  domain: incident
---

# Incident severity, command & communications

The first consequential call in any incident is **"how bad is this, and who needs to know?"** This skill
makes that call repeatable. **Over-classify, then downgrade** — declaring is cheap; under-declaring is
expensive. Set a *provisional* severity in the first minutes from what you can see, and revise as the
blast radius becomes clear.

## Severity rubric (round up when unsure)

| SEV | Definition (user impact × scope) | What it triggers |
|-----|----------------------------------|------------------|
| **SEV1** | Customer-facing outage for all/most users, **or** data-loss / integrity / security event | Declare **now**; assign an incident commander (run the process below); page on-call + service owner + leadership; status updates every **15 min**; full blameless postmortem |
| **SEV2** | Major degradation, or a single critical service/journey down for a subset of users | Declare; assign an incident commander (run the process below); page on-call + service owner; updates every **30 min**; postmortem required |
| **SEV3** | Minor / contained impairment; core journeys work or a workaround exists | On-call owns the lifecycle; no IC required; update stakeholders at start + resolution; abbreviated postmortem |
| **SEV4** | Cosmetic / informational; no user impact | Normal work queue; no incident process |

## How to classify
- **Impact × scope × trend.** Multiply *how bad for a user* by *how many users / which journeys*, then
  weigh *direction* — a SEV3 that's **growing** is escalating toward SEV2; say so and re-page.
- **Bound the blast radius.** One app/route/instance ⇒ likely app-side (yours). Many apps at once, or
  failing/evacuating Diego cells ⇒ platform-side ⇒ escalate to the platform team with evidence (see
  `pcf-ops`). If you **can't yet bound** the blast radius, that alone justifies SEV2 and declaring.
- **Time-box the responder.** First on scene and not stabilized in **~15 min**, or the impact is
  growing → declare and assign an incident commander (run the process below); don't keep digging solo (`sre-ladder`, responder tier).

## Running the incident (command)
Once declared, someone owns the **response** — the **incident commander** (often the on-call lead). The IC
runs the *process*, not the debugging, keeping the response organized so it moves toward mitigation.
- **Coordinate, don't solo-debug.** The moment the IC is heads-down in logs, nobody is commanding.
  Delegate technical RCA to `sre-engineer` and remediation to `release-engineer`; the IC keeps the response organized.
- **Mitigate first.** User pain stops before root cause is found — push for the fastest safe, reversible
  mitigation (`rollback-mitigation`) and make that call explicit.
- **One source of truth.** Keep a single running **timeline** (UTC) of what's known, what's been tried, and what's next.
- **Assign roles:** Investigation lead (`sre-engineer`), Ops/remediation (`release-engineer`), Comms/scribe
  (the IC, or a delegate on a large SEV1). Confirm who owns what.
- **Track every action** — each "someone should…" becomes an owned, tracked item.
- **Resolve & close.** Confirm impact has ended (verify via `sre-monitor`/the investigator), send the
  **Resolution** update, and schedule the `blameless-postmortem`, seeded from the timeline.

### Status — one authoritative block, kept live
```
Incident: <title>   Severity: <SEV-n>   Status: <investigating|mitigating|monitoring|resolved>
Impact: <who/what, since when, trend>
Roles: Investigation=<>, Ops=<>, Comms=<>
Timeline (UTC): <ts — event/decision> …
Current focus: <the one thing the response is doing now>
Mitigation decision: <chosen / pending — rationale>
Open action items: <owner — item — status>
Next update: <time>
```

## Communications cadence
Update on the **fixed cadence for the severity above, even when there is no news** ("still investigating,
next update by HH:MM") — silence reads as loss of control. Keep it honest and jargon-free: never overstate
confidence or understate impact. For SEV1, the first external update should go out within the hour.
For a large SEV1, split **Comms lead** and **Scribe** off from the IC; otherwise the IC owns both.

### Templates
- **Initial** — *What we know* (symptom + impact), *Severity*, *Scope* (who/what affected, since when),
  *We are investigating*, *Next update by* `<HH:MM UTC>`.
- **Update** — *What changed since last update*, *Current status* (investigating | mitigating |
  monitoring), *Mitigation in progress / ETA*, *Next update by* `<HH:MM UTC>`.
- **Resolution** — *Impact has ended* (and since when), *Root-cause summary* (or "under investigation"),
  *What we did*, *Follow-ups + owners*, *Postmortem to follow* (SEV1/SEV2).

## Downgrade & resolve
Downgrade or resolve only when the **golden signals are back to baseline and stay there** for a
sustained window (not just "the graph turned green" — a metastable system can re-break). Verify recovery
via `sre-monitor`/the investigator before you call it, then send the **Resolution** update and schedule
the postmortem (`blameless-postmortem`).

## Pairs with
- `sre-ladder` (responder tier) — uses this rubric to decide severity and escalate.
- `rollback-mitigation` — the fastest-safe mitigation while a SEV1/SEV2 is open.
- `blameless-postmortem` — required after SEV1/SEV2, seeded from the IC timeline.
