#!/usr/bin/env python3
"""Run (or validate) behavioral evals for the agent + skill fleet.

Implements Anthropic's eval shape — *task* (a scenario: prompt + success
criteria), *trial* (one attempt), *grader* (scores the outcome) — and grades
the OUTCOME (what the response decided), not the path taken. Run each scenario
over several trials because model output varies.

Modes:
  --validate   Check every scenario file parses, has required fields, names a
               real fleet target, and uses known graders. Needs no model — run
               it as your CI gate (or locally) to keep the eval suite honest.
  --list       Print the scenarios.
  --run        Actually invoke the agent and grade. Requires a Claude-enabled
               runner: set CLAUDE_BIN (default "claude"); each trial shells out
               `"$CLAUDE_BIN" -p <prompt>` in a FRESH process (fresh session, so
               authoring context can't mask gaps — per skills best practice).

Exit non-zero if any scenario fails its threshold (CI-friendly).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import graders


def positive_int(v: str) -> int:
    """argparse type for --trials: reject 0/negatives (a 0 would ZeroDivision at frac = passes/trials)."""
    iv = int(v)
    if iv < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {iv}")
    return iv

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("evals: PyYAML required — `python -m pip install pyyaml`")

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
REQUIRED = ("id", "target", "prompt", "graders")


def load_scenarios() -> list[dict]:
    out = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            data = {"_yaml_error": str(e)}
        if not isinstance(data, dict):
            data = {"_yaml_error": f"expected mapping, got {type(data).__name__}"}
        data["_file"] = f.name
        out.append(data)
    return out


def target_exists(target: str) -> bool:
    return (ROOT / ".claude/skills" / target / "SKILL.md").is_file() or (
        ROOT / ".claude/agents" / f"{target}.md"
    ).is_file()


def validate(scenarios: list[dict]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for s in scenarios:
        where = s.get("_file", "?")
        for key in REQUIRED:
            if not s.get(key):
                problems.append(f"{where}: missing '{key}'")
        sid = s.get("id")
        if sid:
            if sid in seen:
                problems.append(f"{where}: duplicate id '{sid}'")
            seen.add(sid)
        if s.get("target") and not target_exists(s["target"]):
            problems.append(f"{where}: target '{s['target']}' is not a known skill/agent")
        for g in s.get("graders", []):
            if g.get("type") not in graders.REGISTRY:
                problems.append(f"{where}: unknown grader type '{g.get('type')}'")
                continue
            # Catch a grader missing/with-wrong kwargs at --validate time (CI), instead of
            # passing here and crashing only at --run with a TypeError. A dry run against the
            # empty string exercises the call's binding (required params like of:/pattern:)
            # without needing a model; a binding error is a real suite problem.
            try:
                graders.run_grader(g, "")
            except TypeError as e:
                problems.append(f"{where}: grader '{g.get('type')}' has bad/missing kwargs: {e}")
            except re.error as e:
                problems.append(f"{where}: grader '{g.get('type')}' has an invalid regex: {e}")
    return problems


def run_agent(prompt: str, target: str) -> str:
    """Invoke the fleet in a fresh session. Replace with the Agent SDK if preferred."""
    claude = os.environ.get("CLAUDE_BIN", "claude")
    hint = f"(Use the {target} skill/agent.)\n\n" if target else ""
    proc = subprocess.run(
        [claude, "-p", hint + prompt],
        capture_output=True, text=True, timeout=300, check=False,
        # Decode as UTF-8 explicitly: text=True alone uses the locale codec, which on Windows is
        # cp1252 and dies on the em-dashes/box-drawing the fleet emits. The reader thread then
        # raises, stdout comes back None, and the grader fails with a confusing AttributeError.
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return f"[runner error rc={proc.returncode}] {proc.stderr.strip()}"
    return proc.stdout


def grade_trial(scenario: dict, response: str) -> tuple[bool, list[str]]:
    details = []
    ok_all = True
    for g in scenario["graders"]:
        passed, detail = graders.run_grader(g, response)
        ok_all &= passed
        details.append(f"    [{'PASS' if passed else 'FAIL'}] {g['type']}: {detail}")
    return ok_all, details


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true", help="check the suite, no model")
    g.add_argument("--list", action="store_true")
    g.add_argument("--run", action="store_true", help="invoke the agent and grade")
    ap.add_argument("--trials", type=positive_int, default=3, help="trials per scenario (--run); must be >= 1")
    ap.add_argument("--threshold", type=float, default=1.0, help="pass fraction of trials")
    ap.add_argument("--match", help="only scenarios whose id contains this substring (--list/--run)")
    args = ap.parse_args()

    scenarios = load_scenarios()
    if not scenarios:
        print("evals: no scenarios found in evals/scenarios/")
        return 1

    if args.validate:
        problems = validate(scenarios)
        if problems:
            print("EVAL SUITE INVALID:")
            print("\n".join("  - " + p for p in problems))
            return 1
        print(f"eval suite OK — {len(scenarios)} scenario(s), graders and targets resolve.")
        return 0

    if args.match:
        scenarios = [s for s in scenarios if args.match in (s.get("id") or "")]
        if not scenarios:
            print(f"no scenarios match '{args.match}'")
            return 1

    if args.list:
        for s in scenarios:
            print(f"- {s['id']}  (target: {s['target']})\n    {s['prompt'].strip().splitlines()[0]}")
        return 0

    # --run
    failures = 0
    for s in scenarios:
        passes = 0
        print(f"\n== {s['id']} (target: {s['target']}) ==")
        for t in range(args.trials):
            response = run_agent(s["prompt"], s["target"])
            ok, details = grade_trial(s, response)
            passes += ok
            print(f"  trial {t + 1}: {'PASS' if ok else 'FAIL'}")
            if not ok:
                print("\n".join(details))
        frac = passes / args.trials
        verdict = "PASS" if frac >= args.threshold else "FAIL"
        print(f"  -> {verdict} ({passes}/{args.trials} trials, threshold {args.threshold})")
        failures += verdict == "FAIL"

    print(f"\n{len(scenarios) - failures}/{len(scenarios)} scenarios passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
