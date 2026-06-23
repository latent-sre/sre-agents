# Deferred follow-ups (review gauntlet, 2026-06-23)

Strategic work surfaced by the 8-review gauntlet but **deliberately deferred** out of the docs-fix pass,
captured here so it isn't lost. Each item has a one-line *why*. None of these are blockers for the current
branch; they are the next-order improvements that move the fleet from "structurally sound" to
"actually adopted and actually safe in prod."

- [ ] **Finish the placeholder content.** De-placeholder the 3 runbooks (`runbooks/*.md`, all still marked
  "TEMPLATE — not yet live") and the ~8/9 stack `references/*.md` files (foundation URLs, Splunk indexes,
  Wavefront metrics, Grafana dashboards). *Why: this is the real user-value gap — the fleet's
  stack-specific differentiator is unfilled, and it needs the team's actual environment values to be live.*

- [ ] **Stand up the REAL prod control.** Configure GitHub branch protection + protected environments
  (required reviewers) and OS-level least-privilege / read-only CF credentials. *Why: every guard and gate
  in this repo is an honestly-labeled speed-bump; the load-bearing control lives in GitHub/IAM settings
  OUTSIDE this repo and is not set up here.*

- [ ] **Promote one deterministic behavioral eval to a soft CI gate.** Start with the gate-BLOCK and
  injection-resistance scenarios. *Why: those outcomes are deterministic (unlike stochastic routing), but
  today CI only runs structural `--validate` checks, so a behavioral regression can merge unnoticed.*

- [ ] **Run the ADR-0001 nested-subagent A/B revisit.** Now that nested dispatch exists, measure whether a
  dispatch-capable coordinator agent actually beats `route-request`-as-skill (via `evals/discovery_probe.py`
  + the routing scenarios). *Why: keep the status quo on measured evidence, not on the cost argument alone —
  the obsolete capability premise has been removed from ADR-0001.*

- [ ] **Evaluate trimming surface area (devil's-advocate challenge).** Consider consolidating the 3 gates
  toward 2 (build-ready vs. authorized-to-act); sharpen the ~4 weak skill descriptions
  (`handoff-protocol`, `triage-golden-signals`, `safe-refactor` overlap) for cleaner auto-discovery; weigh
  the ongoing cost of the `.github/` mirror. *Why: less surface area means better auto-routing and lower
  maintenance — challenge every artifact that has to earn its keep.*

- [ ] **Build a `/configure-fleet` (or `SETUP.md`) onboarding wizard.** Turn the currently-invisible
  half-day of filling placeholders into a guided ~15-minute fill-in. *Why: the operability review's
  highest-leverage adoption lever — make first-run setup obvious and fast instead of latent.*
