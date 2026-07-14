#!/usr/bin/env python3
"""Content and inventory contracts for the first Phase-2 skill cohort."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLEET = ROOT / "canonical" / "fleet.json"

_SPEC = importlib.util.spec_from_file_location(
    "production_generate_fleet", ROOT / "scripts" / "generate_fleet.py"
)
generate_fleet = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(generate_fleet)


STACK_DESCRIPTION = (
    "The single stack-definition point — what this team runs today, the stay-in-lane rule, and the "
    "platform boundary. Load before recommending any runtime, tool, or infrastructure change, and when "
    "choosing between observability backends. Triggers: \"what's our stack\", \"should we use X for this\", "
    "\"can we move this to Kubernetes / the cloud\", \"which backend do I query\". One file changes when the "
    "ground shifts."
)


def frontmatter_description(text: str) -> str:
    lines = text.splitlines()
    end = lines.index("---", 1)
    chunks = []
    collecting = False
    for line in lines[1:end]:
        if line.startswith("description:"):
            collecting = True
            inline = line.split(":", 1)[1].strip()
            if inline not in {">", ">-"}:
                chunks.append(inline.strip('"'))
        elif collecting and line.startswith((" ", "\t")):
            chunks.append(line.strip())
        elif collecting:
            break
    return " ".join(chunks)


class Phase2FirstCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fleet = json.loads(FLEET.read_text(encoding="utf-8"))

    def record(self, name: str) -> dict:
        return next(record for record in self.fleet["skills"] if record["name"] == name)

    def assert_inventory(self, name: str, expected: set[str]) -> None:
        root = ROOT / "skills" / name
        actual = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(expected, actual)

    def test_task10_stack_profile_is_the_single_stack_definition_point(self):
        record = self.record("stack-profile")
        self.assertEqual(
            {
                "name": "stack-profile",
                "state": "active",
                "directory": "skills/stack-profile",
                "references": [],
                "assets": [],
                "scripts": [],
            },
            record,
        )
        self.assert_inventory("stack-profile", {"SKILL.md"})
        text = (ROOT / "skills/stack-profile/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(STACK_DESCRIPTION, frontmatter_description(text))
        normalized = " ".join(text.split())
        for required in (
            "# Stack profile — current facts, not aspirations",
            "On-prem servers + PCF (VMware Tanzu Application Service)",
            "**No Kubernetes.**",
            "GCP is under evaluation for late 2026 — not a target today",
            "| Logs | Splunk (SPL) | Loki (LogQL) |",
            "| Metrics | Wavefront / VMware Aria Operations for Applications (WQL) | Mimir / Prometheus (PromQL) |",
            "BOSH, Ops Manager, Diego cells, Gorouter, CredHub/UAA",
            "Claude Sonnet 5 (copilot) → Claude Opus 4.8 (copilot) → GPT-5.4 (copilot)",
            "[unverified — confirmed for the team license tier in Phase 5",
            "<!-- profile canary: sp_7c2e — quoted output proves this file loaded; guarded by the tripwire test -->",
        ):
            self.assertIn(required, normalized)
        _manifest, ready = generate_fleet.load_and_validate(ROOT)
        self.assertEqual([], ready)
        active = [record for record in self.fleet["skills"] if record["state"] == "active"]
        planned = [record for record in self.fleet["skills"] if record["state"] == "planned"]
        self.assertEqual((1, 25), (len(active), len(planned)))


if __name__ == "__main__":
    unittest.main()
