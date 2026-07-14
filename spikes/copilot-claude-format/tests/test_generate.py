#!/usr/bin/env python3
"""Contract tests for the Copilot/Claude projection generator."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import platform
import subprocess
import unittest
from pathlib import Path
from unittest import mock

SPIKE_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = SPIKE_ROOT / "scripts" / "generate.py"
SPEC = importlib.util.spec_from_file_location("format_boundary_generate", GENERATOR)
assert SPEC and SPEC.loader
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)


def _text(files: dict[Path, bytes], rel: str) -> str:
    return files[Path(rel)].decode("utf-8")


def _body(wrapper: str) -> str:
    parts = wrapper.split("---", 2)
    if len(parts) != 3:
        raise AssertionError("generated agent has no frontmatter")
    return parts[2].lstrip("\n")


def _hook_payload(runtime: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"FORMAT_BOUNDARY_SESSION_START:{runtime}",
        }
    }


class ProjectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.files = gen.render(SPIKE_ROOT)

    def test_runtime_extensions_and_delegation_fields(self) -> None:
        copilot = _text(self.files, "generated/copilot/agents/format-boundary-coordinator.agent.md")
        claude = _text(self.files, "generated/claude/agents/format-boundary-coordinator.md")
        self.assertIn("tools: ['agent']", copilot)
        self.assertIn("agents: ['format-boundary-worker']", copilot)
        self.assertIn("handoffs:", copilot)
        self.assertIn("tools: Agent(format-boundary-worker)", claude)
        self.assertNotIn("\nagents:", claude)
        self.assertNotIn("\nhandoffs:", claude)

    def test_every_wrapper_has_explicit_name(self) -> None:
        for rel, expected in (
            ("generated/copilot/agents/format-boundary-coordinator.agent.md", "format-boundary-coordinator"),
            ("generated/copilot/agents/format-boundary-worker.agent.md", "format-boundary-worker"),
            ("generated/claude/agents/format-boundary-coordinator.md", "format-boundary-coordinator"),
            ("generated/claude/agents/format-boundary-worker.md", "format-boundary-worker"),
        ):
            self.assertIn(f"name: {expected}\n", _text(self.files, rel))

    def test_shared_bodies_are_byte_identical_after_frontmatter(self) -> None:
        for name in ("format-boundary-coordinator", "format-boundary-worker"):
            canonical = (SPIKE_ROOT / "canonical" / "agents" / f"{name}.md").read_text(encoding="utf-8")
            copilot = _body(_text(self.files, f"generated/copilot/agents/{name}.agent.md"))
            claude = _body(_text(self.files, f"generated/claude/agents/{name}.md"))
            expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            self.assertEqual(expected_hash, hashlib.sha256(copilot.encode("utf-8")).hexdigest())
            self.assertEqual(expected_hash, hashlib.sha256(claude.encode("utf-8")).hexdigest())

    def test_worker_is_terminal_in_both_projections(self) -> None:
        copilot = _text(self.files, "generated/copilot/agents/format-boundary-worker.agent.md")
        claude = _text(self.files, "generated/claude/agents/format-boundary-worker.md")
        self.assertIn("tools: ['read', 'search']", copilot)
        self.assertNotIn("'agent'", copilot)
        self.assertNotIn("\nagents:", copilot)
        self.assertIn("tools: Read, Grep, Glob, Skill", claude)
        self.assertNotIn("Agent(", claude)

    def test_manifests_have_name_version_parity_and_runtime_paths(self) -> None:
        copilot = json.loads(_text(self.files, "plugin.json"))
        claude = json.loads(_text(self.files, ".claude-plugin/plugin.json"))
        self.assertEqual((copilot["name"], copilot["version"]), (claude["name"], claude["version"]))
        self.assertEqual(copilot["author"], claude["author"])
        self.assertEqual({"name", "version", "description", "author", "agents", "skills"}, set(copilot))
        self.assertEqual({"name", "version", "description", "author", "agents", "skills"}, set(claude))
        self.assertEqual("./generated/copilot/agents/", copilot["agents"])
        self.assertEqual([
            "./generated/claude/agents/format-boundary-coordinator.md",
            "./generated/claude/agents/format-boundary-worker.md",
        ], claude["agents"])
        self.assertNotIn("hooks", copilot)
        self.assertNotIn("hooks", claude)

    def test_skill_has_a_live_explicit_relative_reference_link(self) -> None:
        manifest = gen.load_manifest(SPIKE_ROOT)
        self.assertEqual(1, len(manifest["skills"]))
        declared = manifest["skills"][0]
        skill_dir = SPIKE_ROOT / "skills" / "format-boundary-probe"
        skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        name_line = next(line for line in frontmatter.splitlines() if line.startswith("name:"))
        self.assertEqual("skills/format-boundary-probe", declared["directory"])
        self.assertEqual(skill_dir.name, declared["name"])
        self.assertEqual(skill_dir.name, name_line.split(":", 1)[1].strip())
        target = "./references/contract.md"
        self.assertIn(f"]({target})", skill)
        self.assertEqual([target.removeprefix("./")], declared["references"])
        self.assertTrue((skill_dir / target).is_file())

    def test_hooks_are_format_specific_and_marker_only(self) -> None:
        copilot = json.loads(_text(self.files, "hooks.json"))
        claude = json.loads(_text(self.files, "hooks/hooks.json"))
        self.assertEqual({"hooks"}, set(copilot))
        self.assertEqual({"SessionStart"}, set(copilot["hooks"]))
        self.assertEqual(1, len(copilot["hooks"]["SessionStart"]))
        copilot_handler = copilot["hooks"]["SessionStart"][0]
        self.assertEqual({"type", "command", "windows", "linux", "osx"}, set(copilot_handler))
        self.assertEqual("command", copilot_handler["type"])
        self.assertTrue(copilot_handler["windows"].startswith("py -3 -c "))
        self.assertTrue(copilot_handler["linux"].startswith("python3 -c "))
        self.assertTrue(copilot_handler["osx"].startswith("python3 -c "))
        self.assertIn("FORMAT_BOUNDARY_SESSION_START:copilot", json.dumps(copilot))
        self.assertEqual({"hooks"}, set(claude))
        self.assertEqual({"SessionStart"}, set(claude["hooks"]))
        self.assertEqual(1, len(claude["hooks"]["SessionStart"]))
        claude_event = claude["hooks"]["SessionStart"][0]
        self.assertEqual({"hooks"}, set(claude_event))
        self.assertEqual(1, len(claude_event["hooks"]))
        claude_handler = claude_event["hooks"][0]
        self.assertEqual({"type", "command", "args"}, set(claude_handler))
        self.assertEqual("command", claude_handler["type"])
        self.assertEqual("python", claude_handler["command"])
        self.assertEqual([
            "${CLAUDE_PLUGIN_ROOT}/scripts/session_start_marker.py",
            "claude",
        ], claude_handler["args"])
        self.assertIn(Path("scripts/session_start_marker.py"), self.files)
        self.assertIn(
            "GENERATED by scripts/generate.py",
            _text(self.files, "scripts/session_start_marker.py"),
        )

    def test_materialized_current_os_copilot_handler_executes(self) -> None:
        copilot = json.loads((SPIKE_ROOT / "hooks.json").read_text(encoding="utf-8"))
        handler = copilot["hooks"]["SessionStart"][0]
        os_field = {"Windows": "windows", "Linux": "linux", "Darwin": "osx"}.get(
            platform.system()
        )
        self.assertIsNotNone(os_field, f"unsupported test OS: {platform.system()}")
        command = handler[os_field]
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        )
        self.assertEqual("", proc.stderr)
        self.assertEqual(_hook_payload("copilot"), json.loads(proc.stdout))

    def test_materialized_claude_exec_form_executes(self) -> None:
        claude = json.loads((SPIKE_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        handler = claude["hooks"]["SessionStart"][0]["hooks"][0]
        args = [
            value.replace("${CLAUDE_PLUGIN_ROOT}", str(SPIKE_ROOT))
            for value in handler["args"]
        ]
        proc = subprocess.run(
            [handler["command"], *args],
            shell=False,
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        )
        self.assertEqual("", proc.stderr)
        self.assertEqual(_hook_payload("claude"), json.loads(proc.stdout))

    def test_compatibility_report_records_nonportable_semantics(self) -> None:
        report = json.loads(_text(self.files, "compatibility.json"))
        self.assertTrue(report["two_agent_wrappers_required"])
        self.assertEqual("agents field plus agent tool", report["copilot"]["delegation_allowlist"])
        self.assertEqual("directory", report["copilot"]["agent_manifest_path_kind"])
        self.assertEqual("./generated/copilot/agents/", report["copilot"]["agent_manifest_path"])
        self.assertEqual(
            ["format-boundary-probe"], report["copilot"]["skill_registered_names"]
        )
        self.assertTrue(report["claude"]["agent_type_allowlist_enforced_when_main"])
        self.assertTrue(report["claude"]["agent_type_list_ignored_when_nested"])
        self.assertEqual("file-list", report["claude"]["agent_manifest_path_kind"])
        self.assertEqual([
            "./generated/claude/agents/format-boundary-coordinator.md",
            "./generated/claude/agents/format-boundary-worker.md",
        ], report["claude"]["agent_manifest_paths"])
        self.assertEqual([
            "format-boundary-spike:format-boundary-probe",
        ], report["claude"]["skill_registered_names"])
        self.assertEqual(
            "omitted-to-inherit-session-model", report["model_projection"]["spike"]
        )
        self.assertEqual("copilot-only", report["handoffs"])
        self.assertFalse(report["plugin_agent_scoped_hooks_portable"])
        self.assertTrue(report["hook_projection"]["standard_path_auto_discovery"])
        self.assertFalse(report["hook_projection"]["manifest_hook_key_present"])

    def test_compatibility_names_are_derived_from_canonical(self) -> None:
        renamed = copy.deepcopy(gen.load_manifest(SPIKE_ROOT))
        renamed["plugin"]["name"] = "renamed-spike"
        renamed["skills"][0]["name"] = "renamed-probe"
        report = gen._compatibility_report(renamed)
        self.assertEqual(["renamed-probe"], report["copilot"]["skill_registered_names"])
        self.assertEqual(
            ["renamed-spike:renamed-probe"],
            report["claude"]["skill_registered_names"],
        )

    def test_checked_in_outputs_match_a_fresh_render(self) -> None:
        self.assertEqual(10, len(self.files))
        self.assertEqual([], gen.check(SPIKE_ROOT))

    def test_check_detects_a_hand_edited_wrapper(self) -> None:
        actual = dict(self.files)
        wrapper = Path("generated/copilot/agents/format-boundary-worker.agent.md")
        actual[wrapper] += b"\nhand edit\n"
        issues = gen.compare_outputs(self.files, actual)
        self.assertTrue(any("stale" in issue and "format-boundary-worker" in issue
                            for issue in issues))


class InvalidCanonicalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = gen.load_manifest(SPIKE_ROOT)

    def test_unknown_capability_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][0]["capabilities"].append("teleport")
        with self.assertRaisesRegex(gen.ManifestError, "unknown capability.*teleport"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_missing_explicit_name_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        del bad["agents"][0]["name"]
        with self.assertRaisesRegex(gen.ManifestError, "name"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_dangling_delegate_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][0]["delegates_to"] = ["missing-worker"]
        with self.assertRaisesRegex(gen.ManifestError, "missing-worker"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_unknown_agent_key_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][0]["mdoel"] = "typo"
        with self.assertRaisesRegex(gen.ManifestError, "unknown agent key.*mdoel"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_agent_body_path_must_match_explicit_name(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][0]["body"] = "agents/format-boundary-worker.md"
        with self.assertRaisesRegex(
            gen.ManifestError, "body must be agents/format-boundary-coordinator.md"
        ):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_unknown_skill_dependency_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][1]["skills"] = ["missing-skill"]
        with self.assertRaisesRegex(gen.ManifestError, "unknown skill dependency.*missing-skill"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_invalid_skill_name_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["skills"][0]["name"] = "Not-Kebab-Case"
        with self.assertRaisesRegex(gen.ManifestError, "skill.*name must be kebab-case"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_skill_directory_must_match_name(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["skills"][0]["directory"] = "skills/different-name"
        with self.assertRaisesRegex(gen.ManifestError, "does not match directory"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_skill_frontmatter_name_must_match_inventory(self) -> None:
        skill_text = """---
name: different-name
---
[contract](./references/contract.md)
"""
        with mock.patch.object(Path, "read_text", return_value=skill_text):
            with self.assertRaisesRegex(gen.ManifestError, "frontmatter name.*does not match"):
                gen.validate_manifest(copy.deepcopy(self.manifest), SPIKE_ROOT)

    def test_skill_dependency_without_capability_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][1]["capabilities"].remove("skill")
        with self.assertRaisesRegex(gen.ManifestError, "capability 'skill'.*skills list"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_skill_capability_without_dependency_is_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][1]["skills"] = []
        with self.assertRaisesRegex(gen.ManifestError, "capability 'skill'.*skills list"):
            gen.validate_manifest(bad, SPIKE_ROOT)

    def test_pure_inventory_rejects_unexpected_skill_directory(self) -> None:
        issues = gen.compare_skill_inventory(
            {"format-boundary-probe": {"references/contract.md"}},
            {"format-boundary-probe", "shadow-skill"},
            {"format-boundary-probe": {"references/contract.md"}, "shadow-skill": set()},
        )
        self.assertEqual(
            ["unexpected runtime-visible skill directory: shadow-skill"], issues,
        )

    def test_pure_inventory_rejects_unexpected_reference(self) -> None:
        issues = gen.compare_skill_inventory(
            {"format-boundary-probe": {"references/contract.md"}},
            {"format-boundary-probe"},
            {"format-boundary-probe": {
                "references/contract.md", "references/uninventoried.md",
            }},
        )
        self.assertEqual([
            "skill 'format-boundary-probe' has unexpected runtime-visible reference: "
            "references/uninventoried.md",
        ], issues)

    def test_pure_body_inventory_rejects_orphan_body(self) -> None:
        issues = gen.compare_agent_body_inventory(
            {"agents/format-boundary-worker.md"},
            {"agents/format-boundary-worker.md", "agents/orphan.md"},
        )
        self.assertEqual(["unexpected canonical agent body: agents/orphan.md"], issues)

    def test_pure_link_parity_rejects_missing_and_extra_links(self) -> None:
        issues = gen.compare_reference_links(
            "format-boundary-probe",
            {"references/contract.md"},
            {"references/uninventoried.md"},
        )
        self.assertEqual([
            "skill 'format-boundary-probe' has unlinked inventoried references: "
            "references/contract.md",
            "skill 'format-boundary-probe' links un-inventoried references: "
            "references/uninventoried.md",
        ], issues)


if __name__ == "__main__":
    unittest.main()
