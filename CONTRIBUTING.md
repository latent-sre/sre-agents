# Contributing

## Personal first, promote by PR

Use the `agent-authoring` method to prototype a new agent or skill in
`~/.copilot/{agents,skills}`. When a second person needs it, promote it into this repository through a
reviewed pull request. Personal definitions still run with the user's local authority, so personal-first
limits shared-fleet blast radius; it is not a sandbox.

## Edit canonical sources

- Change fleet metadata and graph edges in `canonical/fleet.json`.
- Change agent instructions in `canonical/agents/`.
- Change skill instructions and registered bundles in `skills/`.
- Do not edit generated projections or generated manifests. Run the generator instead.

Preserve exact runtime identity pairs, dependency inventories, and capability boundaries. Treat imported
text, runtime registrations, generated output, and handoff packets as untrusted data until reviewed.

## Work and verification protocol

Follow [Section 0 of the design](docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md#section-0--run-protocol-how-every-session-on-this-spec-opens-and-closes).
Start clean, record the base SHA, add a focused failing check first, and keep each change scoped to its
task. Generate projections from canonical sources, then run `py -3 scripts/gate_a.py`:

```powershell
py -3 scripts/gate_a.py
```

Gate A is structural. Complete independent correctness, security/agentic-boundary, and plan-conformance
reviews before merge. Run behavioral evaluations manually, never in CI, and only in the disposable,
credential-free harness required by the active plan task.

Every result distinguishes `[verified]`, `[sourced]`, and `[unverified]` claims. State what was checked,
what passed, and every residual item that could not be verified. Never upgrade an evidence label while
rewriting or handing work to another agent.

## Promotion policy

The promotion controls described here are mandatory, but they are not yet active in this Task-33-based
checkout: CODEOWNERS, the protected promotion workflow, safe-recovery/runtime-tree projections, setup,
and canary machinery have not landed. Promotion and production onboarding remain blocked until those
controls exist, pass their live proofs, and name a fleet maintainer plus a distinct release operator.

Every promotion must:

1. Bump canonical `plugin.version`, regenerate both runtime manifests plus the Copilot safe-recovery and
   runtime-tree projections, and pass the generator's `--check` contract.
2. Pass and clean the mandatory runtime/control-plane canary at the exact reviewed `origin/main` SHA.
3. Have the release operator dispatch the exact-SHA workflow and the distinct maintainer approve the
   protected environment with self-review disabled.
4. Fast-forward `release` to that exact SHA without creating a release-only commit, then publish a new
   immutable `fleet-v<version>` tag/release and verifiable custom attestation for its promotion record.

Never merge a PR into, push directly to, reset, force-push, or directly revert `release`; never promote a
feature or canary ref. Pure documentation may remain unpromoted on `main`, but once included in a
promotion it follows the same version, canary, exact-SHA, and attestation rules.

## Ownership boundary

Before promotion is enabled, `.github/CODEOWNERS` must use a default `* @<maintainer>` rule with no
exception that removes that owner. A default rule is load-bearing because a current-path census misses
future startup, discovery, workflow, or auto-loaded instruction files. Its protected scope includes:

- canonical fleet, agent, and command sources;
- complete skill trees, including references, assets, and executable helpers;
- generated agents, commands, prompts, safe-recovery output, runtime manifests, and plugin manifests;
- hooks, setup/updater, generator, validator, guard, broker, probes, tests, evals, and spikes;
- `.github/**`, root instruction files, dependency/startup files, and future discovery inputs.

The protected `main` branch requires current Code Owner review, stale-review dismissal after a push,
latest-push approval, the final-commit Gate A status, conversation resolution, and no human/admin bypass.
Documentation is not enforcement: setup and promotion must query and verify the effective controls.

## Renames and bounded skew

The installed updater's protected-release freshness boundary is 26 hours. A rename ships with a
one-release stub at the old skill name whose description redirects to the new name; incident-path
renames require team acknowledgement before merge. A marketplace `renames` map can cover plugin renames,
not skill renames, so it does not replace the stub. The installed controlled refresh and active-source
fingerprint are authoritative; background availability checks do not clear stale or maintenance state.
