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

## Discipline (how to add a scenario)

1. **Eval before docs.** When writing/changing a skill, add ≥1 scenario that fails without it first.
2. Grade the **outcome**, not the trajectory — don't require a specific tool order.
3. Keep graders deterministic where you can; if you need a judge, calibrate it against a few hand-graded
   cases before trusting it.
4. Read a transcript occasionally even when graders pass — confirm the agent got there legitimately.

## Graders available (`graders.py`)

`contains_all` · `contains_any` · `not_contains` · `regex`. Each scores the response text and returns
`(passed, detail)`. Add new ones to the `REGISTRY`.

> The bundled graders are keyword/structural proxies — fast, deterministic, and good at catching
> "it routed to the wrong agent" or "it complied with an injection." They do **not** judge prose
> quality; that's a deliberate trade for CI-stability. Layer a model-based grader where nuance matters.
