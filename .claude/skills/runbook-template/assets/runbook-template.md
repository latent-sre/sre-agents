---
alert_names: [<exact alert name(s) that link here>]
owner: <team/role>
severity: <SEV-n / page | ticket>
last_verified: <YYYY-MM-DD>
version: 1
---

# Runbook: <concise title / the alert this answers>

## Purpose & scope
What this runbook handles: <…>
**Out of scope** (do NOT use this for): <…>

## Trigger
The exact alert/symptom that brings you here: <alert name + condition, or observed symptom>
Dashboard: <link>  ·  Source/repo: <link>

## Prerequisites
- Access: <roles, foundation/space, VPN, tools>
- Tools: <cf CLI v8, Splunk, Wavefront, …>
- Useful links: <dashboard, saved search, prior postmortem>

## Triage / first checks
1. Confirm impact (golden signals): <where to look>
2. Decision tree:
   - If <condition A> → go to Procedure step <n>.
   - If <condition B> → this isn't the right runbook; see <other runbook> / escalate.

## Procedure
> Mark destructive steps ⚠️; require confirmation (production-change-gate).

1. <imperative step>
   ```bash
   <command>
   ```
   Expected: <what you should see>
2. <next step> …

## Verification
How to confirm the issue is resolved: <command/dashboard + expected healthy state>

## Rollback / cleanup
How to undo each change above (reverse order): <exact steps>
Safe-abort: <how to stop mid-procedure without making it worse>

## Escalation
| When (condition / time elapsed) | Escalate to | How to reach |
|---|---|---|
| <e.g. not resolved in 15 min, or blast radius growing> | <role/team> | <pager / channel> |
| <platform-side signal: many apps / failing cells> | platform team | <…> |

Hand over (handoff-protocol): symptom, what you tried, current state, what you did NOT touch.

## Communication
- Notify: <channel / stakeholders> · Cadence while active: <e.g. every 30 min per `incident-severity`>
- Initial / update / resolved message owner: <role>

## Post-Incident
- [ ] **Update this runbook** with anything learned, and bump `last_verified`.
- [ ] File follow-up **automation candidates** (Crawl→Walk→Run) as tickets.
- [ ] If this was an incident, link the postmortem here and feed action items back in.

## References
- Related runbooks: <…>
- Postmortems: <…>
- Alert definition / SLO: <…>
