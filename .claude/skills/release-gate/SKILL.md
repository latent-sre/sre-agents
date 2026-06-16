---
name: release-gate
description: >-
  Pre-release readiness gate that must pass before a deploy/release. Use as the checkpoint before
  shipping a build to an environment (especially prod) — verifies the change is mergeable, the artifact
  is promotable, migrations and flags are ready, monitoring is in place, and the rollback is written and
  reversible. Pass/fail checklist; pairs with production-change-gate for prod.
metadata:
  domain: gate
---

# Release gate

A release proceeds only when **all** of these pass. Owned by `release-engineer`. For a prod target, also
clear **`production-change-gate`**.

## Checklist
- [ ] **Merge gate passed** — the change is reviewed, tested, secure (`merge-gate`).
- [ ] **Versioned & noted** — version bumped; changelog / release notes written.
- [ ] **One artifact, promoted** — the exact artifact tested in lower envs is the one shipping (build
      once, promote — not a rebuild).
- [ ] **Migrations safe** — DB/schema/config migrations are backward-compatible and ordered to run
      before the code that needs them (expand→contract); each is independently reversible.
- [ ] **Feature flags ready** — risky behavior is flag-gated and defaults safe; flag flip is tested.
- [ ] **Rollback written & reversible** — the exact rollback command/steps are documented and known to
      work (`rollback-mitigation`); for PCF, blue-green route remap or `cf rollback` is available.
- [ ] **Health gates & abort criteria** — success/failure signals defined up front (golden signals in
      Wavefront/Grafana); you know what trips an abort.
- [ ] **Monitoring in place** — alerts/SLOs cover the new behavior; new paging alerts link a runbook
      (`sre-monitor`).
- [ ] **Comms ready** — stakeholders/on-call know the deploy window; status updates planned.

## Verdict
```
release-gate: PASS | BLOCKED
Target: <org/space/env>   Strategy: <blue-green|rolling|canary|flag>
Rollback: <exact steps>
Blocking items: <the NOs>
```

## Notes
- Back this with a GitHub **environment + required reviewers** so the deploy job literally pauses for
  approval (`github-actions-ci`).
- A release you can't cleanly roll back does not pass this gate — fix the rollback first.
