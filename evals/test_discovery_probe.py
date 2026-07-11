#!/usr/bin/env python3
"""Tests for evals/discovery_probe.py's stream-json parser (`_invocations_from_stream`).

Pure-offline: feeds canned stream-json blobs and asserts the parser extracts the right
Skill / Task-Agent invocations — covering tool_use Skill events, nested Task/Agent delegation
(subagent_type), the regex fallback on malformed (non-JSON) lines, and dedupe + order preservation.

Runnable:
    python3 evals/test_discovery_probe.py
Exits non-zero on any failure with a PASS/FAIL summary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import discovery_probe as dp  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    _results.append((bool(cond), label))
    if not cond:
        print(f"  [FAIL] {label}")


def _line(obj: dict) -> str:
    return json.dumps(obj)


def test_skill_tool_use() -> None:
    blob = "\n".join([
        _line({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "merge-gate"}}
        ]}}),
    ])
    out = dp._invocations_from_stream(blob)
    check(out["skill"] == ["merge-gate"], "skill tool_use parsed")
    check(out["agent"] == [], "no agent when only a skill is used")


def test_agent_task_nesting() -> None:
    # Task delegation nested a couple levels deep inside content.
    blob = _line({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "delegating"},
        {"type": "tool_use", "name": "Task", "input": {"subagent_type": "sre-engineer", "prompt": "triage"}},
    ]}})
    out = dp._invocations_from_stream(blob)
    check(out["agent"] == ["sre-engineer"], "Task subagent_type parsed as agent")
    # 'Agent' name also accepted.
    blob2 = _line({"type": "x", "input": {}, "content": [
        {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "sre-engineer"}}
    ]})
    out2 = dp._invocations_from_stream(blob2)
    check(out2["agent"] == ["sre-engineer"], "Agent tool_use parsed as agent")


def test_regex_fallback_on_malformed() -> None:
    # A non-JSON line must still yield invocations via the regex fallback.
    blob = 'garbage not json "skill":"pcf-ops" trailing {oops'
    out = dp._invocations_from_stream(blob)
    check("pcf-ops" in out["skill"], "regex fallback extracts skill from malformed line")
    blob2 = 'broken {{{ "subagent_type":"sde-engineer" }}} not-json'
    out2 = dp._invocations_from_stream(blob2)
    check("sde-engineer" in out2["agent"], "regex fallback extracts subagent_type from malformed line")


def test_dedupe_and_order() -> None:
    blob = "\n".join([
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "splunk-triage"}}]}),
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "pcf-ops"}}]}),
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "splunk-triage"}}]}),
    ])
    out = dp._invocations_from_stream(blob)
    check(out["skill"] == ["splunk-triage", "pcf-ops"], "skills de-duped, first-seen order preserved")


def test_empty_and_blank_lines() -> None:
    out = dp._invocations_from_stream("")
    check(out == {"skill": [], "agent": []}, "empty blob -> empty result")
    out2 = dp._invocations_from_stream("\n   \n\n")
    check(out2 == {"skill": [], "agent": []}, "blank lines -> empty result")


def test_mixed_skill_and_agent() -> None:
    blob = "\n".join([
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "triage-golden-signals"}}]}),
        _line({"content": [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "sre-engineer"}}]}),
        "non-json fallback \"skill\":\"wavefront-queries\"",
    ])
    out = dp._invocations_from_stream(blob)
    check(out["skill"] == ["triage-golden-signals", "wavefront-queries"], "mixed: both skills captured")
    check(out["agent"] == ["sre-engineer"], "mixed: agent captured")


def test_ignores_non_skill_tool_use() -> None:
    # A tool_use that isn't Skill/Task/Agent (e.g. a normal Read) must not be counted.
    blob = _line({"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]})
    out = dp._invocations_from_stream(blob)
    check(out == {"skill": [], "agent": []}, "non-routing tool_use ignored")
    # Skill tool_use with a non-string skill input must be ignored (defensive).
    blob2 = _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": None}}]})
    out2 = dp._invocations_from_stream(blob2)
    check(out2["skill"] == [], "Skill with non-string input ignored")


def main() -> int:
    tests = [
        test_skill_tool_use, test_agent_task_nesting, test_regex_fallback_on_malformed,
        test_dedupe_and_order, test_empty_and_blank_lines, test_mixed_skill_and_agent,
        test_ignores_non_skill_tool_use,
    ]
    for t in tests:
        t()
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\ntest_discovery_probe: {passed}/{total} checks passed.")
    if passed != total:
        print("FAILED")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
