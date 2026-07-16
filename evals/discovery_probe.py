#!/usr/bin/env python3
"""Discovery probe — does the fleet route to the right SKILL or AGENT on its own?

Sibling of `run_evals.py`, filling a gap that one has by design: `run_evals.py`
prepends "(Use the <target> skill/agent.)" to every prompt, so it grades the
*outcome given the right target* — never whether the model **discovers** the
right one unprompted. This harness does the opposite: the prompt is realistic and
NEVER names the target, and we read what the model actually invoked from the
stream-json trace — `Skill(<skill>)` for skill routing, or a `Task`/`Agent`
delegation (`subagent_type`) for agent routing.

It needs a live model (like `run_evals.py --run`), so it is NOT a CI gate —
`--validate` (no model) is the only CI-safe mode here. NOTE: agent-routing
scenarios spawn a real subagent that does real work, so they are MUCH slower than
skill scenarios (minutes each) — scope them with `--match` and raise `--timeout`.

`--run` and `--ab` execute every trial inside `clean_room.clean_env()` (see evals/clean_room.py):
each `claude` subprocess sees ONLY a copy of the credentials, not the operator's ~/.claude, so the
fleet's skills/agents aren't competing against personal ones for discovery. If no credentials are
available, or a trial's trace shows it never authenticated, the run ABORTS with `AuthUnavailable`
before any scenario is scored — a credential-less run otherwise emits a valid, Skill()-free
stream-json trace that would read as a devastating (but fake) finding about the fleet.

Scenario files: evals/discovery/*.yaml — each targets exactly one of:
  expected:        a SKILL that should be invoked (folder in skills/), or
  expected_agent:  an AGENT the request should delegate to (file in generated/claude/agents/)
  id:              short id
  also_acceptable: optional list of other targets of the SAME kind that also count as correct
  prompt:          a realistic, AMBIGUOUS prompt that does NOT name the target

Modes:
  --validate                 parse files + confirm targets exist (no model)
  --list                     print the scenarios
  --run [--settings JSON]    invoke per scenario; report discovery rate
  --ab                       A = baseline vs B = expected-SKILLS forced to name-only
                             (skill scenarios only; the Tier-1 probe)

Common flags: --trials N (3), --match SUBSTR, --settings <json-or-file>,
              --timeout SECONDS (300; raise for agent scenarios).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("discovery_probe: PyYAML required — `python -m pip install pyyaml`")

import clean_room

ROOT = Path(__file__).resolve().parent.parent
DISCOVERY_DIR = Path(__file__).resolve().parent / "discovery"
SKILLS_DIR = ROOT / "skills"
AGENTS_DIR = ROOT / "generated/claude/agents"
_SKILL_RE = re.compile(r'"skill"\s*:\s*"([a-z0-9-]+)"')
_AGENT_RE = re.compile(r'"subagent_type"\s*:\s*"([^"]+)"')  # accept capitals (built-in Explore/Plan)

_AUTH_FAILED_MSG = (
    "a trial came back UNAUTHENTICATED. This is fatal, not a result: the trace is well-formed and "
    "contains no Skill() call, so scoring it would report a no-route -- a fake finding about the "
    "fleet caused by a broken instrument. Run `claude` and /login, then re-run."
)


def load_scenarios() -> list[dict]:
    out = []
    for f in sorted(DISCOVERY_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            data = {"_error": f"YAML parse error: {e}"}
        if not isinstance(data, dict):
            data = {"_error": f"expected mapping, got {type(data).__name__}"}
        data["_file"] = f.name
        out.append(data)
    return out


def skill_exists(name: str) -> bool:
    return (SKILLS_DIR / name / "SKILL.md").is_file()


def agent_exists(name: str) -> bool:
    return (AGENTS_DIR / f"{name}.md").is_file()


def scenario_target(s: dict) -> tuple[str, str | None]:
    """('agent', name) for an agent-routing scenario, else ('skill', name)."""
    if s.get("expected_agent"):
        return "agent", s["expected_agent"]
    return "skill", s.get("expected")


def validate(scenarios: list[dict]) -> list[str]:
    problems, seen = [], set()
    if not scenarios:
        return [f"no scenarios found in {DISCOVERY_DIR}"]
    for s in scenarios:
        where = s.get("_file", "?")
        if s.get("_error"):
            problems.append(f"{where}: {s['_error']}")
        if not s.get("id"):
            problems.append(f"{where}: missing 'id'")
        if not s.get("prompt"):
            problems.append(f"{where}: missing 'prompt'")
        # exactly one of expected / expected_agent
        if bool(s.get("expected")) == bool(s.get("expected_agent")):
            problems.append(f"{where}: set exactly one of 'expected' (skill) or 'expected_agent'")
        sid = s.get("id")
        if sid:
            if sid in seen:
                problems.append(f"{where}: duplicate id '{sid}'")
            seen.add(sid)
        kind, _ = scenario_target(s)
        exists = agent_exists if kind == "agent" else skill_exists
        noun = "agent" if kind == "agent" else "skill"
        primary = s.get("expected_agent") if kind == "agent" else s.get("expected")
        if primary and not exists(primary):
            problems.append(f"{where}: target '{primary}' is not a known {noun}")
        # agent_must_reach_skill: a string names a specific skill the delegated agent must invoke
        # itself. Unvalidated, a typo (e.g. 'sde-laddr') silently scores 0 hits forever instead of
        # failing --validate -- the capability check would never fire and nothing would say why.
        must_reach = s.get("agent_must_reach_skill")
        if isinstance(must_reach, str) and not skill_exists(must_reach):
            problems.append(f"{where}: agent_must_reach_skill '{must_reach}' is not a known skill")
        # also_acceptable: for a SKILL scenario an AGENT is a legitimate alternate -- discovery_rate()
        # already counts agent delegations as routing targets there (invoked = skills + agents), and
        # delegating to the agent that OWNS the skill is the roster working, not a misroute. Validating
        # skills-only here was stricter than the executor and rejected a correct alternate.
        for t in (s.get("also_acceptable") or []):
            ok = exists(t) or (kind == "skill" and agent_exists(t))
            if not ok:
                extra = " or agent" if kind == "skill" else ""
                problems.append(f"{where}: also_acceptable '{t}' is not a known {noun}{extra}")
    return problems


def _invocations_from_stream(blob: str) -> dict[str, list[str]]:
    """What the model invoked, parsed from a stream-json transcript:
    {'skill': [...], 'agent': [...], 'subagent_skill': [...]} (order-preserving, de-duped).

    `subagent_skill` is the load-bearing one: skills a SUBAGENT invoked, not the main session.
    Claude Code stamps each event with `parent_tool_use_id` -- None for the main session, and the
    id of the Task/Agent tool_use for anything a subagent did. So a Skill event with a non-None
    parent_tool_use_id was invoked BY the delegated agent.

    This distinction is why the fleet shipped with agents that could not invoke ANY skill: every
    other probe here measures the MAIN session, which always has the Skill tool, so a subagent
    with `Skill` missing from its `tools:` allowlist looked identical to a healthy one.
    """
    skills: list[str] = []
    agents: list[str] = []
    subagent_skills: list[str] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            skills += _SKILL_RE.findall(line)   # fallback: regex the raw line
            agents += _AGENT_RE.findall(line)
            continue
        # None => the main session emitted this; an id => a subagent did, under that Task call.
        from_subagent = evt.get("parent_tool_use_id") is not None
        stack = [evt]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "tool_use":
                    inp = node.get("input") or {}
                    if node.get("name") == "Skill" and isinstance(inp.get("skill"), str):
                        skills.append(inp["skill"])
                        if from_subagent:
                            subagent_skills.append(inp["skill"])
                    elif node.get("name") in ("Task", "Agent") and isinstance(inp.get("subagent_type"), str):
                        agents.append(inp["subagent_type"])
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)

    def _dedupe(xs: list[str]) -> list[str]:
        seen, out = set(), []
        for x in xs:
            if x not in seen:
                seen.add(x); out.append(x)
        return out

    return {"skill": _dedupe(skills), "agent": _dedupe(agents),
            "subagent_skill": _dedupe(subagent_skills)}


def run_trial(prompt: str, settings: str | None, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, list[str]]:
    claude = os.environ.get("CLAUDE_BIN", "claude")
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    if settings:
        cmd += ["--settings", settings]
    try:
        # encoding/errors: text=True alone decodes with the locale codec (cp1252 on Windows), which
        # dies on non-latin-1 bytes in the model's output and yields stdout=None. Force UTF-8.
        # env: the CLEAN ROOM (clean_room.clean_env()). Without it this inherits the operator's
        # ~/.claude -- personal skills, personal agents, installed plugins -- which COMPETE with the
        # fleet for discovery, i.e. we would be measuring the laptop.
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
            encoding="utf-8", errors="replace", env=env,
        )
    except subprocess.TimeoutExpired as e:
        # A delegation may have been emitted BEFORE the (slow-subagent) timeout — parse the
        # partial trace rather than scoring a real routing decision as a miss.
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
        invocations = _invocations_from_stream(out)
        # A killed process almost never gets to emit the final structured result event, so
        # is_error_event is normally False here -- no structured signal either way, same as before.
        # IF one somehow is present, honor it -- but never fall back to substring-scanning the raw
        # partial transcript for the auth marker text (the false-fatal this fix exists to close):
        # this branch planted the literal string "Not logged in" in ~30 places across evals/ and
        # docs/, so an agent scenario that greps this repo and then times out would read a
        # tool_result containing that text and wrongly abort the whole suite as an auth failure.
        if clean_room.is_error_event(out) and not (invocations["skill"] or invocations["agent"]):
            if clean_room.result_looks_like_auth(out):
                raise clean_room.AuthUnavailable(_AUTH_FAILED_MSG)
            raise clean_room.RunnerFailed(f"trial timed out after {timeout}s and the runner reported an error")
        print(f"    [runner timeout after {timeout}s — parsing partial trace]", file=sys.stderr)
        return invocations

    invocations = _invocations_from_stream(proc.stdout)
    measured = bool(invocations["skill"] or invocations["agent"])
    # The CLI's own structured signal (the stream-json `result` event's `is_error`), not a substring
    # scan of the raw transcript: that would match `tool_result` content too -- a file the agent
    # itself read, a grep hit -- which can innocently contain any marker text this module cares
    # about. `subtype` still lies (a not-logged-in run says subtype="success" while is_error=true),
    # so is_error is the only field trusted here. proc.returncode is an OR'd fallback for the case
    # where the CLI crashed before emitting any stream event at all.
    failed = proc.returncode != 0 or clean_room.is_error_event(proc.stdout)
    if failed and not measured:
        # Nothing was invoked AND the run did not complete cleanly: this trial produced NO
        # measurement. Scoring it would silently fold a broken instrument (rate limit, 5xx, network
        # drop, bad --settings payload -- auth is only one way to get here) into "no-route" stats.
        if clean_room.is_error_event(proc.stdout) and clean_room.result_looks_like_auth(proc.stdout):
            raise clean_room.AuthUnavailable(_AUTH_FAILED_MSG)
        raise clean_room.RunnerFailed(
            f"trial produced no measurement (rc={proc.returncode}): {proc.stderr.strip()[:300]}"
        )
    if failed and measured:
        # The routing decision WAS genuinely observed before/despite the failure signal -- score
        # it, but make the runner problem visible rather than silently swallowing it.
        print(f"    [runner reported rc={proc.returncode} but an invocation was already observed "
              f"in the trace -- scoring it] {proc.stderr.strip()[:300]}", file=sys.stderr)
    return invocations


def discovery_rate(scenario: dict, settings: str | None, trials: int, timeout: int,
                   env: dict[str, str] | None = None) -> tuple[int, int, int, list[list[str]]]:
    """Returns (hits, capability_fails, errors, traces).

    A trial with `agent_must_reach_skill` set lands in exactly one of FOUR outcomes, not three:
      HIT             -- expected agent reached AND it loaded the required skill itself.
      CAPABILITY FAIL -- expected agent reached, but `must_reach` was NOT satisfied. This used to
                         fall into NO bucket at all: not a hit (ok was False), not a misroute (the
                         expected target WAS in the trace), not a no-route (the trace was
                         non-empty) -- so `0 hit / 0 mis / 0 none` printed for real trials and the
                         suite exited 0 while the exact failure this probe exists to catch occurred.
      MISROUTE/NO-ROUTE (computed by the caller from `traces`, unchanged) -- the expected agent was
                         never delegated to, so there is no capability to observe: UNMEASURED, not
                         a capability failure. Keep these conceptually distinct even though the
                         count is the same union (mis + none).
    An ERROR trial (clean_room.RunnerFailed: the runner didn't complete and nothing was invoked) is
    excluded entirely -- it is unmeasurable, not a no-route -- and counted separately so the
    per-scenario buckets can still be shown to sum to `trials`.
    """
    kind, exp = scenario_target(scenario)
    accept = {exp, *(scenario.get("also_acceptable") or [])}
    # CAPABILITY probe: the delegated agent must itself invoke a skill. Set `agent_must_reach_skill`
    # to a skill name, or to `true` for "any skill". This is the ONLY check that catches an agent
    # whose `tools:` omits `Skill` -- the documented way to disable skill invocation entirely
    # (https://code.claude.com/docs/en/sub-agents). Every other probe measures the main session,
    # which always has Skill, so a crippled agent is invisible to them. It shipped that way.
    must_reach = scenario.get("agent_must_reach_skill")
    hits = cap_fails = errors = 0
    traces: list[list[str]] = []
    for _ in range(trials):
        try:
            full = run_trial(scenario["prompt"], settings, timeout, env=env)
        except clean_room.RunnerFailed as e:
            print(f"    [trial ERROR -- unmeasurable, excluded from routing stats: {e}]", file=sys.stderr)
            errors += 1
            continue
        # Skill scenarios: a wrong skill OR ANY agent delegation counts as a routing target
        # (e.g. delegating to the built-in Explore instead of loading the expected skill is a
        # misroute, not a no-route). Agent scenarios: only agent delegations count — skills are
        # the chosen agent's own tools, not a competing route.
        invoked = (full["skill"] + full["agent"]) if kind == "skill" else full["agent"]
        reached = full["subagent_skill"]
        traces.append(invoked + [f"subagent-skill:{s}" for s in reached])
        expected_reached = bool(accept & set(invoked))
        capability_ok = True
        if must_reach:
            # The agent must have been reached AND have loaded a skill ITSELF. A main-session
            # Skill call does not count: that is exactly the false pass this probe exists to kill.
            capability_ok = bool(reached) if must_reach is True else (must_reach in reached)
        if expected_reached and must_reach and not capability_ok:
            cap_fails += 1
        elif expected_reached and capability_ok:
            hits += 1
        # else: the expected target was never reached -- a routing miss (misroute/no-route),
        # computed by the caller from `traces`. No capability was observable in that trial.
    return hits, cap_fails, errors, traces


def _load_settings(val: str | None) -> str | None:
    if not val:
        return None
    p = Path(val)
    return p.read_text(encoding="utf-8") if p.is_file() else val


def _name_only(base: str | None, skills: set[str]) -> str:
    cfg = json.loads(base) if base else {}
    cfg.setdefault("skillOverrides", {})
    for s in skills:
        cfg["skillOverrides"][s] = "name-only"
    return json.dumps(cfg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true", help="check the suite, no model (CI-safe)")
    g.add_argument("--list", action="store_true")
    g.add_argument("--run", action="store_true", help="measure autonomous discovery")
    g.add_argument("--ab", action="store_true", help="baseline vs expected-skills-as-name-only")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--match", help="only scenarios whose id contains this substring (--list/--run/--ab)")
    ap.add_argument("--settings", help="baseline settings JSON string or file path")
    ap.add_argument("--timeout", type=int, default=300, help="per-trial timeout sec (raise for agent scenarios)")
    ap.add_argument("--agents", action="store_true",
                    help="opt in to agent-routing scenarios (write-capable subagents — isolate in a worktree)")
    ap.add_argument("--max-misroute", type=int, default=0,
                    help="ADVISORY tolerance for --run: exit non-zero only if total misroutes EXCEED N "
                         "(default 0). --run is NOT a CI gate — model output is stochastic, so a single "
                         "flaky misroute shouldn't hard-fail; raise this when measuring, don't gate on it.")
    args = ap.parse_args()

    scenarios = load_scenarios()
    problems = validate(scenarios)

    if args.validate:
        if problems:
            print("DISCOVERY SUITE INVALID:")
            print("\n".join("  - " + p for p in problems))
            return 1
        print(f"discovery suite OK — {len(scenarios)} scenario(s), targets resolve.")
        return 0

    # All model-driven modes need a clean suite (fail fast with a clear list).
    if problems and (args.run or args.ab):
        print("DISCOVERY SUITE INVALID (fix before running):")
        print("\n".join("  - " + p for p in problems))
        return 1

    if args.match:
        scenarios = [s for s in scenarios if args.match in (s.get("id") or "")]
        if not scenarios:
            print(f"no scenarios match '{args.match}'")
            return 1

    if args.list:
        for s in scenarios:
            kind, exp = scenario_target(s)
            extra = f"  (also: {', '.join(s.get('also_acceptable') or [])})" if s.get("also_acceptable") else ""
            lines = (s.get("prompt") or "").strip().splitlines()
            print(f"- {s.get('id', '?')} -> {kind}:{exp}{extra}\n    {lines[0] if lines else '(no prompt)'}")
        return 0

    # Agent scenarios spawn WRITE-CAPABLE subagents in the CWD; require explicit opt-in and exclude
    # them from default runs so a bare `--run` can't mutate the caller's checkout.
    if not args.agents:
        skipped = [s for s in scenarios if scenario_target(s)[0] == "agent"]
        scenarios = [s for s in scenarios if scenario_target(s)[0] == "skill"]
        if skipped:
            print(f"note: skipped {len(skipped)} agent scenario(s); pass --agents to include them "
                  f"(write-capable — isolate in a throwaway git worktree).\n")
        if not scenarios:
            print("no skill scenarios selected (agent scenarios require --agents).")
            return 1
    elif args.run or args.ab:
        print("WARNING: --agents runs write-capable subagents in the CWD — isolate this in a "
              "throwaway git worktree so the working tree can't be mutated.\n")

    base = _load_settings(args.settings)

    # clean_env() wraps ONLY --run/--ab -- the paths that invoke a model. It raises AuthUnavailable
    # immediately (before a single trial runs) if there are no credentials, so a credential-less
    # invocation aborts with zero scenario results instead of reporting a fake 0% discovery rate.
    # --validate/--list return above this line and so never touch it -- they run no model and are
    # CI gates that must work on machines with no ~/.claude at all.
    try:
        with clean_room.clean_env() as env:
            if args.run:
                # Classify every trial into one of FOUR mutually-exclusive buckets, which sum to
                # `trials` per scenario (an ERROR trial is excluded up front by discovery_rate and
                # counted separately, so it doesn't silently vanish from the arithmetic either):
                #   hit             -- the expected target was reached (and, if `agent_must_reach_skill`
                #                      is set, the delegated agent loaded the required skill itself).
                #   MISROUTE        -- a non-accepted target was invoked AND the expected one was not.
                #   no-route        -- nothing invoked; the model answered inline.
                #   CAPABILITY FAIL -- the expected agent WAS reached but did not satisfy
                #                      `agent_must_reach_skill`. This used to land in NO bucket at
                #                      all (not hit, not misroute, not no-route) and print
                #                      `0 hit / 0 mis / 0 none` while exiting 0 -- silently
                #                      swallowing the exact failure this probe exists to catch.
                # UNMEASURED (informational, not a bucket in the sum): for a must_reach scenario,
                # mis+none trials had no capability to observe at all -- distinct from CAPABILITY
                # FAIL, which means the capability WAS observable and failed.
                t_hit = t_mis = t_none = t_capfail = t_err = 0
                for s in scenarios:
                    hits, cap_fails, errors, traces = discovery_rate(s, base, args.trials, args.timeout, env=env)
                    kind, exp = scenario_target(s)
                    accept = {exp, *(s.get("also_acceptable") or [])}
                    must_reach = s.get("agent_must_reach_skill")
                    mis = sum(1 for tr in traces if tr and not (accept & set(tr)))
                    none = sum(1 for tr in traces if not tr)
                    unmeasured = (mis + none) if must_reach else 0
                    bucket_sum = hits + mis + none + cap_fails + errors
                    assert bucket_sum == args.trials, (
                        f"{s['id']}: buckets do not sum to trials "
                        f"({hits} hit + {mis} mis + {none} none + {cap_fails} capfail + {errors} error "
                        f"= {bucket_sum} != {args.trials})"
                    )
                    t_hit += hits; t_mis += mis; t_none += none; t_capfail += cap_fails; t_err += errors
                    picks = ", ".join(sorted({x for tr in traces for x in tr}) or ["none"])
                    tags = []
                    if mis:
                        tags.append("MISROUTE")
                    if cap_fails:
                        tags.append("CAPABILITY FAIL")
                    if errors:
                        tags.append("ERROR")
                    tag = "   <- " + ", ".join(tags) if tags else ""
                    cap_bit = f" / {cap_fails} CAPFAIL" if must_reach else ""
                    unmeasured_bit = f" / {unmeasured} unmeasured" if must_reach else ""
                    err_bit = f" / {errors} ERROR" if errors else ""
                    print(f"  {s['id']:<34} {hits} hit / {mis} mis / {none} none{cap_bit}{unmeasured_bit}{err_bit}"
                          f"  -> {kind}:{exp}  (saw: {picks}){tag}  [{bucket_sum}/{args.trials} accounted for]")
                n = len(scenarios) * args.trials
                grand_total = t_hit + t_mis + t_none + t_capfail + t_err
                print(f"\n{t_hit}/{n} hit · {t_mis}/{n} MISROUTE (real routing failures) · "
                      f"{t_none}/{n} no-route (answered without the target — often not a fault) · "
                      f"{t_capfail}/{n} CAPABILITY FAIL (agent reached, ladder/skill not loaded) · "
                      f"{t_err}/{n} ERROR (runner failed, unmeasurable, excluded from the rates above).")
                print(f"buckets sum to n: {grand_total} == {n}: {grand_total == n}")
                print("Decision rule: treat MISROUTE and CAPABILITY FAIL as failure signals, not raw hit-rate.")
                # CAPABILITY FAIL and ERROR are NOT advisory-tolerant like MISROUTE: a capability
                # check that can't report its own failure (or a run that produced no measurement)
                # is a correctness bug in the probe/fleet, not stochastic model variance.
                if t_capfail > 0:
                    print(f"{t_capfail} CAPABILITY FAIL -- forcing non-zero exit (never advisory).")
                if t_err > 0:
                    print(f"{t_err} ERROR trial(s) -- unmeasurable, forcing non-zero exit.")
                # ADVISORY exit only for MISROUTE — --run is not a CI gate. Tolerate up to
                # --max-misroute (default 0) stochastic misroutes, mirroring run_evals' --threshold.
                if t_mis > args.max_misroute:
                    print(f"(advisory) {t_mis} misroute(s) > --max-misroute {args.max_misroute}")
                if t_mis > args.max_misroute or t_capfail > 0 or t_err > 0:
                    return 1
                return 0

            # --ab : A = baseline, B = every expected SKILL forced to name-only (skill scenarios only)
            skill_scenarios = [s for s in scenarios if scenario_target(s)[0] == "skill"]
            if not skill_scenarios:
                print("--ab applies to skill scenarios only; none selected.")
                return 1
            expected = {s["expected"] for s in skill_scenarios}
            b_settings = _name_only(base, expected)
            print(f"A = baseline | B = name-only for: {', '.join(sorted(expected))}\n")
            print(f"  {'scenario':<34} {'A':>5} {'B':>5}")
            ta = tb = 0
            for s in skill_scenarios:
                ha, _, _, _ = discovery_rate(s, base, args.trials, args.timeout, env=env)
                hb, _, _, _ = discovery_rate(s, b_settings, args.trials, args.timeout, env=env)
                ta += ha; tb += hb
                flag = "" if ha == hb else "   <- changed"
                print(f"  {s['id']:<34} {ha}/{args.trials:<3} {hb}/{args.trials:<3}{flag}")
            print(f"\n  {'TOTAL':<34} {ta}/{len(skill_scenarios)*args.trials:<3} {tb}/{len(skill_scenarios)*args.trials:<3}")
            print("\nReading: B << A means demoting these skills costs discovery; B == A means name-only is safe.")
            return 0
    except clean_room.AuthUnavailable as e:
        print(f"discovery_probe: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
