---
name: production-change-gate
description: >-
  Change-**authorization** checkpoint for ANY production-facing or destructive action — deploys,
  route/traffic changes, scaling, config flips, data changes, cf writes (including changes that aren't
  releases). Use immediately before executing to confirm human approval, blast-radius assessment, a
  reversible backout plan, an authorized executor, comms, and monitoring. Enforces that prod changes
  need explicit human sign-off. (`release-gate` checks build readiness; this authorizes the action.)
---

# Production change gate

Any action that touches production must clear this gate **before execution**. This is the embodiment of
our **"prod-facing actions require explicit human confirmation"** rule. `sre-engineer`/`sde-engineer`
*recommend*; a human release owner *executes*; a human *approves*.

> **The checklist is not the enforcement.** This gate is a discipline a *cooperating* agent runs; on its
> own it stops nothing. The load-bearing control for prod is **GitHub branch protection + protected
> environments with required reviewers** (see CLAUDE.md) — and only if *Allow administrators to bypass
> protection rules* is disabled (it is ON by default). Treat this checklist as the human-decision record
> that rides on top of that boundary, **not** as the boundary itself.

> **How it layers with `release-gate`:** `release-gate` checks whether a *build/release* is **ready** to
> ship (artifact, migrations, flags, rollback). This gate authorizes the **prod change itself** — and
> applies equally to changes that **aren't** releases (a scale, a route remap, a config flip, a data
> change). A prod release clears `release-gate` **then** this gate; a non-release prod change clears only
> this one.

## Checklist
- [ ] **The boundary is actually ON** — verified, not assumed. Everything below is a *record*; branch
      protection is the *control*, and it ships OFF by default. Check it:

      gh api repos/{owner}/{repo}/branches/{branch}/protection \
        --jq '{enforce_admins: .enforce_admins.enabled,
               required_reviews: .required_pull_request_reviews.required_approving_review_count,
               dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews}'

      `enforce_admins` must be **true** (that is GitHub's *Allow administrators to bypass protection
      rules*, **disabled**). If it is `false` — or the call **404s**, meaning the branch has no protection
      at all — this gate is decoration: **BLOCK**, and fix the setting before any prod change. Record the
      output; an unverified boundary makes every item below `[unverified]` too.
- [ ] **Approved** — an authorized human has explicitly approved this specific change now (and a change
      record exists if your process / CAB requires one).
- [ ] **Blast radius understood** — what this affects (which apps/routes/spaces/users, % of traffic) and
      the worst case if it goes wrong, written down.
- [ ] **Backout plan, reversible** — the exact rollback is documented and known-good; prefer actions
      reversible in seconds (blue-green route remap, flag flip) over irreversible ones
      (`rollback-mitigation`).
- [ ] **Authorized executor** — run by the right role with least-privilege creds; not bypassing review or
      gates. No ad-hoc prod edits.
- [ ] **Plan/diff shown** — the command(s) and the manifest/config diff have been shown and confirmed —
      no surprise side effects.
- [ ] **Timing** — appropriate window considered (avoid peak / freeze periods unless it's an emergency
      mitigation); maintenance window or suppression set in Moogsoft if needed.
- [ ] **Monitoring during change** — someone is watching the golden signals; abort criteria are agreed.
- [ ] **Comms** — stakeholders/on-call notified before and after.

## Verdict
```
production-change-gate: APPROVED | BLOCKED
Change: <what, where>   Approved by: <human>   When: <UTC>
Backout: <exact reversible steps>
Watching: <who, which signals>   Abort if: <criteria>
```

## Emergency exception
During a declared incident, mitigation speed can outweigh full process — but **never skip human
confirmation and a backout plan**. Record the emergency decision and who made it; reconcile the change
record afterward.
