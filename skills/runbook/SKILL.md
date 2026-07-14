---
name: runbook
description: >-
  Write or update an operational runbook or operating doc — how to check, restart, and recover a
  service, written for the stressed 3am reader. Triggers: 'write a runbook', 'document this
  procedure', 'how do we handle X at 3am'. Every slot is filled or marked 'n/a — why'; commands
  carry evidence labels. Ownership map only—not a load: canonical `postmortem` owns post-incident
  retrospective structure.
argument-hint: "[service or tool]"
---

Runbooks are read at 3 a.m. by someone who is tired — usually future-you. Terse, copy-pasteable, zero ambiguity.

Investigate before writing: read the actual config, compose/unit files, and any existing docs. A runbook written from memory documents the lab you *think* you have.

## Required structure (every slot filled or marked "n/a — why")

Full fill-in template: [runbook template](./assets/runbook-template.md) — copy it to start.

```
# <Service> runbook
- What/why: one sentence; who notices if it's down.
- Where: host, config path in the repo, data path, URL(s).
- Health: the exact command or URL that shows it's healthy, and what good output looks like.
- Restart: exact commands in order, including the wait-and-verify step.
- Common failures: symptom → likely cause → fix, one line each.
- Recovery: the restore-from-backup path with exact commands; when to stop repairing and restore.
- Dependencies: what it needs (DNS, DB, proxy) and what depends on it.
```

Rules:
- Every command copy-pasteable as written — real paths and real names. A `<placeholder>` is allowed only for truly variable values, and then say where to find the value.
- "Common failures" lists only what has been observed or is clearly plausible for this service — no padding to make the section look complete.
- If you couldn't verify a command works (service not running, no access), mark it `[unverified]` rather than presenting it as tested.

## Runbook vs playbook vs SOP
- **Runbook** — steps to handle *one* alert/task/failure mode (this template).
- **Playbook** — a broader response *strategy* orchestrating multiple runbooks (e.g. a major-incident
  playbook). Ownership map only—not a load: canonical `incident-command` owns live-incident coordination.
- **SOP** — a fixed procedure for routine operations (not incident-driven).

Keep them current the only way that works: **rehearse them.** Run game days / drills under realistic
conditions, and bump `last_verified` after each.

## Authoring rules
- **Numbered, imperative steps.** Copy-pasteable commands with real values or clearly templated
  `<PLACEHOLDER>`s. No "obviously" or "just".
- **Expected output per step** — so the reader knows it worked before moving on.
- **Verify and roll back** — every state-changing action has "how to confirm it worked" and "how to undo
  it." Mark destructive steps with a warning. Tier 2/3: record explicit human approval for the exact
  command/target plus rollback evidence before execution.
- **Trigger-anchored** — starts from a concrete trigger (this alert/symptom/task), ends at "resolved or
  escalate to <whom>."
- **Current or deleted** — date it, own it, prune what's wrong. A wrong runbook is worse than none.
- **Machine-linkable frontmatter** — give each runbook YAML frontmatter (`alert_names`, `owner`,
  `severity`, `last_verified`, `version`) so alerts auto-link and a linter can flag any not
  verified in ~90 days.
- **Verify commands before publishing** — run read-only ones to confirm syntax; never run destructive
  steps to "test" them; mark anything `[unverified]`.

## Alert → runbook links and the Crawl → Walk → Run path

Link every paging alert to its runbook. When investigation is needed, hand the trigger and evidence
to the `sre` agent; when code remediation is needed, hand the defect and evidence to the `sde` agent.
If a step is fully mechanical, recommend automating it along the **Crawl → Walk → Run** path: document
the manual steps (crawl), wrap them in a checked script the on-call runs by hand (walk), then trigger
it automatically once proven (run). Data-drive the alert→runbook link so saved searches/alerts surface
the right runbook automatically — each tool in our stack has a mechanism:
- **Splunk:** `... | lookup instructions_lookup alert_type OUTPUT runbook_url`.
- **Grafana:** a `runbook_url` annotation on the alert rule (templated by labels).
- **Wavefront:** the alert's resolution/runbook link, with Mustache-templated targets.
- **Moogsoft:** enrichment that attaches the runbook URL + escalation path to the alert/Situation.

### Worked excerpt — tier-marked steps with provenance

> **Trigger**: alert `checkout-p95-burn-fast` (page).
> **First checks**: `cf app checkout` → expect `6/6 running` [sourced] (incident #2026-07-02 transcript).
> **Procedure step 1** ⚠️ (Tier 2 — needs explicit human approval for this command/target):
> `cf restart-app-instance checkout <idx>` — restarts ONE instance; the other five keep serving.
> **Verification**: p95 back under 800 ms within 10 min on the checkout dashboard.
> **Rollback**: none needed — the restart is the reset. If step 1 ran twice without effect, STOP:
> restart is a stopgap, not a fix — escalate per the Escalation table.
> **Provenance**: first checks and procedure step 1 [sourced] from incident #2026-07-02 transcript;
> any later step is [unverified] until a human tests it before this runbook is trusted at 3 a.m.
