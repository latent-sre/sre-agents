#!/usr/bin/env python3
"""Contract tests for the Copilot/Claude projection generator."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import tempfile
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


def _minimal_manifest() -> dict:
    return {
        "schema_version": 1,
        "plugin": {
            "name": "projection-fixture",
            "version": "0.0.1",
            "description": "Temporary projection contract fixture.",
            "author": {"name": "test-suite"},
        },
        "commands": [],
        "skills": [],
        "agents": [],
    }


def _terminal_agent(name: str = "probe-worker") -> dict:
    return {
        "name": name,
        "description": "Terminal projection contract worker.",
        "body": f"agents/{name}.md",
        "capabilities": ["read"],
        "skills": [],
        "delegates_to": [],
        "handoffs": [],
    }


def _write_fixture(root: Path, manifest: dict, files: dict[str, str] | None = None) -> None:
    canonical = root / "canonical"
    canonical.mkdir(parents=True, exist_ok=True)
    (canonical / "fleet.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    for relative, content in (files or {}).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _skill_bundle() -> tuple[dict, dict[str, str]]:
    skill = {
        "name": "probe-skill",
        "directory": "skills/probe-skill",
        "references": ["references/nested/contract.md"],
        "assets": ["assets/nested/template.yaml"],
        "scripts": ["scripts/nested/check.py"],
    }
    files = {
        "skills/probe-skill/SKILL.md": """---
name: probe-skill
description: Temporary bundled-skill fixture.
---

[contract](./references/nested/contract.md)
[template](./assets/nested/template.yaml)
[check](./scripts/nested/check.py)
""",
        "skills/probe-skill/references/nested/contract.md": "PROBE_REFERENCE\n",
        "skills/probe-skill/assets/nested/template.yaml": "marker: PROBE_ASSET\n",
        "skills/probe-skill/scripts/nested/check.py": "MARKER = 'PROBE_SCRIPT'\n",
    }
    return skill, files


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
        expected_keys = {
            "name", "version", "description", "author", "agents", "skills", "commands",
        }
        self.assertEqual(expected_keys, set(copilot))
        self.assertEqual(expected_keys, set(claude))
        self.assertEqual("./generated/copilot/agents/", copilot["agents"])
        self.assertEqual([
            "./generated/claude/agents/format-boundary-coordinator.md",
            "./generated/claude/agents/format-boundary-worker.md",
        ], claude["agents"])
        self.assertEqual([], copilot["commands"])
        self.assertEqual([], claude["commands"])
        self.assertNotIn("hooks", copilot)
        self.assertNotIn("hooks", claude)

    def test_skill_has_exact_live_bundle_inventory(self) -> None:
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
        expected = {
            "references": ["references/contract.md"],
            "assets": ["assets/inventory-marker.txt"],
            "scripts": ["scripts/inventory_marker.py"],
        }
        for kind, relatives in expected.items():
            self.assertEqual(relatives, declared[kind])
            for relative in relatives:
                target = f"./{relative}"
                self.assertIn(f"]({target})", skill)
                self.assertTrue((skill_dir / relative).is_file())

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
        self.assertEqual(2, report["canonical_agent_count"])
        self.assertEqual(4, report["generated_wrapper_count"])
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
            "wrapper-model-fields-omitted-to-inherit-session-model",
            report["model_projection"]["spike"],
        )
        copilot_policy = report["model_projection"]["copilot"]
        claude_policy = report["model_projection"]["claude"]
        self.assertEqual([], copilot_policy["configured"])
        self.assertEqual("list", copilot_policy["shape"])
        self.assertFalse(copilot_policy["emitted"])
        self.assertIsNone(claude_policy["configured"])
        self.assertEqual("scalar", claude_policy["shape"])
        self.assertFalse(claude_policy["emitted"])
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
        manifest = gen.load_manifest(SPIKE_ROOT)
        self.assertEqual(6 + (2 * len(manifest["agents"])), len(self.files))
        self.assertEqual([], gen.check(SPIKE_ROOT))

    def test_check_detects_a_hand_edited_wrapper(self) -> None:
        actual = dict(self.files)
        wrapper = Path("generated/copilot/agents/format-boundary-worker.agent.md")
        actual[wrapper] += b"\nhand edit\n"
        issues = gen.compare_outputs(self.files, actual)
        self.assertTrue(any("stale" in issue and "format-boundary-worker" in issue
                            for issue in issues))


class ReusableGeneratorContractTests(unittest.TestCase):
    def test_empty_scaffold_emits_explicit_empty_runtime_registrations(self) -> None:
        manifest = _minimal_manifest()
        manifest["models"] = {"copilot": [], "claude": None}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)

            files = gen.render(root)

        expected_keys = {
            "name", "version", "description", "author", "agents", "skills", "commands",
        }
        for runtime_manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            value = json.loads(_text(files, runtime_manifest))
            self.assertEqual(expected_keys, set(value))
            self.assertEqual([], value["agents"])
            self.assertEqual([], value["skills"])
            self.assertEqual([], value["commands"])
        fixture = json.loads((
            SPIKE_ROOT / "tests/fixtures/empty-plugin/.claude-plugin/plugin.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual([], fixture["agents"])
        self.assertEqual([], fixture["skills"])
        self.assertEqual([], fixture["commands"])
        self.assertFalse(any("generated/" in path.as_posix() for path in files))
        report = json.loads(_text(files, "compatibility.json"))
        self.assertEqual(0, report["canonical_agent_count"])
        self.assertEqual(0, report["generated_wrapper_count"])
        self.assertEqual(0, report["canonical_command_count"])

    def test_empty_scaffold_check_reports_every_leftover_agent_file(self) -> None:
        manifest = _minimal_manifest()
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)
            gen.write(root)
            stale_paths = (
                "generated/copilot/agents/archive/removed.agent.md",
                "generated/copilot/agents/wrong-suffix.md",
                "generated/claude/agents/archive/removed.md",
            )
            for relative in stale_paths:
                stale = root / relative
                stale.parent.mkdir(parents=True, exist_ok=True)
                stale.write_text("stale\n", encoding="utf-8")

            issues = gen.check(root)

        self.assertEqual([
            f"unexpected generated file: {relative}"
            for relative in sorted(stale_paths)
        ], issues)

    def test_write_converges_after_agent_removal(self) -> None:
        manifest = _minimal_manifest()
        manifest["agents"] = [_terminal_agent("first-worker"), _terminal_agent("removed-worker")]
        files = {
            "canonical/agents/first-worker.md": "First body.\n",
            "canonical/agents/removed-worker.md": "Removed body.\n",
        }
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            gen.write(root)

            manifest["agents"] = [manifest["agents"][0]]
            _write_fixture(root, manifest)
            (root / "canonical/agents/removed-worker.md").unlink()
            gen.write(root)

            self.assertTrue(
                (root / "generated/copilot/agents/first-worker.agent.md").is_file()
            )
            self.assertFalse(
                (root / "generated/copilot/agents/removed-worker.agent.md").exists()
            )
            self.assertFalse(
                (root / "generated/claude/agents/removed-worker.md").exists()
            )
            self.assertEqual([], gen.check(root))

    def test_write_refuses_link_like_expected_targets_and_parents(self) -> None:
        fixtures = (
            ("plugin.json", "plugin.json"),
            ("generated/copilot/agents/probe-worker.agent.md", "probe-worker.agent.md"),
            ("generated/copilot/agents/probe-worker.agent.md", "copilot"),
        )
        for relative, unsafe_name in fixtures:
            with self.subTest(relative=relative, unsafe_name=unsafe_name):
                manifest = _minimal_manifest()
                files: dict[str, str] = {}
                if "probe-worker" in relative:
                    manifest["agents"] = [_terminal_agent()]
                    files["canonical/agents/probe-worker.md"] = "Body.\n"
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("do not follow\n", encoding="utf-8")
                    real_check = gen._is_link_or_junction

                    def classify(path: Path) -> bool:
                        return path.name == unsafe_name or real_check(path)

                    with mock.patch.object(
                        gen, "_is_link_or_junction", side_effect=classify
                    ):
                        with self.assertRaisesRegex(
                            gen.ManifestError, "write through.*link or junction"
                        ):
                            gen.write(root)

    def test_write_refuses_hardlinked_expected_output(self) -> None:
        manifest = _minimal_manifest()
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)
            outside = root / "outside.txt"
            outside.write_text("must remain unchanged\n", encoding="utf-8")
            target = root / "plugin.json"
            try:
                os.link(outside, target)
            except OSError as exc:
                self.skipTest(f"hardlink creation unavailable: {exc}")

            with self.assertRaisesRegex(gen.ManifestError, "hardlinked output"):
                gen.write(root)

            self.assertEqual("must remain unchanged\n", outside.read_text(encoding="utf-8"))

    def test_write_replaces_outputs_atomically_and_cleans_failed_temps(self) -> None:
        manifest = _minimal_manifest()
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)
            gen.write(root)
            first_relative = next(iter(gen.render(root)))
            first_target = root / first_relative
            original = first_target.read_bytes()

            manifest["plugin"]["description"] = "Changed projection fixture."
            _write_fixture(root, manifest)
            with mock.patch.object(
                gen.os, "replace", side_effect=OSError("simulated replace failure")
            ):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    gen.write(root)

            self.assertEqual(original, first_target.read_bytes())
            self.assertEqual([], list(root.rglob("*.tmp")))

    def test_check_refuses_link_like_expected_targets_and_parents(self) -> None:
        for unsafe_name in ("plugin.json", ".claude-plugin", "generated"):
            with self.subTest(unsafe_name=unsafe_name):
                manifest = _minimal_manifest()
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest)
                    real_check = gen._is_link_or_junction

                    def classify(path: Path) -> bool:
                        return path.name == unsafe_name or real_check(path)

                    with mock.patch.object(
                        gen, "_is_link_or_junction", side_effect=classify
                    ):
                        with self.assertRaisesRegex(
                            gen.ManifestError, "inspect through.*link or junction"
                        ):
                            gen.check(root)

    def test_check_refuses_hardlinked_expected_output(self) -> None:
        manifest = _minimal_manifest()
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)
            outside = root / "outside.txt"
            outside.write_text("must remain unchanged\n", encoding="utf-8")
            target = root / "plugin.json"
            try:
                os.link(outside, target)
            except OSError as exc:
                self.skipTest(f"hardlink creation unavailable: {exc}")

            with self.assertRaisesRegex(gen.ManifestError, "hardlinked output"):
                gen.check(root)

    def test_canonical_authority_rejects_link_like_root_and_manifest(self) -> None:
        for unsafe_name in ("canonical", "fleet.json"):
            with self.subTest(unsafe_name=unsafe_name):
                manifest = _minimal_manifest()
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest)
                    real_check = gen._is_link_or_junction

                    def classify(path: Path) -> bool:
                        return path.name == unsafe_name or real_check(path)

                    with mock.patch.object(
                        gen, "_is_link_or_junction", side_effect=classify
                    ):
                        with self.assertRaisesRegex(
                            gen.ManifestError, "canonical.*link or junction"
                        ):
                            gen.load_manifest(root)

    def test_windows_reparse_points_are_treated_as_links_without_path_helper(self) -> None:
        fake_stat = mock.Mock(st_mode=0, st_file_attributes=0x400)
        with mock.patch.object(Path, "lstat", return_value=fake_stat):
            self.assertTrue(gen._is_link_or_junction(Path("reparse-point")))

    def test_skill_bundle_accepts_exact_reference_asset_and_script_inventory(self) -> None:
        manifest = _minimal_manifest()
        skill, files = _skill_bundle()
        manifest["skills"] = [skill]
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)

            generated = gen.render(root)

        for runtime_manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            value = json.loads(_text(generated, runtime_manifest))
            self.assertEqual("./skills/", value["skills"])
            self.assertEqual([], value["agents"])

    def test_command_inventory_projects_runtime_specific_paths(self) -> None:
        manifest = _minimal_manifest()
        manifest["commands"] = ["commands/probe-command.md"]
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(
                root,
                manifest,
                {"commands/probe-command.md": "Run the format boundary probe.\n"},
            )

            generated = gen.render(root)

        copilot = json.loads(_text(generated, "plugin.json"))
        claude = json.loads(_text(generated, ".claude-plugin/plugin.json"))
        self.assertEqual("./commands/", copilot["commands"])
        self.assertEqual(["./commands/probe-command.md"], claude["commands"])

    def test_command_inventory_rejects_missing_unexpected_and_nested_files(self) -> None:
        fixtures = (
            (["commands/missing.md"], {}, "missing canonical command"),
            ([], {"commands/rogue.md": "rogue\n"}, "unexpected canonical command"),
            ([], {"commands/nested/rogue.md": "rogue\n"}, "command directory"),
        )
        for commands, files, diagnostic in fixtures:
            with self.subTest(commands=commands, files=tuple(files)):
                manifest = _minimal_manifest()
                manifest["commands"] = commands
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(gen.ManifestError, diagnostic):
                        gen.validate_manifest(manifest, root)

    def test_default_discovery_paths_cannot_bypass_canonical_inventory(self) -> None:
        fixtures = (
            ("agents/rogue.md", "rogue agent\n", "default agent"),
            ("SKILL.md", "---\nname: rogue\n---\n", "root SKILL"),
            ("commands/rogue.md", "rogue command\n", "command"),
        )
        for relative, content, diagnostic in fixtures:
            with self.subTest(relative=relative):
                manifest = _minimal_manifest()
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, {relative: content})
                    with self.assertRaisesRegex(gen.ManifestError, diagnostic):
                        gen.validate_manifest(manifest, root)

    def test_skill_bundle_rejects_files_outside_known_bundle_roots(self) -> None:
        for relative in ("secret.txt", "legacy/old.md"):
            with self.subTest(relative=relative):
                manifest = _minimal_manifest()
                skill, files = _skill_bundle()
                manifest["skills"] = [skill]
                files[f"skills/probe-skill/{relative}"] = "not inventoried\n"
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(
                        gen.ManifestError,
                        "unexpected skill path.*" + relative.split("/", 1)[0],
                    ):
                        gen.validate_manifest(manifest, root)

    def test_skill_bundle_rejects_symlink_escape(self) -> None:
        manifest = _minimal_manifest()
        skill, files = _skill_bundle()
        manifest["skills"] = [skill]
        link_relative = "skills/probe-skill/assets/nested/template.yaml"
        del files[link_relative]
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            outside = root / "outside-template.yaml"
            outside.write_text("outside: true\n", encoding="utf-8")
            link = root / link_relative
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(outside, link)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(gen.ManifestError, "link or junction"):
                gen.validate_manifest(manifest, root)

    def test_skill_bundle_link_guard_is_fail_closed(self) -> None:
        manifest = _minimal_manifest()
        skill, files = _skill_bundle()
        manifest["skills"] = [skill]
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            real_check = gen._is_link_or_junction

            def classify(path: Path) -> bool:
                return path.name == "template.yaml" or real_check(path)

            with mock.patch.object(gen, "_is_link_or_junction", side_effect=classify):
                with self.assertRaisesRegex(gen.ManifestError, "link or junction"):
                    gen.validate_manifest(manifest, root)

    def test_owned_tree_walk_prunes_link_like_directories_before_descent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            nested = root / "link-like" / "must-not-be-visited.txt"
            nested.parent.mkdir(parents=True)
            nested.write_text("outside stand-in\n", encoding="utf-8")
            real_check = gen._is_link_or_junction

            def classify(path: Path) -> bool:
                return path.name == "link-like" or real_check(path)

            with mock.patch.object(gen, "_is_link_or_junction", side_effect=classify):
                visited = {
                    path.relative_to(root).as_posix()
                    for path in gen._walk_tree_without_following_links(root)
                }

        self.assertIn("link-like", visited)
        self.assertNotIn("link-like/must-not-be-visited.txt", visited)

    def test_skill_bundle_rejects_missing_and_unexpected_files_by_kind(self) -> None:
        for kind, relative in (
            ("references", "references/nested/contract.md"),
            ("assets", "assets/nested/template.yaml"),
            ("scripts", "scripts/nested/check.py"),
        ):
            with self.subTest(kind=kind, condition="missing"):
                manifest = _minimal_manifest()
                skill, files = _skill_bundle()
                manifest["skills"] = [skill]
                del files[f"skills/probe-skill/{relative}"]
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(
                        gen.ManifestError, f"missing inventoried {kind[:-1]}.*{relative}"
                    ):
                        gen.validate_manifest(manifest, root)

            with self.subTest(kind=kind, condition="unexpected"):
                manifest = _minimal_manifest()
                skill, files = _skill_bundle()
                manifest["skills"] = [skill]
                extra = f"{kind}/nested/uninventoried.txt"
                files[f"skills/probe-skill/{extra}"] = "unexpected\n"
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(
                        gen.ManifestError,
                        f"unexpected runtime-visible {kind[:-1]}.*{extra}",
                    ):
                        gen.validate_manifest(manifest, root)

    def test_skill_bundle_paths_are_posix_relative_and_kind_scoped(self) -> None:
        invalid_values = (
            ("scripts", "assets/template.yaml"),
            ("scripts", "scripts/../assets/template.yaml"),
            ("scripts", "scripts\\check.py"),
            ("assets", "/assets/template.yaml"),
        )
        for kind, value in invalid_values:
            with self.subTest(kind=kind, value=value):
                manifest = _minimal_manifest()
                skill, files = _skill_bundle()
                skill[kind] = [value]
                manifest["skills"] = [skill]
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(gen.ManifestError, f"invalid {kind[:-1]} path"):
                        gen.validate_manifest(manifest, root)

    def test_runtime_model_policy_projects_only_runtime_specific_shapes(self) -> None:
        manifest = _minimal_manifest()
        manifest["models"] = {
            "copilot": ["copilot-primary", "copilot-fallback"],
            "claude": "sonnet",
        }
        manifest["agents"] = [_terminal_agent()]
        files = {"canonical/agents/probe-worker.md": "Do the bounded probe.\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)

            generated = gen.render(root)

        copilot = _text(generated, "generated/copilot/agents/probe-worker.agent.md")
        claude = _text(generated, "generated/claude/agents/probe-worker.md")
        self.assertIn("model: ['copilot-primary', 'copilot-fallback']\n", copilot)
        self.assertNotIn('model: "sonnet"', copilot)
        self.assertIn('model: "sonnet"\n', claude)
        self.assertNotIn("copilot-primary", claude)
        for runtime_manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            value = json.loads(_text(generated, runtime_manifest))
            self.assertIn("agents", value)
            self.assertEqual([], value["skills"])
        report = json.loads(_text(generated, "compatibility.json"))
        self.assertEqual(
            ["copilot-primary", "copilot-fallback"],
            report["model_projection"]["copilot"]["configured"],
        )
        self.assertEqual(
            "sonnet", report["model_projection"]["claude"]["configured"]
        )
        self.assertTrue(report["model_projection"]["copilot"]["emitted"])
        self.assertTrue(report["model_projection"]["claude"]["emitted"])
        self.assertEqual(1, report["canonical_agent_count"])
        self.assertEqual(2, report["generated_wrapper_count"])

    def test_configured_models_are_not_reported_emitted_without_agents(self) -> None:
        manifest = _minimal_manifest()
        manifest["models"] = {"copilot": ["copilot-primary"], "claude": "sonnet"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest)
            report = json.loads(_text(gen.render(root), "compatibility.json"))
        self.assertEqual(0, report["canonical_agent_count"])
        self.assertEqual(0, report["generated_wrapper_count"])
        self.assertFalse(report["model_projection"]["copilot"]["emitted"])
        self.assertFalse(report["model_projection"]["claude"]["emitted"])

    def test_absent_or_empty_model_policy_omits_models(self) -> None:
        for policy in (None, {"copilot": [], "claude": None}):
            with self.subTest(policy=policy):
                manifest = _minimal_manifest()
                if policy is not None:
                    manifest["models"] = policy
                manifest["agents"] = [_terminal_agent()]
                files = {"canonical/agents/probe-worker.md": "Do the bounded probe.\n"}
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    generated = gen.render(root)
                copilot = _text(
                    generated, "generated/copilot/agents/probe-worker.agent.md"
                ).split("---", 2)[1]
                claude = _text(
                    generated, "generated/claude/agents/probe-worker.md"
                ).split("---", 2)[1]
                self.assertNotIn("\nmodel:", copilot)
                self.assertNotIn("\nmodel:", claude)

    def test_runtime_model_policy_rejects_crossed_and_ambiguous_values(self) -> None:
        invalid = (
            ({"copilot": "copilot-primary", "claude": None}, "models.copilot"),
            ({"copilot": [], "claude": ["claude-sonnet"]}, "models.claude"),
            ({"copilot": [""], "claude": None}, "models.copilot"),
            ({"copilot": ["same", "same"], "claude": None}, "models.copilot"),
            ({"copilot": [], "claude": "  "}, "models.claude"),
            ({"copilot": [" padded"], "claude": None}, "models.copilot"),
            ({"copilot": ["line\nbreak"], "claude": None}, "models.copilot"),
            ({"copilot": [], "claude": "sonnet\t"}, "models.claude"),
            ({"copilot": [], "claude": "sonnet\u0000"}, "models.claude"),
            ({"copilot": []}, "missing required key.*claude"),
            ({"claude": None}, "missing required key.*copilot"),
            ({"copilot": [], "claude": None, "typo": "x"}, "unknown models key"),
        )
        for policy, diagnostic in invalid:
            with self.subTest(policy=policy):
                manifest = _minimal_manifest()
                manifest["models"] = policy
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest)
                    with self.assertRaisesRegex(gen.ManifestError, diagnostic):
                        gen.validate_manifest(manifest, root)

    def test_frontmatter_scalars_must_be_trimmed_single_line_printable_text(self) -> None:
        for unsafe in (" leading", "trailing ", "line\nbreak", "line\u2028break"):
            with self.subTest(unsafe=repr(unsafe)):
                manifest = _minimal_manifest()
                manifest["plugin"]["description"] = unsafe
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest)
                    with self.assertRaisesRegex(
                        gen.ManifestError, "trimmed.*single-line printable"
                    ):
                        gen.validate_manifest(manifest, root)

    def test_agent_level_model_override_remains_rejected(self) -> None:
        manifest = _minimal_manifest()
        agent = _terminal_agent()
        agent["model"] = "runtime-leak"
        manifest["agents"] = [agent]
        files = {"canonical/agents/probe-worker.md": "Do the bounded probe.\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(gen.ManifestError, "unknown agent key.*model"):
                gen.validate_manifest(manifest, root)

    def test_skill_requires_explicit_inventory_arrays(self) -> None:
        for missing in ("references", "assets", "scripts"):
            with self.subTest(missing=missing):
                manifest = _minimal_manifest()
                skill, files = _skill_bundle()
                del skill[missing]
                manifest["skills"] = [skill]
                with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
                    root = Path(temporary)
                    _write_fixture(root, manifest, files)
                    with self.assertRaisesRegex(
                        gen.ManifestError, f"missing required key.*{missing}"
                    ):
                        gen.validate_manifest(manifest, root)

    def test_agent_body_paths_are_canonical_posix_paths(self) -> None:
        manifest = _minimal_manifest()
        agent = _terminal_agent()
        agent["body"] = "agents\\probe-worker.md"
        manifest["agents"] = [agent]
        files = {"canonical/agents/probe-worker.md": "Body.\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(gen.ManifestError, "body must be canonical POSIX"):
                gen.validate_manifest(manifest, root)

    def test_reference_links_are_canonical_posix_paths(self) -> None:
        manifest = _minimal_manifest()
        skill, files = _skill_bundle()
        manifest["skills"] = [skill]
        files["skills/probe-skill/SKILL.md"] = files[
            "skills/probe-skill/SKILL.md"
        ].replace(
            "./references/nested/contract.md",
            "./references/nested\\contract.md",
        )
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(gen.ManifestError, "invalid reference link path"):
                gen.validate_manifest(manifest, root)

    def test_agent_body_must_end_with_line_feed(self) -> None:
        manifest = _minimal_manifest()
        manifest["agents"] = [_terminal_agent()]
        files = {"canonical/agents/probe-worker.md": "Body without final LF"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(gen.ManifestError, "must end with a line feed"):
                gen.validate_manifest(manifest, root)

    def test_canonical_agent_directory_rejects_wrong_extension_files(self) -> None:
        manifest = _minimal_manifest()
        files = {"canonical/agents/orphan.md.bak": "orphan\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(
                gen.ManifestError, "unexpected canonical agent body.*orphan.md.bak"
            ):
                gen.validate_manifest(manifest, root)

    def test_agent_requires_at_least_one_capability(self) -> None:
        manifest = _minimal_manifest()
        agent = _terminal_agent()
        agent["capabilities"] = []
        manifest["agents"] = [agent]
        files = {"canonical/agents/probe-worker.md": "Body.\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            with self.assertRaisesRegex(gen.ManifestError, "at least one capability"):
                gen.validate_manifest(manifest, root)


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

    def test_unknown_and_duplicate_manifest_keys_are_rejected(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["agents"][0]["mdoel"] = "typo"
        with self.assertRaisesRegex(gen.ManifestError, "unknown agent key.*mdoel"):
            gen.validate_manifest(bad, SPIKE_ROOT)

        duplicate = json.dumps(_minimal_manifest()).replace(
            '"schema_version": 1',
            '"schema_version": 1, "schema_version": 1',
            1,
        )
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir(parents=True)
            (canonical / "fleet.json").write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(gen.ManifestError, "duplicate JSON key"):
                gen.load_manifest(root)

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

    def test_skill_dependency_derives_claude_skill_access(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        self.assertNotIn("skill", manifest["agents"][1]["capabilities"])
        generated = gen.render(SPIKE_ROOT)
        claude = _text(
            generated, "generated/claude/agents/format-boundary-worker.md"
        ).split("---", 2)[1]
        self.assertIn("tools: Read, Grep, Glob, Skill", claude)

    def test_production_capabilities_project_runtime_tools(self) -> None:
        manifest = _minimal_manifest()
        agent = _terminal_agent()
        agent["capabilities"] = ["read", "search", "execute", "edit", "web"]
        manifest["agents"] = [agent]
        files = {"canonical/agents/probe-worker.md": "Exercise production tools.\n"}
        with tempfile.TemporaryDirectory(prefix="format-projection-") as temporary:
            root = Path(temporary)
            _write_fixture(root, manifest, files)
            generated = gen.render(root)
        copilot = _text(
            generated, "generated/copilot/agents/probe-worker.agent.md"
        ).split("---", 2)[1]
        claude = _text(
            generated, "generated/claude/agents/probe-worker.md"
        ).split("---", 2)[1]
        self.assertIn("tools: ['read', 'search', 'execute', 'edit', 'web']", copilot)
        self.assertIn(
            "tools: Read, Grep, Glob, Bash, Edit, Write, WebSearch, WebFetch",
            claude,
        )

    def test_pure_inventory_rejects_unexpected_skill_directory(self) -> None:
        issues = gen.compare_skill_inventory(
            {"format-boundary-probe": {
                "references": {"references/contract.md"},
                "assets": set(),
                "scripts": set(),
            }},
            {"format-boundary-probe", "shadow-skill"},
            {
                "format-boundary-probe": {
                    "references": {"references/contract.md"},
                    "assets": set(),
                    "scripts": set(),
                },
                "shadow-skill": {
                    "references": set(), "assets": set(), "scripts": set(),
                },
            },
        )
        self.assertEqual(
            ["unexpected runtime-visible skill directory: shadow-skill"], issues,
        )

    def test_pure_inventory_rejects_unexpected_reference(self) -> None:
        issues = gen.compare_skill_inventory(
            {"format-boundary-probe": {
                "references": {"references/contract.md"},
                "assets": set(),
                "scripts": set(),
            }},
            {"format-boundary-probe"},
            {"format-boundary-probe": {
                "references": {
                    "references/contract.md", "references/uninventoried.md",
                },
                "assets": set(),
                "scripts": set(),
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
