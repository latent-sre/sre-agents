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


def test_subagent_skill_attribution() -> None:
    """parent_tool_use_id: None = the main session; an id = a SUBAGENT, under that Task call.

    This distinction is load-bearing. The fleet shipped with `Skill` missing from every agent's
    `tools:` allowlist -- the documented way to disable skill invocation entirely -- so no agent
    could load a skill. It was invisible because every other probe measures the MAIN session, which
    always has Skill. Only subagent attribution catches it. Do not collapse these two.
    """
    blob = "\n".join([
        # main session loads a skill -- must NOT count as the agent reaching one
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "pcf-ops"}}]}),
        # a subagent loads one -- this is the real capability being asserted
        _line({"parent_tool_use_id": "toolu_abc",
               "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "sre-ladder"}}]}),
    ])
    out = dp._invocations_from_stream(blob)
    check(out["skill"] == ["pcf-ops", "sre-ladder"], "attribution: both skills seen overall")
    check(out["subagent_skill"] == ["sre-ladder"], "attribution: only the SUBAGENT's skill counted")
    check("pcf-ops" not in out["subagent_skill"], "attribution: a main-session skill is NOT an agent reach")


def test_empty_and_blank_lines() -> None:
    out = dp._invocations_from_stream("")
    check(out == {"skill": [], "agent": [], "subagent_skill": []}, "empty blob -> empty result")
    out2 = dp._invocations_from_stream("\n   \n\n")
    check(out2 == {"skill": [], "agent": [], "subagent_skill": []}, "blank lines -> empty result")


def test_mixed_skill_and_agent() -> None:
    blob = "\n".join([
        _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "sre-ladder"}}]}),
        _line({"content": [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "sre-engineer"}}]}),
        "non-json fallback \"skill\":\"wavefront-queries\"",
    ])
    out = dp._invocations_from_stream(blob)
    check(out["skill"] == ["sre-ladder", "wavefront-queries"], "mixed: both skills captured")
    check(out["agent"] == ["sre-engineer"], "mixed: agent captured")


def test_ignores_non_skill_tool_use() -> None:
    # A tool_use that isn't Skill/Task/Agent (e.g. a normal Read) must not be counted.
    blob = _line({"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]})
    out = dp._invocations_from_stream(blob)
    check(out == {"skill": [], "agent": [], "subagent_skill": []}, "non-routing tool_use ignored")
    # Skill tool_use with a non-string skill input must be ignored (defensive).
    blob2 = _line({"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": None}}]})
    out2 = dp._invocations_from_stream(blob2)
    check(out2["skill"] == [], "Skill with non-string input ignored")


def test_capability_fail_is_counted_not_silently_zero() -> None:
    """[P1] The exact trial the branch's flagship scenario exists to catch: a delegated agent that
    runs but never loads its ladder. Before the fix this landed in NO bucket -- not a hit (must_reach
    unsatisfied), not a misroute (the expected agent WAS in the trace), not a no-route (the trace was
    non-empty) -- and `discovery_rate` silently returned `(0, [...])`, printing `0 hit / 0 mis / 0
    none` for real trials while exiting 0. It must now be counted as a CAPABILITY FAIL and the
    buckets must sum to `trials`."""
    import unittest.mock as mock

    # Every trial: the expected agent WAS delegated to, but it never invoked the required skill
    # itself (reached == [] under its own parent_tool_use_id) -- exactly the crippled-agent trace.
    fake_invocations = {"skill": [], "agent": ["sde-engineer"], "subagent_skill": []}
    scenario = {
        "id": "test-capability-fail",
        "expected_agent": "sde-engineer",
        "agent_must_reach_skill": "sde-ladder",
        "prompt": "do the thing",
    }
    with mock.patch.object(dp, "run_trial", return_value=fake_invocations):
        hits, cap_fails, errors, traces = dp.discovery_rate(scenario, None, 3, 10, env=None)

    check(hits == 0, f"a capability-fail trial must NOT count as a hit (got hits={hits})")
    check(cap_fails == 3, f"all 3 trials must be counted as CAPABILITY FAIL (got cap_fails={cap_fails})")
    check(errors == 0, "no runner errors occurred in this scenario")
    # Reproduce the caller's mis/none classification (as main() does) to prove the four buckets are
    # now mutually exclusive and exhaustive -- the bug this test exists to catch was exactly that
    # hit + mis + none did NOT sum to trials.
    accept = {"sde-engineer"}
    mis = sum(1 for tr in traces if tr and not (accept & set(tr)))
    none = sum(1 for tr in traces if not tr)
    check(mis == 0, "the expected agent WAS in the trace -- this must not be a misroute")
    check(none == 0, "the trace was non-empty -- this must not be a no-route")
    check(hits + mis + none + cap_fails + errors == 3,
          f"buckets must sum to trials (got {hits}+{mis}+{none}+{cap_fails}+{errors} != 3)")


def test_capability_hit_when_ladder_is_reached() -> None:
    """Sanity counterpart: when the delegated agent DOES load the required skill itself, it's a
    hit, not a capability fail -- guards against a fix that over-corrects to always flagging."""
    import unittest.mock as mock

    fake_invocations = {"skill": [], "agent": ["sde-engineer"], "subagent_skill": ["sde-ladder"]}
    scenario = {
        "id": "test-capability-hit",
        "expected_agent": "sde-engineer",
        "agent_must_reach_skill": "sde-ladder",
        "prompt": "do the thing",
    }
    with mock.patch.object(dp, "run_trial", return_value=fake_invocations):
        hits, cap_fails, errors, traces = dp.discovery_rate(scenario, None, 2, 10, env=None)
    check(hits == 2, f"ladder reached -> both trials are hits (got hits={hits})")
    check(cap_fails == 0, "ladder reached -> not a capability fail")


def main() -> int:
    tests = [
        test_skill_tool_use, test_agent_task_nesting, test_regex_fallback_on_malformed,
        test_dedupe_and_order, test_empty_and_blank_lines, test_mixed_skill_and_agent,
        test_ignores_non_skill_tool_use, test_subagent_skill_attribution,
        test_capability_fail_is_counted_not_silently_zero, test_capability_hit_when_ladder_is_reached,
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
