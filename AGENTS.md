# SRE Agents repository guide

This repository develops the SRE Agents fleet. These instructions are for contributors working on
the fleet source; shipped runtime context belongs in canonical agents and skills, not in this file.

## Authoring layout

- `canonical/fleet.json` owns fleet metadata, capabilities, dependencies, delegation, and handoffs.
- `canonical/agents/` owns shared agent bodies.
- `skills/` owns the 26 Agent Skills and their registered bundles.
- `generated/` and the runtime manifests are deterministic projections; never edit them directly.
- `scripts/` owns generation, validation, and structural gates.
- `evals/` owns behavioral scenarios and graders.

## Required workflow

Follow the [work and verification protocol](CONTRIBUTING.md#work-and-verification-protocol).
Write a failing focused check before changing an artifact. For fleet runtime content, edit
`canonical/fleet.json`, `canonical/agents/`, or `skills/`, then regenerate projections through the
repository generator; edit repository machinery and documentation in their owning source paths.

Run `py -3 scripts/gate_a.py` before committing. Gate A proves structure, not semantic correctness;
complete the independent correctness, security, and plan-conformance reviews required by Section 0.

Behavioral evaluations are manual, never CI. Run them only against reviewed, team-authored content in
the disposable, credential-free boundary defined by the plan, and preserve their evidence labels.

Contribution policy, source-of-truth rules, and review expectations are in
[CONTRIBUTING.md](CONTRIBUTING.md).
