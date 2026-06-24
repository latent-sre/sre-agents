# Deferred follow-ups (review gauntlet, 2026-06-23)

> **2026-06-23 — surface-area review settled.** A 9-scan gauntlet (5 independent + 2 devil's-advocate
> + 2 Anthropic-best-practice) examined whether to consolidate and **VALIDATED the 10 agents / ~38
> skills counts** (8/9 keep 10 agents, 7/9 keep ~38 skills). Decision: **keep the counts**, do NOT add
> comms/FinOps lanes, and **fill + tier** instead of cut. The adoption tiering lives in
> [`docs/ADOPTION.md`](ADOPTION.md). Count-cutting is **resolved**; the live work below is
> description-sharpening, machinery cuts, and content-filling.

Strategic work surfaced by the 8-review gauntlet but **deliberately deferred** out of the docs-fix pass,
captured here so it isn't lost. Each item has a one-line *why*. None of these are blockers for the current
branch; they are the next-order improvements that move the fleet from "structurally sound" to
"actually adopted and actually safe in prod."

- [ ] **Finish the placeholder content — #1 PRIORITY (per the 2026-06-23 adoption review).** De-placeholder
  the 3 runbooks (`runbooks/*.md`, all still marked "TEMPLATE — not yet live") and the stack
  `references/*.md` files (foundation URLs, Splunk indexes, Wavefront metrics, Grafana dashboards). *Why:
  this is the real user-value gap — the fleet's stack-specific differentiator is unfilled, and it needs the
  team's actual environment values to be live. The adoption guide names the first fill-in jobs:
  [`docs/ADOPTION.md`](ADOPTION.md#the-first-fill-in-jobs).*

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

- [ ] **Trim surface area — COUNT-cutting half RESOLVED, refinement half LIVE.** The 2026-06-23 9-scan
  review settled the count question: **keep 10 agents / ~38 skills** (do not consolidate the roster). The
  remaining work is *not* deletion: (a) **description-sharpening** *(in progress)* — sharpen the ~4 weak
  skill descriptions (`handoff-protocol`, `triage-golden-signals`, `safe-refactor` overlap) for cleaner
  auto-discovery; (b) **machinery cuts** — consider consolidating the 3 gates toward 2 (build-ready vs.
  authorized-to-act) and weigh the ongoing cost of the `.github/` mirror and the over-built CI machinery.
  *Why: better auto-routing and lower maintenance — but on artifacts, not on agent/skill counts, which the
  review validated.*

- [ ] **(Optional) Generate a github.com Copilot *coding-agent* wrapper variant.** The committed
  `.github/agents/*.agent.md` target **VS Code Copilot** (the `search`/`edit`/`runCommands` toolset
  vocabulary the generator emits — `runCommands` is the correct VS Code terminal tool). The **github.com
  Copilot coding agent** uses a *different, incompatible* tool vocabulary (e.g. `execute`/`shell`) — a
  known upstream mismatch between the two Copilot products (github/copilot-cli#738) — and one committed
  file can't safely carry both (VS Code can mis-parse unrecognized names). *Why deferred: supporting the
  coding agent means emitting a SECOND wrapper variant with its own vocabulary, which needs the verified
  github.com tool aliases (GitHub's docs were unreachable from the build environment). Confirm the exact
  aliases, then add a `*.coding-agent.md` emitter to `sync-copilot.*`. Until then `.github/agents/` is
  VS-Code-only by decision.*

- [ ] **Build a `/configure-fleet` (or `SETUP.md`) onboarding wizard.** Turn the currently-invisible
  half-day of filling placeholders into a guided ~15-minute fill-in. *Why: the operability review's
  highest-leverage adoption lever — make first-run setup obvious and fast instead of latent.*
