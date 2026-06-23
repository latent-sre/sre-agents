#!/usr/bin/env python3
"""Discovery probe — does the fleet route to the right SKILL on its own?

Sibling of `run_evals.py`, filling a gap that one has by design: `run_evals.py`
prepends "(Use the <target> skill/agent.)" to every prompt, so it grades the
*outcome given the right skill* — never whether the model **discovers** the right
skill unprompted. This harness does the opposite: the prompt is realistic and
NEVER names the target, and we read which `Skill(...)` the model actually invoked
from the stream-json trace. It answers "is this skill discoverable from its
listing entry?" and, in --ab mode, "does demoting it to name-only cost discovery?"

It needs a live model (like `run_evals.py --run`), so it is NOT a CI gate —
`--validate` (no model) is the only CI-safe mode here.

Scenario files: evals/discovery/*.yaml
  id:              short id
  expected:        the skill that *should* be invoked (a folder in .claude/skills/)
  also_acceptable: optional list of other skills that also count as correct
  prompt:          a realistic, AMBIGUOUS prompt that does NOT name the skill

Modes:
  --validate                 parse files + confirm `expected` targets exist (no model)
  --list                     print the scenarios
  --run [--settings JSON]    invoke per scenario; report discovery rate
  --ab                       A = baseline vs B = expected-skills forced to name-only;
                             prints the side-by-side discovery table (the Tier-1 probe)

Common flags: --trials N (default 3), --settings <json-or-file> (baseline settings).
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
REQUIRED = ("id", "expected", "prompt")
_SKILL_RE = re.compile(r'"skill"\s*:\s*"([a-z0-9-]+)"')


def load_scenarios() -> list[dict]:
    out = []
    for f in sorted(DISCOVERY_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {"_error": f"expected mapping, got {type(data).__name__}"}
        data["_file"] = f.name
        out.append(data)
    return out


def skill_exists(name: str) -> bool:
    return (SKILLS_DIR / name / "SKILL.md").is_file()


def validate(scenarios: list[dict]) -> list[str]:
    problems, seen = [], set()
    if not scenarios:
        return [f"no scenarios found in {DISCOVERY_DIR}"]
    for s in scenarios:
        where = s.get("_file", "?")
        if s.get("_error"):
            problems.append(f"{where}: {s['_error']}")
        for key in REQUIRED:
            if not s.get(key):
                problems.append(f"{where}: missing '{key}'")
        sid = s.get("id")
        if sid and sid in seen:
            problems.append(f"{where}: duplicate id '{sid}'")
        seen.add(sid)
        for t in [s.get("expected"), *(s.get("also_acceptable") or [])]:
            if t and not skill_exists(t):
                problems.append(f"{where}: target '{t}' is not a known skill")
    return problems


def _skills_from_stream(blob: str) -> list[str]:
    """Every skill the model invoked, parsed from a stream-json transcript."""
    found: list[str] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            found += _SKILL_RE.findall(line)  # fallback: regex the raw line
            continue
        stack = [evt]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "tool_use" and node.get("name") == "Skill":
                    sk = (node.get("input") or {}).get("skill")
                    if isinstance(sk, str):
                        found.append(sk)
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    # de-dupe, preserve order
    seen, uniq = set(), []
    for s in found:
        if s not in seen:
            seen.add(s); uniq.append(s)
    return uniq


def run_trial(prompt: str, settings: str | None) -> list[str]:
    claude = os.environ.get("CLAUDE_BIN", "claude")
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    if settings:
        cmd += ["--settings", settings]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    return _skills_from_stream(proc.stdout)


def discovery_rate(scenario: dict, settings: str | None, trials: int) -> tuple[int, list[list[str]]]:
    accept = {scenario["expected"], *(scenario.get("also_acceptable") or [])}
    hits, traces = 0, []
    for _ in range(trials):
        invoked = run_trial(scenario["prompt"], settings)
        traces.append(invoked)
        if accept & set(invoked):
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
    args = ap.parse_args()

    scenarios = load_scenarios()

    if args.validate:
        problems = validate(scenarios)
        if problems:
            print("DISCOVERY SUITE INVALID:")
            print("\n".join("  - " + p for p in problems))
            return 1
        print(f"discovery suite OK — {len(scenarios)} scenario(s), targets resolve.")
        return 0

    if args.match:
        scenarios = [s for s in scenarios if args.match in (s.get("id") or "")]
        if not scenarios:
            print(f"no scenarios match '{args.match}'")
            return 1

    if args.list:
        for s in scenarios:
            extra = f"  (also: {', '.join(s.get('also_acceptable') or [])})" if s.get("also_acceptable") else ""
            print(f"- {s['id']} -> {s['expected']}{extra}\n    {s['prompt'].strip().splitlines()[0]}")
        return 0

    base = _load_settings(args.settings)

    if args.run:
        total = 0
        for s in scenarios:
            hits, traces = discovery_rate(s, base, args.trials)
            total += hits
            picks = ", ".join(sorted({sk for tr in traces for sk in tr}) or ["none"])
            print(f"  {s['id']:<28} {hits}/{args.trials} discovered {s['expected']}  (saw: {picks})")
        print(f"\n{total}/{len(scenarios) * args.trials} trials discovered the expected skill.")
        return 0

    # --ab : A = baseline, B = every expected skill forced to name-only
    expected = {s["expected"] for s in scenarios}
    b_settings = _name_only(base, expected)
    print(f"A = baseline | B = name-only for: {', '.join(sorted(expected))}\n")
    print(f"  {'scenario':<28} {'A':>5} {'B':>5}")
    ta = tb = 0
    for s in scenarios:
        ha, _ = discovery_rate(s, base, args.trials)
        hb, _ = discovery_rate(s, b_settings, args.trials)
        ta += ha; tb += hb
        flag = "" if ha == hb else "   <- changed"
        print(f"  {s['id']:<28} {ha}/{args.trials:<3} {hb}/{args.trials:<3}{flag}")
    print(f"\n  {'TOTAL':<28} {ta}/{len(scenarios)*args.trials:<3} {tb}/{len(scenarios)*args.trials:<3}")
    print("\nReading: B << A means demoting these skills costs discovery; B == A means name-only is safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
