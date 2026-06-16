# Runbook: <concise title / the alert this answers>

> **Owner:** <team/role>  ·  **Last reviewed:** <YYYY-MM-DD>  ·  **Severity:** <SEV-n / page|ticket>

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
> Mark destructive steps ⚠️ and require confirmation (production-change-gate).

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
- Escalate to <role/team> if <condition / time elapsed>.
- Hand over (handoff-protocol): symptom, what you tried, current state, what you did NOT touch.

## References
- Related runbooks: <…>
- Postmortems: <…>
- Alert definition / SLO: <…>
