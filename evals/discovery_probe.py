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

Scenario files: evals/discovery/*.yaml — each targets exactly one of:
  expected:        a SKILL that should be invoked (folder in .claude/skills/), or
  expected_agent:  an AGENT the request should delegate to (file in .claude/agents/)
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

ROOT = Path(__file__).resolve().parent.parent
DISCOVERY_DIR = Path(__file__).resolve().parent / "discovery"
SKILLS_DIR = ROOT / ".claude/skills"
AGENTS_DIR = ROOT / ".claude/agents"
_SKILL_RE = re.compile(r'"skill"\s*:\s*"([a-z0-9-]+)"')
_AGENT_RE = re.compile(r'"subagent_type"\s*:\s*"([^"]+)"')  # accept capitals (built-in Explore/Plan)


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


def run_trial(prompt: str, settings: str | None, timeout: int) -> dict[str, list[str]]:
    claude = os.environ.get("CLAUDE_BIN", "claude")
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    if settings:
        cmd += ["--settings", settings]
    try:
        # encoding/errors: text=True alone decodes with the locale codec (cp1252 on Windows), which
        # dies on non-latin-1 bytes in the model's output and yields stdout=None. Force UTF-8.
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as e:
        # A delegation may have been emitted BEFORE the (slow-subagent) timeout — parse the
        # partial trace rather than scoring a real routing decision as a miss.
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
        print(f"    [runner timeout after {timeout}s — parsing partial trace]", file=sys.stderr)
        return _invocations_from_stream(out)
    if proc.returncode != 0:
        # Surface a failing runner instead of silently scoring it as a miss
        # (a bad --settings payload or auth failure would otherwise corrupt results).
        print(f"    [runner error rc={proc.returncode}] {proc.stderr.strip()[:300]}", file=sys.stderr)
    return _invocations_from_stream(proc.stdout)


def discovery_rate(scenario: dict, settings: str | None, trials: int, timeout: int) -> tuple[int, list[list[str]]]:
    kind, exp = scenario_target(scenario)
    accept = {exp, *(scenario.get("also_acceptable") or [])}
    # CAPABILITY probe: the delegated agent must itself invoke a skill. Set `agent_must_reach_skill`
    # to a skill name, or to `true` for "any skill". This is the ONLY check that catches an agent
    # whose `tools:` omits `Skill` -- the documented way to disable skill invocation entirely
    # (https://code.claude.com/docs/en/sub-agents). Every other probe measures the main session,
    # which always has Skill, so a crippled agent is invisible to them. It shipped that way.
    must_reach = scenario.get("agent_must_reach_skill")
    hits, traces = 0, []
    for _ in range(trials):
        full = run_trial(scenario["prompt"], settings, timeout)
        # Skill scenarios: a wrong skill OR ANY agent delegation counts as a routing target
        # (e.g. delegating to the built-in Explore instead of loading the expected skill is a
        # misroute, not a no-route). Agent scenarios: only agent delegations count — skills are
        # the chosen agent's own tools, not a competing route.
        invoked = (full["skill"] + full["agent"]) if kind == "skill" else full["agent"]
        reached = full["subagent_skill"]
        traces.append(invoked + [f"subagent-skill:{s}" for s in reached])
        ok = bool(accept & set(invoked))
        if must_reach:
            # The agent must have been reached AND have loaded a skill ITSELF. A main-session
            # Skill call does not count: that is exactly the false pass this probe exists to kill.
            ok = ok and (bool(reached) if must_reach is True else must_reach in reached)
        if ok:
            hits += 1
    return hits, traces


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

    if args.run:
        # Classify every trial: hit (the expected target was reached) / MISROUTE (a non-accepted
        # target was invoked AND the expected one was not — incl. a wrong-kind delegation) /
        # no-route (nothing invoked; the model answered inline). Misroutes are the real routing
        # failures; a no-route on a general-knowledge prompt is usually not a fault.
        t_hit = t_mis = t_none = 0
        for s in scenarios:
            hits, traces = discovery_rate(s, base, args.trials, args.timeout)
            kind, exp = scenario_target(s)
            accept = {exp, *(s.get("also_acceptable") or [])}
            mis = sum(1 for tr in traces if tr and not (accept & set(tr)))
            none = sum(1 for tr in traces if not tr)
            t_hit += hits; t_mis += mis; t_none += none
            picks = ", ".join(sorted({x for tr in traces for x in tr}) or ["none"])
            tag = "   <- MISROUTE" if mis else ""
            print(f"  {s['id']:<34} {hits} hit / {mis} mis / {none} none  -> {kind}:{exp}  (saw: {picks}){tag}")
        n = len(scenarios) * args.trials
        print(f"\n{t_hit}/{n} hit · {t_mis}/{n} MISROUTE (real routing failures) · "
              f"{t_none}/{n} no-route (answered without the target — often not a fault).")
        print("Decision rule: treat MISROUTE as the failure signal, not raw hit-rate.")
        # ADVISORY exit only — --run is not a CI gate. Tolerate up to --max-misroute (default 0)
        # stochastic misroutes before signaling failure, mirroring run_evals' --threshold.
        if t_mis > args.max_misroute:
            print(f"(advisory) {t_mis} misroute(s) > --max-misroute {args.max_misroute}")
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
        ha, _ = discovery_rate(s, base, args.trials, args.timeout)
        hb, _ = discovery_rate(s, b_settings, args.trials, args.timeout)
        ta += ha; tb += hb
        flag = "" if ha == hb else "   <- changed"
        print(f"  {s['id']:<34} {ha}/{args.trials:<3} {hb}/{args.trials:<3}{flag}")
    print(f"\n  {'TOTAL':<34} {ta}/{len(skill_scenarios)*args.trials:<3} {tb}/{len(skill_scenarios)*args.trials:<3}")
    print("\nReading: B << A means demoting these skills costs discovery; B == A means name-only is safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
