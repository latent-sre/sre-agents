---
name: merge-gate
description: >-
  Quality gate that must pass before a code change merges. Use as the checkpoint after code review and
  testing, before declaring a change "done" or merging a PR. A pass/fail checklist covering tests,
  review, security, coverage, secrets, compatibility, and docs. Run it (or invoke /merge-gate) to verify
  readiness.
---

# Merge gate

A change merges only when **all** of these pass. Any **NO** blocks the merge — fix it or get an explicit,
recorded waiver from a human owner.

## Checklist
- [ ] **Builds & CI green** — compile/lint/format and the full test suite pass in CI. Attach the
      evidence (CI link, or run output from a non-read-only agent such as `test-engineer`), not just a
      tick — an asserted "green" is `[unverified]`.
      > The **read-only agents cannot supply this themselves**: `code-reviewer`, `security-reviewer`,
      > and `sre-engineer` are blocked from running test suites and builds, because doing so executes
      > the code under review (`conftest.py`, npm lifecycle scripts). Take the evidence from CI or from
      > `test-engineer` — do not ask a reviewer to run the suite, and do not accept a reviewer's
      > second-hand "tests pass" as `[verified]`.
- [ ] **Behavior tested** — the change's new/changed lines are covered; new behavior has tests; any bug
      fix has a regression test that fails without the fix (`tdd-workflow`). Show that it ran.
- [ ] **Reviewed** — `code-reviewer` ran; all Critical/High findings are resolved (not just acknowledged).
- [ ] **Security** — if the change touches auth, input handling, secrets, crypto, file/network access,
      or dependencies → `security-reviewer` ran and must-fix items are closed.
- [ ] **No secrets** — no credentials/tokens/keys in code, fixtures, or logs.
- [ ] **Backward compatible** — no silent contract break; migrations ordered; expand→contract followed
      where a contract changed (`safe-refactor`). If an **HTTP API** changed, the OpenAPI spec matches the
      code and the change is backward-compatible for clients (`api-design`).
- [ ] **Web GUI (if touched)** — keyboard-accessible / WCAG checked or explicitly waived; no secrets in
      the bundle; tokens not in `localStorage` (`spa-architecture`).
- [ ] **Scoped & clean** — smallest correct change; no dead code, debug leftovers, or unrelated churn.
      Size matters: ~200–400 LOC is the effective review chunk; defect detection drops past ~400 LOC and
      above ~500 LOC/hr, so cap continuous review at 60–90 min. A reviewer may request a split **solely**
      for size — an oversized change is a blocking finding, not a nit.
- [ ] **Docs/ops updated** — if behavior or operations changed, docs and any affected runbook are
      updated (`runbook-author`), or explicitly noted as not needed.

## Verdict
```
merge-gate: PASS | BLOCKED
Blocking items: <the NOs, each with what's needed to clear it>
Waivers (if any): <item — approved by <human> — reason>
```

## Notes
- This gate is a checklist by default. In GitHub it should be backed by **branch protection** (required
  checks + required review) so it can't be skipped; in Claude Code, hardened with a hook.
- "Approved with nits" can merge if the nits are non-blocking and tracked. Critical/High cannot.
