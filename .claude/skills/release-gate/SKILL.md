---
name: release-gate
description: >-
  Use before releasing a build to decide whether its artifact, migrations, flags, monitoring,
  communications, and rollback are ready. Do not use to authorize execution of a production change.
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
      work (`rollback-mitigation`); for PCF, blue-green route remap (or `cf rollback`, if app revisions
      are enabled) is available.
- [ ] **Health gates & abort criteria** — success/failure signals defined up front (golden signals in
      Wavefront/Grafana); you know what trips an abort.
- [ ] **Monitoring in place** — alerts/SLOs cover the new behavior; new paging alerts link a runbook
      (`sre-monitor`).
- [ ] **Comms ready** — stakeholders/on-call know the deploy window; status updates planned.
- [ ] **(Prod only) `production-change-gate` is queued as a prerequisite** — release-gate confirms build
      *readiness* only; it **cannot** authorize a prod action. Prod releases additionally require a
      separate `production-change-gate` sign-off (GitHub environment + required reviewers) *before* the
      deploy runs. Check this box to confirm that gate is lined up — not that it is granted here.

## Verdict
```
release-gate: PASS | BLOCKED
Target: <org/space/env>   Strategy: <blue-green|rolling|canary|flag>
Rollback: <exact steps>
Blocking items: <the NOs>
```

## Notes
- **Gate topology:** release-gate **absorbs** `merge-gate` as a precondition (first line item above),
  but `production-change-gate` is a **separate, later** gate that authorizes the prod action. release-gate
  checks build **readiness** only and never grants prod authorization in-checklist — the prod line item
  is a *prerequisite pointer* to `production-change-gate`, not an approval; that gate must still be
  cleared on its own and must not be skipped.
- Back this with a GitHub **environment + required reviewers** so the deploy job literally pauses for
  approval (`github-actions-ci`).
- A release you can't cleanly roll back does not pass this gate — fix the rollback first.
