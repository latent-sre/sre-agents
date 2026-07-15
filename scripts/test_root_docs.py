#!/usr/bin/env python3
"""Task 46 contracts for the root-document split and absorption evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLEET = json.loads((ROOT / "canonical/fleet.json").read_text(encoding="utf-8"))
EVIDENCE = ROOT / "docs/superpowers/evidence/task-46-root-doc-absorption.md"
AGENTS_SHA256 = "548738b7655f15cc8348e947c9b98dc61144b44adb641bfefbd7163c13f1e045"
EXPECTED_RANGES = (
    "AGENTS.md:1-16",
    "AGENTS.md:17-52",
    "AGENTS.md:53-70",
    "AGENTS.md:71-89",
    "AGENTS.md:90-119",
    "AGENTS.md:120-126",
    "AGENTS.md:127-130",
    "AGENTS.md:131-143",
    "AGENTS.md:144-158",
    "AGENTS.md:159-167",
    "AGENTS.md:168-191",
    "CLAUDE.md:1-6",
    "CLAUDE.md:7-34",
    "CLAUDE.md:35-53",
    "CLAUDE.md:54-57",
)


class RootDocumentSplitTests(unittest.TestCase):
    def test_agents_is_short_repository_guidance_only(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(AGENTS_SHA256, hashlib.sha256(text.encode("utf-8")).hexdigest())

        for required in (
            "This repository develops",
            "`canonical/fleet.json`",
            "`canonical/agents/`",
            "`skills/`",
            "`generated/`",
            "`scripts/`",
            "`evals/`",
            "Section 0",
            "`py -3 scripts/gate_a.py`",
            "manual",
            "never CI",
            "[CONTRIBUTING.md](CONTRIBUTING.md)",
        ):
            self.assertIn(required, text)

        self.assertLessEqual(len(text.splitlines()), 45)
        self.assertNotIn("|", text, "AGENTS.md must not grow a roster or tool-census table")
        for agent in FLEET["agents"]:
            self.assertNotIn(f"`{agent['name']}`", text)
        for forbidden in (
            "## Stack profile",
            "## The roster",
            "## Skills",
            "The guard only sees",
            ".claude/agents/",
            ".claude/skills/",
            "sde-engineer",
            "code-reviewer",
            "security-reviewer",
            "sre-engineer",
            "prompt-engineer",
            "Splunk",
            "Wavefront",
            "Moogsoft",
            "ThousandEyes",
        ):
            self.assertNotIn(forbidden, text)

    def test_claude_entrypoint_is_minimal_and_exact(self) -> None:
        expected = (
            "@AGENTS.md\n\n"
            "Use `py -3` for repository Python commands on Windows; `python3` is the "
            "Microsoft Store stub on this machine.\n"
        )
        actual = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(expected, actual)

    def test_readme_inventory_matches_canonical_fleet(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        start = "<!-- fleet-inventory:start -->"
        end = "<!-- fleet-inventory:end -->"
        self.assertEqual(1, text.count(start))
        self.assertEqual(1, text.count(end))
        inventory = text.split(start, 1)[1].split(end, 1)[0]
        agents_part, skills_part = inventory.split("### Skills (26)", 1)

        row = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)
        self.assertEqual(
            [agent["name"] for agent in FLEET["agents"]],
            row.findall(agents_part),
        )
        self.assertEqual(
            [skill["name"] for skill in FLEET["skills"]],
            row.findall(skills_part),
        )
        self.assertIn("### Agents (5)", agents_part)
        self.assertNotIn("Both tools read `.claude/` directly", text)
        self.assertNotRegex(text, r"\.claude[\\/](?:agents|skills)")
        self.assertIn("separate VS Code /\nGitHub Copilot and Claude Code runtime definitions", text)
        self.assertIn("runtime-specific projections", text)
        self.assertIn("ignores a nested delegator's target list", text)
        self.assertIn("terminal agents remain terminal by omitting `Agent`", text)
        for legacy_name in ("sde-engineer", "code-reviewer", "prompt-engineer"):
            self.assertNotIn(legacy_name, text)

    def test_contributing_is_a_real_target_for_agents(self) -> None:
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for required in (
            "Personal first, promote by PR",
            "`canonical/fleet.json`",
            "`canonical/agents/`",
            "`skills/`",
            "Do not edit generated projections",
            "`py -3 scripts/gate_a.py`",
            "manually, never in CI",
            "`~/.copilot/{agents,skills}`",
            "`agent-authoring` method",
            "not yet active",
            "Promotion and production onboarding remain blocked",
            "canonical `plugin.version`",
            "Copilot safe-recovery",
            "runtime-tree projections",
            "exact reviewed `origin/main` SHA",
            "distinct maintainer",
            "immutable `fleet-v<version>`",
            "`.github/CODEOWNERS`",
            "`* @<maintainer>`",
            "one-release stub",
            "26 hours",
            "[verified]",
            "[sourced]",
            "[unverified]",
        ):
            self.assertIn(required, text)

    def test_absorption_evidence_covers_both_legacy_files_without_gaps(self) -> None:
        text = EVIDENCE.read_text(encoding="utf-8")
        row_pattern = re.compile(
            r"^\| `((AGENTS|CLAUDE)\.md:(\d+)-(\d+))` \| ([^|\n]+) \| ([^|\n]+) \| (Complete) \|$",
            re.MULTILINE,
        )
        rows = row_pattern.findall(text)
        self.assertEqual(list(EXPECTED_RANGES), [row[0] for row in rows])

        coverage: dict[str, list[int]] = {"AGENTS.md": [], "CLAUDE.md": []}
        for source_range, source, start, end, absorbed, home, status in rows:
            self.assertTrue(absorbed.strip(), source_range)
            self.assertTrue(home.strip(), source_range)
            self.assertEqual("Complete", status)
            coverage[f"{source}.md"].extend(range(int(start), int(end) + 1))

            path_tokens = []
            for token in re.findall(r"`([^`]+)`", home):
                if "/" not in token and not token.endswith((".md", ".json", ".py")):
                    continue
                candidate = token.lstrip("@").rstrip("/")
                path_tokens.append(candidate)
                if "*" in candidate:
                    self.assertTrue(list(ROOT.glob(candidate)), f"{source_range}: {candidate}")
                else:
                    self.assertTrue((ROOT / candidate).exists(), f"{source_range}: {candidate}")
            self.assertTrue(path_tokens, f"{source_range}: no resolvable home path")

        for source, covered in coverage.items():
            line_count = len((ROOT / "legacy/claude-fleet" / source).read_text(encoding="utf-8").splitlines())
            self.assertEqual(list(range(1, line_count + 1)), covered, source)

        homes = {row[0]: row[5] for row in rows}
        required_mappings = {
            "AGENTS.md:71-89": (
                "canonical/agents/reviewer.md",
                "canonical/agents/scribe.md",
                "canonical/agents/sre.md",
                "canonical/agents/observer.md",
                "canonical/fleet.json",
            ),
            "AGENTS.md:90-119": (
                "canonical/agents/reviewer.md",
                "canonical/agents/sre.md",
                "skills/agent-security/SKILL.md",
            ),
            "CLAUDE.md:7-34": (
                "skills/agent-authoring/SKILL.md",
                "skills/agent-authoring/references/roster.md",
                "skills/eng-ladder/SKILL.md",
                "skills/production-change-gate/SKILL.md",
                "canonical/fleet.json",
            ),
            "CLAUDE.md:35-53": (
                "skills/agent-authoring/references/roster.md",
                "docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md",
            ),
        }
        for source_range, required in required_mappings.items():
            for token in required:
                self.assertIn(token, homes[source_range], f"{source_range}: {token}")

        security = (ROOT / "skills/agent-security/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Delegation is not isolation", security)
        self.assertIn("provides no agent-initiated", security)
        self.assertIn("content hash", security)
        roster = (ROOT / "skills/agent-authoring/references/roster.md").read_text(encoding="utf-8")
        self.assertIn("reasoned default, not a measured result", roster)
        self.assertIn("controlled A/B", roster)
        self.assertIn("prevents cheaply tiering", roster)
        production_gate = (ROOT / "skills/production-change-gate/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("The checklist is not the enforcement", production_gate)
        self.assertIn("administrators", production_gate)
        design = (
            ROOT / "docs/superpowers/specs/2026-07-13-copilot-fleet-redesign-design.md"
        ).read_text(encoding="utf-8")
        self.assertIn("coordinator subagent would add a round-trip", design)
        self.assertIn("reasoned default, not a measured result", design)
        self.assertIn("controlled A/B", design)
        boundary_checks = {
            "canonical/agents/reviewer.md": "cite the builder's packet test evidence or CI",
            "canonical/agents/scribe.md": "cannot execute anything, by tool absence",
            "canonical/agents/sre.md": "when execute is absent",
            "canonical/agents/observer.md": "when execute is absent",
        }
        for path, doctrine in boundary_checks.items():
            self.assertIn(doctrine, (ROOT / path).read_text(encoding="utf-8"), path)
        self.assertIn("15/15 sections absorbed", text)
        self.assertNotIn("Incomplete", text)
        self.assertNotIn("Missing", text)

    def test_gate_a_runs_the_root_document_contract_exactly_once(self) -> None:
        path = ROOT / "scripts/gate_a.py"
        spec = importlib.util.spec_from_file_location("task46_gate_a", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = ("Root document split", ["scripts/test_root_docs.py"], None)
        self.assertEqual(1, module.STEPS.count(expected))


if __name__ == "__main__":
    unittest.main()
