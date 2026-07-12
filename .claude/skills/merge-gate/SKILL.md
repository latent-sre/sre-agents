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

Throughout, **`HEAD` means the tip commit of the branch being merged — the PR head — not your local
checkout** (reviewing a PR from a local `main` would otherwise resolve `HEAD` to main's tip and block
everything).

## Checklist
- [ ] **Builds & CI green** — compile/lint/format and the full test suite pass **in CI**. Attach the
      **CI run link**, not just a tick — an asserted "green" is `[unverified]`.
      > **CI is the execution boundary, and for untrusted code it is the ONLY one.** Running a suite
      > executes the code under test (`conftest.py`, npm lifecycle scripts, `go test` compiles the
      > tree). For a diff from outside the team — a fork PR, an external contributor, a dependency
      > bump — that is arbitrary code chosen by its author, so it must run in CI's ephemeral,
      > credential-scoped runner. Not on a developer's box, and not inside an agent.
      >
      > **Do not launder this through `test-engineer`.** The read-only agents (`code-reviewer`,
      > `security-reviewer`, `sre-engineer`) are blocked from running suites — but `test-engineer` has
      > **unguarded `Bash` plus `Write`/`Edit`**, so asking *it* to run an untrusted suite is strictly
      > *worse* than letting the reviewer do it: same arbitrary execution, more privilege. Delegation
      > is not isolation. `test-engineer` runs suites for code **the team authored**; it is not a
      > sandbox and must not be used as one.
      >
      > We do **not** currently have a credential-less isolated runner for agent-initiated test
      > execution. Until we do, untrusted-diff test evidence comes from CI or it does not exist.
- [ ] **Behavior tested** — the change's new/changed lines are covered; new behavior has tests; any bug
      fix has a regression test that fails without the fix (`tdd-workflow`). Show that it ran, **and record
      the SHA it ran at**. If that SHA != `HEAD`, apply the same staleness test as below: empty or
      test-irrelevant diff → re-confirm and record `HEAD`; otherwise the evidence is stale — **re-run**.
- [ ] **Reviewed** — `code-reviewer` ran; all Critical/High findings are resolved (not just acknowledged).
      **Record the SHA the review ran against.** If that SHA != `HEAD`, diff them (`git diff <review-sha>..HEAD`).
      If the diff is **empty** (rebase, `--amend`, a merge of the base branch) or touches only files outside
      the reviewed set, **re-confirm and record the new SHA — no re-review needed.** If it touches reviewed
      code, the approval is stale — a later fix can break what was approved — so re-derive the diff
      (`handoff-protocol`) and this item is a **NO** until the new commits are reviewed.
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
- **The stale-approval check above is a self-run speed-bump, not the control.** The enforcement is branch
  protection's **"Dismiss stale pull request approvals when new commits are pushed"** — it invalidates the
  approval mechanically when a later fix lands, whether or not the agent runs this checklist. Turn it on;
  don't rely on the tick-box.
- "Approved with nits" can merge if the nits are non-blocking and tracked. Critical/High cannot.
