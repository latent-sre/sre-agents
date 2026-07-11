---
name: sre-ladder
description: >-
  Use at the start of operational detection, triage, or incident investigation to choose responder,
  investigator, or elite depth. Do not use for a single log, metric, network, or PCF query.
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
