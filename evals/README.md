# Fleet evals

Behavioral evals for the agents + skills — the layer above `scripts/validate-fleet.ps1`
(which only checks structure/spec). These check that the fleet *behaves*: that a request routes
to the right place, a gate blocks what it should, and an agent treats untrusted content as data.

Built on Anthropic's eval shape (["Demystifying evals for AI agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)):

- **Task** — a scenario file in `scenarios/*.yaml`: a `prompt`, human-readable `success_criteria`, and
  machine `graders`.
- **Trial** — one attempt. Model output varies, so run several (`--trials`, default 3) and aggregate.
- **Grader** — scores the **outcome** (what the response decided), *not the path taken*. Prefer the
  deterministic graders in `graders.py`; add a model-based judge only for genuinely subjective quality.

## Run it

```bash
python evals/run_evals.py --validate     # check the suite itself (no model) — this is what CI runs
python evals/run_evals.py --list         # show scenarios
python evals/run_evals.py --run          # invoke the fleet and grade (needs a Claude-enabled runner)
```

`--run` shells out to `"$CLAUDE_BIN" -p <prompt>` (default `claude`) in a **fresh process per trial** —
a fresh session so leftover authoring context can't mask gaps (per the skills best-practice). Swap
`run_agent()` in `run_evals.py` for the Agent SDK if you'd rather drive it programmatically.

## Discovery probe (`discovery_probe.py`) — routing *without* a target hint

`run_evals.py` prepends `"(Use the <target> skill/agent.)"` to every prompt, so it grades
the **outcome given the right skill** — it can't tell you whether the model *discovers* the
right skill on its own. `discovery_probe.py` fills that gap: each scenario in `discovery/*.yaml`
is a realistic prompt that **never names the skill**, and the probe reads which `Skill(...)` the
model actually invoked from the `stream-json` trace.

```bash
python evals/discovery_probe.py --validate    # CI-safe: parse + targets exist, no model
python evals/discovery_probe.py --list
python evals/discovery_probe.py --run --match obs     # measure discovery for a subset (needs a live model)
python evals/discovery_probe.py --ab  --match method  # A=listed vs B=name-only, over the 4 method-skills
```

`--ab` answers "does demoting these skills to `skillOverrides: name-only` cost discovery?"
(`B == A` ⇒ name-only is safe; `B << A` ⇒ it hurts) — it forces `name-only` on the expected
skills of the selected scenarios, so scope it with `--match`. This is the harness behind the
2026-06 Tier-1 decision: with `--match method` (the four `domain=method` skills) at
`skillListingBudgetFraction: 0.04` discovery was **6/12 → 6/12** between conditions — no discovery loss, and no measurable gain — so the
"demote the meta-skills" idea was declined. Like `--run` in `run_evals.py`, the model-driven
modes are **not** a CI gate; only `--validate` is.

**Read `--run` by MISROUTE, not raw hit-rate.** Each trial is classified `hit` / `MISROUTE`
(a *wrong* target was invoked) / `no-route` (nothing invoked — the model answered inline). `--run`
exits non-zero **only when total misroutes exceed `--max-misroute` (default 0)**, because those are the
real routing failures; a `no-route` on a general-knowledge prompt (e.g.
`discover-method-parallelization`) is usually fine, not a fault. `--run` is **advisory, not a CI gate** —
model output is stochastic, so a single flaky misroute shouldn't hard-fail a pipeline; raise
`--max-misroute` (or just read the report) when measuring rather than gating. Only `--validate` is CI-safe. This is why the weak general-knowledge probes don't need their prompts retargeted to force
discovery — the classification already separates "answered inline" from "routed to the wrong place."

> Caveat: discovery ≠ necessity. A skill scoring 0 may simply mean the model answered well
> *without* loading it. Read these as relative/A-B and misroute signals, not absolute hit-rate.

### Agent-routing scenarios (`expected_agent`)

A scenario can target an **agent** instead of a skill (`expected_agent: sre-engineer`); the probe
then reads `Task`/`Agent` `subagent_type` delegations from the trace. These spawn a *real* subagent
that does real work, so they're minutes-slow — scope with `--match agent`, raise `--timeout`, and run
in a throwaway git worktree (writing agents like `sde-engineer` are isolated there).

```bash
python evals/discovery_probe.py --run --agents --match agent --trials 2 --timeout 540
```

Agent scenarios are **opt-in** (`--agents`) and excluded from default runs, because they spawn
write-capable subagents in the CWD — a bare `--run` stays skill-only and safe.

> **Important limitation — measures delegation propensity, not routing quality.** Headless `claude -p`
> often answers a request *inline* instead of delegating, so a low agent score is **not** a fleet
> routing fault. The 2026-06 baseline was **4/12**: `security-reviewer` and `sre-engineer` routed
> 2/2 (investigative/review work naturally spins up a subagent), while `database-reliability`,
> `release-engineer`, and `runbook-author` were handled inline (`saw: none`) and `sde-engineer`
> delegated to the built-in `Explore` agent. The authoritative test of *routing correctness* is the
> `route-request` skill's decision (see `run_evals.py`'s `route-request-*` scenario), not headless
> delegation. These scenarios are kept as a working capability + a documented baseline, not a gate.

## Discipline (how to add a scenario)

1. **Eval before docs.** When writing/changing a skill, add ≥1 scenario that fails without it first.
2. Grade the **outcome**, not the trajectory — don't require a specific tool order.
3. Keep graders deterministic where you can; if you need a judge, calibrate it against a few hand-graded
   cases before trusting it.
4. Read a transcript occasionally even when graders pass — confirm the agent got there legitimately.

## Graders available (`graders.py`)

`contains_all` · `contains_any` · `not_contains` · `regex` · `not_regex` (passes iff the pattern does
*not* match — used for "must not propose to act" checks). Each scores the response text and returns
`(passed, detail)`. Add new ones to the `REGISTRY`. The graders and the stream-json parser are
unit-tested offline and run in CI: `python evals/test_graders.py` (includes adversarial should-fail
verdicts — e.g. a `BLOCKED … does not pass` that must not score as PASS) and
`python evals/test_discovery_probe.py`.

> The bundled graders are keyword/structural proxies — fast, deterministic, and good at catching
> "it routed to the wrong agent" or "it complied with an injection." They do **not** judge prose
> quality; that's a deliberate trade for CI-stability. Layer a model-based grader where nuance matters.
