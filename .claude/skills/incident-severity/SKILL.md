---
name: incident-severity
description: >-
  Severity rubric and stakeholder-communications cadence for an incident — classify SEV1–SEV4 by user
  impact × scope × trend, decide what each level triggers (declare, incident-commander, paging, comms
  cadence, postmortem), and send the initial/update/resolution updates. Use the moment you must assign a
  severity or send a status update. Pairs with incident-commander, sre-ladder-responder, and
  blameless-postmortem.
metadata:
  domain: incident
---

# Incident severity & communications

The first consequential call in any incident is **"how bad is this, and who needs to know?"** This skill
makes that call repeatable. **Over-classify, then downgrade** — declaring is cheap; under-declaring is
expensive. Set a *provisional* severity in the first minutes from what you can see, and revise as the
blast radius becomes clear.

## Severity rubric (round up when unsure)

| SEV | Definition (user impact × scope) | What it triggers |
|-----|----------------------------------|------------------|
| **SEV1** | Customer-facing outage for all/most users, **or** data-loss / integrity / security event | Declare **now**; engage `incident-commander`; page on-call + service owner + leadership; status updates every **15 min**; full blameless postmortem |
| **SEV2** | Major degradation, or a single critical service/journey down for a subset of users | Declare; engage `incident-commander`; page on-call + service owner; updates every **30 min**; postmortem required |
| **SEV3** | Minor / contained impairment; core journeys work or a workaround exists | On-call owns the lifecycle; no IC required; update stakeholders at start + resolution; abbreviated postmortem |
| **SEV4** | Cosmetic / informational; no user impact | Normal work queue; no incident process |

## How to classify
- **Impact × scope × trend.** Multiply *how bad for a user* by *how many users / which journeys*, then
  weigh *direction* — a SEV3 that's **growing** is escalating toward SEV2; say so and re-page.
- **Bound the blast radius.** One app/route/instance ⇒ likely app-side (yours). Many apps at once, or
  failing/evacuating Diego cells ⇒ platform-side ⇒ escalate to the platform team with evidence (see
  `pcf-ops`). If you **can't yet bound** the blast radius, that alone justifies SEV2 and declaring.
- **Time-box the responder.** First on scene and not stabilized in **~15 min**, or the impact is
  growing → declare and pull in `incident-commander`; don't keep digging solo (`sre-ladder-responder`).

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
- `incident-commander` — owns declaration, roles, the timeline, and sending these updates.
- `sre-ladder-responder` — uses this rubric to decide severity and escalate.
- `rollback-mitigation` — the fastest-safe mitigation while a SEV1/SEV2 is open.
- `blameless-postmortem` — required after SEV1/SEV2, seeded from the IC timeline.
