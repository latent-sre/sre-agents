"""Deterministic graders for fleet evals.

Anthropic's eval guidance: prefer deterministic/code-based graders; reserve
model-based judging for genuinely subjective quality. These graders score an
agent's *response text* against a scenario's success criteria. They are a
pragmatic proxy — they check that the load-bearing words/decisions are present,
not prose quality. For nuanced judgment, add a model-based grader (see README).

Each grader returns (passed: bool, detail: str).
"""
from __future__ import annotations

import re
from collections.abc import Callable


def _norm(text: str) -> str:
    return text.lower()


def contains_all(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    missing = [t for t in of if t.lower() not in r]
    return (not missing, "missing: " + ", ".join(missing) if missing else "all present")


def contains_any(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    hit = [t for t in of if t.lower() in r]
    return (bool(hit), "found: " + ", ".join(hit) if hit else "none of: " + ", ".join(of))


def not_contains(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    bad = [t for t in of if t.lower() in r]
    return (not bad, "must-not-appear present: " + ", ".join(bad) if bad else "clean")


def regex(response: str, pattern: str) -> tuple[bool, str]:
    ok = re.search(pattern, response, re.IGNORECASE | re.MULTILINE) is not None
    return (ok, f"/{pattern}/ {'matched' if ok else 'no match'}")


def not_regex(response: str, pattern: str) -> tuple[bool, str]:
    """Passes iff the pattern does NOT match — a negative assertion that needs regex power
    (alternation, word boundaries) rather than plain substrings. Use for "must not propose to
    RUN a state-changing command" style checks where `not_contains` can't express the phrasing."""
    m = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
    detail = f"matched: {m.group(0)!r}" if m else "absent (good)"
    return (m is None, f"/{pattern}/ {detail}")


REGISTRY: dict[str, Callable[..., tuple[bool, str]]] = {
    "contains_all": contains_all,
    "contains_any": contains_any,
    "not_contains": not_contains,
    "regex": regex,
    "not_regex": not_regex,
}


def run_grader(spec: dict, response: str) -> tuple[bool, str]:
    """spec = {type: <name>, ...kwargs}. Dispatches to REGISTRY."""
    kind = spec.get("type")
    fn = REGISTRY.get(kind)
    if fn is None:
        raise ValueError(f"unknown grader type: {kind!r} (known: {', '.join(REGISTRY)})")
    kwargs = {k: v for k, v in spec.items() if k != "type"}
    return fn(response, **kwargs)
