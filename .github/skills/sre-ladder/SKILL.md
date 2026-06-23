---
name: sre-ladder
description: >-
  Set your SRE altitude for an alert or incident, then load the matching tier — match response depth to
  the situation. Use at the start of any detection/triage/investigation work: responder (safe first
  response — golden signals, read-only checks, work the runbook, decide severity, escalate), investigator
  (hypothesis-driven RCA — build a timeline, correlate "what changed", test hypotheses against evidence),
  or elite (systemic/distributed failure analysis and prevention). Read the one tier file for the method.
metadata:
  domain: ladder
  track: sre
---

# SRE ladder — pick your altitude

Match response depth to the situation; escalate a tier the moment the current one isn't enough. Load
**only** the tier that matches.

- **Responder** *(first on scene, any seniority)* — read the golden signals, run safe read-only checks,
  work the linked runbook, decide severity, escalate well; do no harm. → [`references/responder.md`](references/responder.md)
- **Investigator** — own the hunt for the actual cause: timeline, "what changed", a differential of
  hypotheses tested against evidence. → [`references/investigator.md`](references/investigator.md)
- **Elite** — systemic/distributed failure modes (cascades, retry storms, saturation collapse,
  metastable failure) and closing the detection gap so the class can't recur. → [`references/elite.md`](references/elite.md)
