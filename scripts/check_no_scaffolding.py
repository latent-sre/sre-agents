#!/usr/bin/env python3
"""Reject build-process scaffolding tokens in shipped LLM-facing content.

Skill and agent bodies are runtime context: an agent loads them and reads every word. Redesign
bookkeeping -- task numbers, spec-section cross-references, the interim `content-building` assembly
state -- is authoring scaffolding, not operational guidance. When it rides along into a SKILL.md or
agent body it dates the artifact and hands the model instructions about the repository's own build
plan instead of the job in front of it. AGENTS.md draws exactly this line ("shipped runtime context
belongs in canonical agents and skills"); this gate keeps the line from rotting.

The patterns are deliberately narrow -- only tokens that never legitimately appear in operational
content. `Phase <n>` is intentionally NOT matched: `ops-tooling` uses "Phase 0 -- Requirements" as a
real methodology heading, so a blanket phase ban would be a false positive. Evidence labels
(`[unverified]`) and the shipped `content-complete` state are content and stay untouched.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()

# (compiled pattern, human label). Each matches only tokens that are build scaffolding wherever they
# appear in runtime content -- never legitimate operational prose.
SCAFFOLDING = (
    (re.compile(r"(?<![A-Za-z0-9])Task \d+"), "build-task reference"),
    (re.compile(r"(?<![A-Za-z0-9-])[Ss]pec Section \d+"), "spec-section cross-reference"),
    (re.compile(r"(?<![A-Za-z0-9-])content-building(?![A-Za-z0-9-])"), "assembly-state scaffolding"),
)

SCANNED_TREES = (Path("skills"), Path("canonical/agents"), Path("canonical/commands"))


def _scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    except OSError as exc:
        return [f"{path.as_posix()}: cannot read: {exc}"]
    failures = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern, label in SCAFFOLDING:
            match = pattern.search(line)
            if match is not None:
                failures.append(
                    f"{path.as_posix()}:{number}: {label} '{match.group(0)}' -- "
                    "build scaffolding does not belong in shipped runtime content"
                )
    return failures


def check(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    failures: list[str] = []
    for relative in SCANNED_TREES:
        base = root / relative
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                failures.extend(_scan_file(path))
    return failures


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("check_no_scaffolding: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("check_no_scaffolding: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
