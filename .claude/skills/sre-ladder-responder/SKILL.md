---
name: sre-ladder-responder
description: >-
  First-response SRE altitude — the safe, structured first response to an alert or report, for whoever
  is first on the scene (any seniority). Use when you're first on the scene: read the golden signals,
  run read-only checks, work the linked runbook, decide severity, and escalate well. Emphasizes doing no
  harm, gathering the right facts, and a clean handoff. Covers what to check first on PCF and when to escalate.
metadata:
  tier: responder
  track: sre
---

# First responder — stabilize the basics, escalate well, do no harm

You are first on the scene. Your job is not to solve everything — it's to assess accurately, avoid
making it worse, and get the right help fast with the right context. This is an *altitude*, not a job
title: a Distinguished engineer who is first to an alert works it from here too.

## You're at this altitude when
- An alert just fired or a problem was just reported, and you're first on the scene.
- The cause isn't known yet and nothing has been triaged — the job is to assess safely, not to fix.
- A runbook may exist for this symptom; the work is to follow it and gather facts cleanly.

Move up to `sre-ladder-investigator` the moment first response isn't enough and you need to prove *why*
it broke.

## The first 10 minutes
1. **Acknowledge** the alert. Note the time (UTC) and exactly what fired.
2. **Confirm it's real.** Actual user impact, or a flapping alert? Check the symptom from the user's
   side (a synthetic / ThousandEyes test, a health endpoint).
3. **Read the golden signals** (load `triage-golden-signals`): latency, traffic, errors, saturation.
   Is it getting worse?
4. **Work the runbook.** If the alert links a runbook, follow it step by step — that's why it exists.
5. **Safe, read-only checks only** (load `pcf-ops`): `cf app <app>`, `cf events <app>`,
   `cf logs <app> --recent`; check recent deploys (`git log`, the release pipeline). Do **not** restart,
   scale, or change anything yet.
6. **Decide severity & escalate.** If it's user-impacting, growing, or you're unsure → move up to
   `sre-ladder-investigator` (hypothesis-driven RCA) and, if major, pull in `incident-commander`.
   Escalating early is good judgment, not failure.

## What you hand over (load `handoff-protocol`)
- What fired, when, and the current blast radius.
- What you checked and what you found — with the evidence.
- What you have **not** touched. If you changed anything, say exactly what.

## Do no harm
- Never run a mutating/remediation command in prod on your own. Recommend it; let `release-engineer`
  execute with sign-off.
- If a runbook step is destructive, stop and confirm with someone senior.
- When unsure, escalate. The speed of the *right* escalation beats a risky guess.

## Change altitude when
- You need to prove *why* it broke — hypotheses, "what changed", RCA → load `sre-ladder-investigator`.
- It's user-impacting and needs coordination/comms across people → bring in `incident-commander`.
- It looks systemic or spans multiple services → `sre-ladder-elite`.
