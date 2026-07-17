#!/usr/bin/env python3
"""Red-first contract for the build-scaffolding gate on shipped LLM-facing content."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_no_scaffolding


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="scaffolding-gate-")
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path


class ScaffoldingGateTests(Fixture):
    def test_clean_content_is_silent(self):
        self.write("skills/probe/SKILL.md", "# Probe\n\nDo the operational thing.\n")
        self.write("canonical/agents/probe.md", "# Probe agent\n\nInvestigate the failure.\n")
        self.assertEqual([], check_no_scaffolding.check(self.root))

    def test_build_task_reference_is_flagged(self):
        self.write("skills/probe/SKILL.md", "Boundary remains pending Task 38 for now.\n")
        failures = check_no_scaffolding.check(self.root)
        self.assertTrue(any("Task 38" in item for item in failures), failures)

    def test_hyphen_prefixed_task_is_flagged(self):
        self.write("skills/probe/SKILL.md", "## Runtime boundary (pre-Task 38)\n")
        failures = check_no_scaffolding.check(self.root)
        self.assertTrue(any("Task 38" in item for item in failures), failures)

    def test_spec_section_reference_is_flagged(self):
        self.write("skills/probe/SKILL.md", "Recorded here per spec Section 3, not elsewhere.\n")
        failures = check_no_scaffolding.check(self.root)
        self.assertTrue(any("spec Section 3" in item for item in failures), failures)

    def test_assembly_state_token_is_flagged(self):
        self.write("skills/probe/SKILL.md", "Projected in the content-building tree.\n")
        failures = check_no_scaffolding.check(self.root)
        self.assertTrue(any("content-building" in item for item in failures), failures)

    def test_methodology_phase_heading_is_not_a_false_positive(self):
        # `ops-tooling` legitimately uses "Phase 0 -- Requirements" as a real heading; the gate must
        # not touch it. The shipped `content-complete` state and `[unverified]` labels are content too.
        self.write(
            "skills/probe/SKILL.md",
            "## Phase 0 -- Requirements\n\nAssembly is content-complete; this claim is `[unverified]`.\n",
        )
        self.assertEqual([], check_no_scaffolding.check(self.root))

    def test_untracked_trees_are_ignored(self):
        # The gate scans shipped content only, not generator source or docs.
        self.write("scripts/notes.md", "Landed in Task 12.\n")
        self.assertEqual([], check_no_scaffolding.check(self.root))


if __name__ == "__main__":
    unittest.main()
