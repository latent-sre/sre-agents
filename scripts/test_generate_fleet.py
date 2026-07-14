#!/usr/bin/env python3
"""Contracts for the canonical fleet generator.

The real construction tree has five canonical agent definitions and derives
runtime visibility from the planned/active skill catalog and closed agent graph.
Temporary roots exercise later construction states without
publishing those fixtures through either runtime's discovery path.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import stat
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_fleet.py"
SPEC = importlib.util.spec_from_file_location("generate_fleet", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"cannot load {MODULE_PATH}")
generate_fleet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_fleet)


PINNED_SKILLS = [
    ("stack-profile", 10),
    ("root-cause", 11),
    ("runbook", 12),
    ("eng-ladder", 13),
    ("craft", 14),
    ("backend-craft", 15),
    ("frontend-craft", 16),
    ("ops-tooling", 17),
    ("pcf-ops", 18),
    ("pcf-deploy", 18),
    ("database-reliability", 19),
    ("ci-actions", 20),
    ("merge-gate", 21),
    ("release-gate", 21),
    ("production-change-gate", 22),
    ("incident-command", 23),
    ("postmortem", 23),
    ("service-onboarding", 32),
    ("agent-authoring", 25),
    ("agent-security", 25),
    ("obs-logs", 27),
    ("obs-metrics", 28),
    ("obs-traces", 29),
    ("obs-dashboards", 30),
    ("obs-alerting", 31),
    ("obs-pipeline", 32),
]

PINNED_SKILL_DEPENDENCIES = {
    "ops-tooling": ["eng-ladder"],
    "service-onboarding": [
        "production-change-gate",
        "obs-pipeline",
        "obs-dashboards",
        "obs-alerting",
        "ci-actions",
        "runbook",
    ],
}


def _plugin() -> dict:
    return {
        "name": "sre-agents",
        "displayName": "SRE Agents",
        "description": "SRE + SDE fleet — 5 agents, 26 skills, incident-to-code.",
        "version": "0.1.0",
        "author": {"name": "latent-sre", "url": "https://github.com/latent-sre"},
        "homepage": "https://github.com/latent-sre/sre-agents",
        "repository": "https://github.com/latent-sre/sre-agents",
        "license": "MIT",
        "keywords": [
            "agents", "skills", "sre", "copilot", "claude", "pcf", "observability"
        ],
    }


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "plugin": _plugin(),
        "models": {"copilot": [], "claude": None},
        "assembly_state": "boundary-only",
        "commands": [],
        "skills": [
            {"name": name, "state": "planned", "activate_task": task}
            for name, task in PINNED_SKILLS
        ],
        "skill_dependencies": copy.deepcopy(PINNED_SKILL_DEPENDENCIES),
        "agents": [],
    }


def _required_block(skills: list[str]) -> str:
    lines = ["## Required on-demand skills", "<!-- required-skills:start -->"]
    lines.extend(
        f"- `{name}` (Claude: `sre-agents:{name}`) — load when required."
        for name in skills
    )
    lines.extend(
        [
            "<!-- required-skills:end -->",
            "",
            "When required, load the runtime identity from the required-skills block.",
        ]
    )
    return "\n".join(lines)


def _dependency_block(skills: list[str]) -> str:
    lines = [
        "<!-- required-skill-dependencies:start -->",
        "## Required on-demand skill dependencies",
    ]
    lines.extend(
        f"- canonical `{name}`; Copilot `{name}`; Claude `sre-agents:{name}`"
        for name in skills
    )
    lines.extend(["<!-- required-skill-dependencies:end -->", ""])
    return "\n".join(lines)


class FleetRoot:
    def __init__(self, testcase: unittest.TestCase):
        # Python's TemporaryDirectory applies a Windows ACL/mode combination
        # that the managed workspace sandbox cannot descend into.  TEMP/TMP is
        # still the caller-selected isolated root; create the leaf with the
        # normal directory mode and remove it through the test cleanup.
        self.root = Path(tempfile.gettempdir()) / f"fleet-{uuid.uuid4().hex}"
        self.root.mkdir()
        testcase.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "canonical" / "agents").mkdir(parents=True)
        self.manifest = _manifest()
        self.flush()

    def flush(self) -> None:
        (self.root / "canonical" / "fleet.json").write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def skill_record(self, name: str) -> dict:
        return next(item for item in self.manifest["skills"] if item["name"] == name)

    def activate(
        self,
        name: str,
        *,
        references: dict[str, str | bytes] | None = None,
        assets: dict[str, str | bytes] | None = None,
        scripts: dict[str, str | bytes] | None = None,
        body_extra: str = "",
    ) -> None:
        references = references or {}
        assets = assets or {}
        scripts = scripts or {}
        record = self.skill_record(name)
        record.clear()
        record.update(
            {
                "name": name,
                "state": "active",
                "directory": f"skills/{name}",
                "references": [f"references/{path}" for path in references],
                "assets": [f"assets/{path}" for path in assets],
                "scripts": [f"scripts/{path}" for path in scripts],
            }
        )
        skill_root = self.root / "skills" / name
        skill_root.mkdir(parents=True, exist_ok=True)
        dependency_names = self.manifest["skill_dependencies"].get(name, [])
        body = (
            "---\n"
            f"name: {name}\n"
            f"description: Exercise {name}. Triggers: \"use {name}\", \"run {name}\".\n"
            "---\n\n"
            f"# {name}\n\n"
            f"{_dependency_block(dependency_names) if dependency_names else ''}"
            f"{body_extra}"
        )
        (skill_root / "SKILL.md").write_text(body, encoding="utf-8", newline="\n")
        for kind, values in (
            ("references", references), ("assets", assets), ("scripts", scripts)
        ):
            for relative, content in values.items():
                path = skill_root / kind / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    path.write_bytes(content)
                else:
                    path.write_text(content, encoding="utf-8", newline="\n")
        self.flush()

    def add_agent(
        self,
        name: str,
        *,
        required_skills: list[str] | None = None,
        capabilities: list[str] | None = None,
        delegates_to: list[str] | None = None,
        handoffs: list[str] | None = None,
        body_extra: str = "",
    ) -> dict:
        required_skills = required_skills or []
        delegates_to = delegates_to or []
        handoffs = handoffs or []
        agent = {
            "name": name,
            "description": f"Exercise {name}. Triggers: \"use {name}\", \"run {name}\".",
            "body": f"agents/{name}.md",
            "capabilities": capabilities or ["read"],
            "required_skills": required_skills,
            "delegates_to": delegates_to,
            "handoffs": [
                {
                    "agent": target,
                    "label": f"Hand to {target}",
                    "prompt": "Preserve [verified], [sourced], and [unverified] labels.",
                    "send": False,
                }
                for target in handoffs
            ],
        }
        self.manifest["agents"].append(agent)
        body = f"# {name}\n\n{body_extra}{_required_block(required_skills)}\n"
        (self.root / "canonical" / "agents" / f"{name}.md").write_text(
            body, encoding="utf-8", newline="\n"
        )
        self.flush()
        return agent

    def add_command(
        self,
        name: str = "adr",
        *,
        description: str | None = None,
        argument_mode: str = "required",
        argument_usage: str = "<decision> [probe: <token>]",
        invocation_mode: str = "manual",
        body: str | None = None,
    ) -> dict:
        self.manifest["assembly_state"] = "content-building"
        record = {
            "name": name,
            "source": f"commands/{name}.md",
            "description": description
            or (
                "Scaffold a self-contained Nygard Architecture Decision Record under "
                "docs/adr. Invoke manually with sde selected. Triggers: 'create an ADR', "
                "'scaffold an architecture decision record'."
            ),
            "argument_mode": argument_mode,
            "argument_usage": argument_usage,
            "invocation_mode": invocation_mode,
        }
        self.manifest["commands"].append(record)
        command_root = self.root / "canonical" / "commands"
        command_root.mkdir(parents=True, exist_ok=True)
        if body is None:
            body = (
                "# Fail-closed selected-agent preflight\n\n"
                "Continue only with sde selected and existing edit/write capability.\n\n"
                "Scaffold the decision: `{{arguments}}`.\n"
            )
        (command_root / f"{name}.md").write_text(
            body, encoding="utf-8", newline="\n"
        )
        self.flush()
        return record


class ProductionGeneratorContracts(unittest.TestCase):
    maxDiff = None

    def assertInvalid(self, fleet: FleetRoot, fragment: str) -> None:
        fleet.flush()
        with self.assertRaisesRegex(generate_fleet.ManifestError, fragment):
            generate_fleet.load_and_validate(fleet.root)

    def test_real_phase2_core_cohort_projects_exactly_three_agents(self) -> None:
        manifest, ready = generate_fleet.load_and_validate(ROOT)
        self.assertEqual(["reviewer", "sde", "scribe"], ready)
        outputs = generate_fleet.render(ROOT, manifest, ready)
        wrapper_paths = {
            path.as_posix()
            for path in outputs
            if path.as_posix().startswith("generated/") and "/agents/" in path.as_posix()
        }
        self.assertEqual(
            {
                "generated/copilot/agents/reviewer.agent.md",
                "generated/copilot/agents/sde.agent.md",
                "generated/copilot/agents/scribe.agent.md",
                "generated/claude/agents/reviewer.md",
                "generated/claude/agents/sde.md",
                "generated/claude/agents/scribe.md",
            },
            wrapper_paths,
        )
        self.assertEqual(
            "./generated/copilot/agents/",
            json.loads(outputs[Path("plugin.json")])["agents"],
        )
        self.assertEqual(
            [
                "./generated/claude/agents/reviewer.md",
                "./generated/claude/agents/sde.md",
                "./generated/claude/agents/scribe.md",
            ],
            json.loads(outputs[Path(".claude-plugin/plugin.json")])["agents"],
        )
        for name in ready:
            frontmatter = outputs[
                Path(f"generated/claude/agents/{name}.md")
            ].decode("utf-8").split("\n---\n", 1)[0]
            self.assertIn("Skill", frontmatter)
            self.assertNotIn("\nskills:", frontmatter)

    def test_catalog_is_exact_and_planned_active_shapes_do_not_cross(self) -> None:
        mutations = []
        fleet = FleetRoot(self)
        replaced = copy.deepcopy(fleet.manifest)
        replaced["skills"][0]["name"] = "replacement"
        mutations.append((replaced, "catalog"))
        duplicate = copy.deepcopy(fleet.manifest)
        duplicate["skills"][1]["name"] = duplicate["skills"][0]["name"]
        mutations.append((duplicate, "catalog"))
        wrong_task = copy.deepcopy(fleet.manifest)
        wrong_task["skills"][0]["activate_task"] = 999
        mutations.append((wrong_task, "catalog"))
        crossover = copy.deepcopy(fleet.manifest)
        crossover["skills"][0]["directory"] = "skills/stack-profile"
        mutations.append((crossover, "planned skill"))
        for manifest, fragment in mutations:
            with self.subTest(fragment=fragment):
                candidate = FleetRoot(self)
                candidate.manifest = manifest
                self.assertInvalid(candidate, fragment)

        planned_dir = FleetRoot(self)
        (planned_dir.root / "skills" / "stack-profile").mkdir(parents=True)
        self.assertInvalid(planned_dir, "planned skill directory")

    def test_active_skill_requires_exact_directory_and_bundle_inventory(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            references={"facts.md": "facts\n"},
            assets={"sample.txt": "sample\n"},
            scripts={"probe.py": "print('marker')\n"},
            body_extra=(
                "Read [facts](./references/facts.md), [sample](./assets/sample.txt), "
                "and [probe](./scripts/probe.py).\n"
            ),
        )
        manifest, ready = generate_fleet.load_and_validate(fleet.root)
        self.assertEqual([], ready)
        self.assertEqual("active", manifest["skills"][0]["state"])

        unexpected = fleet.root / "skills" / "stack-profile" / "references" / "extra.md"
        unexpected.write_text("extra\n", encoding="utf-8")
        self.assertInvalid(fleet, "unexpected")
        unexpected.unlink()
        (fleet.root / "skills" / "stack-profile" / "assets" / "sample.txt").unlink()
        self.assertInvalid(fleet, "missing")

    def test_skill_dependency_graph_is_pinned_and_active_owner_requires_active_targets(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["skill_dependencies"]["ops-tooling"] = []
        self.assertInvalid(fleet, "skill_dependencies")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate("ops-tooling")
        self.assertInvalid(fleet, "planned target")
        fleet.activate("eng-ladder")
        generate_fleet.load_and_validate(fleet.root)

        skill_body = fleet.root / "skills" / "ops-tooling" / "SKILL.md"
        skill_body.write_text(
            skill_body.read_text(encoding="utf-8").replace(
                "Claude `sre-agents:eng-ladder`", "Claude `eng-ladder`"
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalid(fleet, "dependency identities")

    def test_agent_required_skill_pairs_are_exact_and_unknown_names_fail(self) -> None:
        fleet = FleetRoot(self)
        fleet.add_agent("builder", required_skills=["stack-profile"])
        generate_fleet.load_and_validate(fleet.root)
        body = fleet.root / "canonical" / "agents" / "builder.md"
        body.write_text(
            body.read_text(encoding="utf-8").replace(
                "sre-agents:stack-profile", "stack-profile"
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalid(fleet, "required-skill identities")

        fleet = FleetRoot(self)
        fleet.add_agent("builder", required_skills=["unknown-skill"])
        self.assertInvalid(fleet, "unknown required skill")

        fleet = FleetRoot(self)
        fleet.add_agent("reviewer", required_skills=[])
        self.assertInvalid(fleet, "pinned matrix")

    def test_hidden_load_scanning_covers_every_utf8_bundle_file(self) -> None:
        fixtures = (
            ("references", "guide.md", "See root-cause before continuing.\n"),
            ("assets", "config.yaml", "# switch to root-cause\nvalue: safe\n"),
            ("scripts", "emit.py", 'print("Use this skill root-cause")\n'),
        )
        for kind, name, content in fixtures:
            with self.subTest(kind=kind):
                fleet = FleetRoot(self)
                fleet.manifest["assembly_state"] = "content-building"
                values = {name: content}
                kwargs = {kind: values}
                fleet.activate("stack-profile", **kwargs)
                self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            references={"binary.dat": b"\xff\xfe\x00"},
            body_extra="Read [binary guidance](./references/binary.dat) before acting.\n",
        )
        self.assertInvalid(fleet, "binary instruction guidance")

    def test_not_a_load_does_not_mask_a_later_hidden_instruction(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra=(
                "Ownership only—not a load: root-cause owns diagnosis. "
                "Then load root-cause.\n"
            ),
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra="Ownership only—not a load: load root-cause before continuing.\n",
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra=(
                "Ownership only—not a load: root-cause owns diagnosis, but load it "
                "anyway.\n"
            ),
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra=(
                "Ownership only—not a load: root-cause owns diagnosis, but load "
                "eng-ladder before continuing.\n"
            ),
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra=(
                "Ownership only—not a load: root-cause, but load root-cause "
                "before continuing.\n"
            ),
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra=(
                "Ownership only—not a load: root-cause owns diagnosis. "
                "Follow it anyway.\n"
            ),
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

    def test_target_before_action_coreference_is_a_hidden_instruction(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra="A root-cause guide may exist; follow it before continuing.\n",
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

    def test_wrapped_target_before_action_coreference_is_a_hidden_instruction(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra="A root-cause guide may exist.\nFollow it before continuing.\n",
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate(
            "stack-profile",
            body_extra="Follow the canonical\nroot-cause method before continuing.\n",
        )
        self.assertInvalid(fleet, "undeclared mandatory load")

    def test_greatest_closed_ready_set_recursively_eliminates_unready_targets(self) -> None:
        fleet = FleetRoot(self)
        fleet.add_agent("agent-a", delegates_to=["agent-b"])
        fleet.add_agent("agent-b", handoffs=["agent-c"])
        fleet.add_agent("agent-c", required_skills=["stack-profile"])
        _manifest_value, ready = generate_fleet.load_and_validate(fleet.root)
        self.assertEqual([], ready)

        fleet = FleetRoot(self)
        fleet.add_agent("agent-a", delegates_to=["agent-b"])
        fleet.add_agent("agent-b", delegates_to=["agent-a"])
        _manifest_value, ready = generate_fleet.load_and_validate(fleet.root)
        self.assertEqual(["agent-a", "agent-b"], ready)

    def test_handoff_only_and_mixed_edges_participate_in_readiness(self) -> None:
        fleet = FleetRoot(self)
        fleet.add_agent("agent-a", handoffs=["agent-b"])
        fleet.add_agent("agent-b", delegates_to=["agent-c"])
        fleet.add_agent("agent-c", required_skills=["stack-profile"])
        _manifest_value, ready = generate_fleet.load_and_validate(fleet.root)
        self.assertEqual([], ready)

    def test_runtime_projections_are_specific_and_claude_omits_sre_observer_execute(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.manifest["models"] = {"copilot": ["Copilot Model"], "claude": "sonnet"}
        needed = {
            "stack-profile",
            *generate_fleet.PINNED_AGENT_REQUIRED_SKILLS["sre"],
            *generate_fleet.PINNED_AGENT_REQUIRED_SKILLS["observer"],
        }
        for skill, _task in PINNED_SKILLS:
            if skill in needed:
                fleet.activate(skill)
        fleet.add_agent("terminal")
        fleet.add_agent(
            "builder",
            required_skills=["stack-profile"],
            capabilities=["read", "search", "execute", "edit", "web"],
            delegates_to=["terminal"],
            handoffs=["terminal"],
        )
        fleet.add_agent(
            "sre",
            required_skills=generate_fleet.PINNED_AGENT_REQUIRED_SKILLS["sre"],
            capabilities=["read", "execute"],
        )
        fleet.add_agent(
            "observer",
            required_skills=generate_fleet.PINNED_AGENT_REQUIRED_SKILLS["observer"],
            capabilities=["read", "execute"],
        )
        manifest, ready = generate_fleet.load_and_validate(fleet.root)
        outputs = generate_fleet.render(fleet.root, manifest, ready)
        copilot_builder = outputs[
            Path("generated/copilot/agents/builder.agent.md")
        ].decode()
        claude_builder = outputs[Path("generated/claude/agents/builder.md")].decode()
        self.assertIn(
            "tools: ['read', 'search', 'execute', 'edit', 'web', 'agent']",
            copilot_builder,
        )
        self.assertIn("agents: ['terminal']", copilot_builder)
        self.assertIn("handoffs:", copilot_builder)
        self.assertIn("model: ['Copilot Model']", copilot_builder)
        self.assertIn("Bash", claude_builder)
        self.assertIn("Agent(terminal)", claude_builder)
        self.assertNotIn("handoffs:", claude_builder.split("\n---\n", 1)[0])
        self.assertIn('model: "sonnet"', claude_builder)
        for name in ("sre", "observer"):
            self.assertIn(
                "'execute'", outputs[Path(f"generated/copilot/agents/{name}.agent.md")].decode()
            )
            self.assertNotIn(
                "Bash", outputs[Path(f"generated/claude/agents/{name}.md")].decode()
            )
        claude_frontmatter = claude_builder.split("\n---\n", 1)[0]
        self.assertNotIn("\nskills:", claude_frontmatter)
        self.assertIn("Skill", claude_frontmatter)

    def test_boundary_only_rejects_active_skills_and_all_command_artifacts(self) -> None:
        fleet = FleetRoot(self)
        fleet.activate("stack-profile")
        self.assertInvalid(fleet, "boundary-only")

        fleet = FleetRoot(self)
        fleet.manifest["commands"] = [{"name": "not-accepted"}]
        self.assertInvalid(fleet, "format boundary not accepted")

        fleet = FleetRoot(self)
        command_root = fleet.root / "canonical" / "commands"
        command_root.mkdir()
        (command_root / "orphan.md").write_text("orphan\n", encoding="utf-8")
        self.assertInvalid(fleet, "command body")

        fleet = FleetRoot(self)
        default_commands = fleet.root / "commands"
        default_commands.mkdir()
        (default_commands / "orphan.md").write_text("orphan\n", encoding="utf-8")
        self.assertInvalid(fleet, "default-discovery")

        fleet = FleetRoot(self)
        (fleet.root / "SKILL.md").write_text("orphan\n", encoding="utf-8")
        self.assertInvalid(fleet, "root SKILL.md")

    def test_content_building_commands_require_exact_schema_and_source_inventory(self) -> None:
        fleet = FleetRoot(self)
        fleet.add_command()
        manifest, _ready = generate_fleet.load_and_validate(fleet.root)
        self.assertEqual("adr", manifest["commands"][0]["name"])

        mutations = (
            ("unknown key", lambda record: record.update({"extra": True})),
            ("missing key", lambda record: record.pop("description")),
            ("source", lambda record: record.update({"source": "commands/wrong.md"})),
            ("argument_mode", lambda record: record.update({"argument_mode": "optional"})),
            ("argument_usage", lambda record: record.update({"argument_usage": ""})),
            ("invocation_mode", lambda record: record.update({"invocation_mode": "auto"})),
        )
        for fragment, mutate in mutations:
            with self.subTest(fragment=fragment):
                broken = FleetRoot(self)
                record = broken.add_command()
                mutate(record)
                self.assertInvalid(broken, fragment)

        no_argument = FleetRoot(self)
        no_argument.add_command(
            name="status",
            argument_mode="none",
            argument_usage="",
            body="# Status\n",
        )
        generate_fleet.load_and_validate(no_argument.root)

        for body, fragment in (
            ("# Missing sentinel\n", "sentinel"),
            ("{{arguments}} then {{arguments}}\n", "sentinel"),
            ("{{arguments}} plus $ARGUMENTS\n", "runtime argument expression"),
            (
                "{{arguments}} plus ${input:arguments}\n",
                "runtime argument expression",
            ),
            ("{{arguments}} plus ${input:other}\n", "runtime argument expression"),
            ("{{arguments}} plus ${CLAUDE_SKILL_DIR}\n", "runtime argument expression"),
            ("{{arguments}} plus $1\n", "runtime argument expression"),
            ("{{arguments}} plus $ARGUMENTS[0]\n", "runtime argument expression"),
            ("{{arguments}}. Load `stack-profile` now.\n", "mandatory load"),
        ):
            with self.subTest(body=body):
                broken = FleetRoot(self)
                broken.add_command(body=body)
                self.assertInvalid(broken, fragment)

        orphan = FleetRoot(self)
        orphan.manifest["assembly_state"] = "content-building"
        command_root = orphan.root / "canonical" / "commands"
        command_root.mkdir()
        (command_root / "orphan.md").write_text("orphan\n", encoding="utf-8")
        self.assertInvalid(orphan, "inventory")

    def test_command_sources_reject_link_like_and_hardlinked_bodies(self) -> None:
        linked = FleetRoot(self)
        linked.add_command()
        command_path = linked.root / "canonical" / "commands" / "adr.md"
        original = generate_fleet._is_link_or_junction
        with mock.patch.object(
            generate_fleet,
            "_is_link_or_junction",
            side_effect=lambda path: Path(path) == command_path or original(Path(path)),
        ):
            self.assertInvalid(linked, "link or junction")

        if not hasattr(os, "link"):
            return
        hardlinked = FleetRoot(self)
        hardlinked.add_command()
        command_path = hardlinked.root / "canonical" / "commands" / "adr.md"
        other = hardlinked.root / "hardlink-source.md"
        other.write_text("{{arguments}}\n", encoding="utf-8", newline="\n")
        command_path.unlink()
        try:
            os.link(other, command_path)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        self.assertInvalid(hardlinked, "hardlink")

    def test_command_projections_map_metadata_without_widening_and_preserve_body(self) -> None:
        fleet = FleetRoot(self)
        command = fleet.add_command()
        manifest, ready = generate_fleet.load_and_validate(fleet.root)
        outputs = generate_fleet.render(fleet.root, manifest, ready)
        paths = {
            Path("generated/copilot/commands/adr.md"),
            Path("generated/copilot/prompts/adr.prompt.md"),
            Path("generated/claude/commands/adr.md"),
        }
        self.assertTrue(paths <= set(outputs))
        self.assertEqual(
            "./generated/copilot/commands/",
            json.loads(outputs[Path("plugin.json")])["commands"],
        )
        self.assertEqual(
            ["./generated/claude/commands/adr.md"],
            json.loads(outputs[Path(".claude-plugin/plugin.json")])["commands"],
        )

        canonical = (fleet.root / "canonical" / "commands" / "adr.md").read_text(
            encoding="utf-8"
        )
        expected = {
            Path("generated/copilot/commands/adr.md"): ("$ARGUMENTS", True, False),
            Path("generated/copilot/prompts/adr.prompt.md"): (
                "${input:arguments}", False, True
            ),
            Path("generated/claude/commands/adr.md"): ("$ARGUMENTS", True, False),
        }
        for path, (argument_expression, explicit_manual, has_name) in expected.items():
            with self.subTest(path=path.as_posix()):
                text = outputs[path].decode("utf-8")
                self.assertTrue(text.startswith("---\n"))
                frontmatter, body = text[4:].split("\n---\n", 1)
                self.assertIn(
                    f"description: {json.dumps(command['description'], ensure_ascii=False)}",
                    frontmatter,
                )
                self.assertIn(
                    f"argument-hint: {json.dumps(command['argument_usage'])}",
                    frontmatter,
                )
                self.assertEqual(explicit_manual, "disable-model-invocation: true" in frontmatter)
                self.assertEqual(has_name, "\nname: adr\n" in f"\n{frontmatter}\n")
                for forbidden in ("\nagent:", "\ntools:", "\nallowed-tools:"):
                    self.assertNotIn(forbidden, f"\n{frontmatter}")
                self.assertEqual(1, body.count(argument_expression))
                self.assertEqual(
                    canonical,
                    body.replace(argument_expression, "{{arguments}}"),
                )

    def test_command_write_removes_all_three_views_when_record_is_removed(self) -> None:
        fleet = FleetRoot(self)
        fleet.add_command()
        generate_fleet.write(fleet.root)
        projected = (
            fleet.root / "generated" / "copilot" / "commands" / "adr.md",
            fleet.root / "generated" / "copilot" / "prompts" / "adr.prompt.md",
            fleet.root / "generated" / "claude" / "commands" / "adr.md",
        )
        self.assertTrue(all(path.is_file() for path in projected))

        fleet.manifest["commands"] = []
        (fleet.root / "canonical" / "commands" / "adr.md").unlink()
        fleet.flush()
        self.assertTrue(generate_fleet.check(fleet.root))
        generate_fleet.write(fleet.root)
        self.assertTrue(all(not path.exists() for path in projected))
        self.assertEqual([], generate_fleet.check(fleet.root))

    def test_content_complete_flag_requires_exact_complete_ready_fleet(self) -> None:
        fleet = FleetRoot(self)
        with self.assertRaisesRegex(generate_fleet.ManifestError, "content-complete"):
            generate_fleet.load_and_validate(fleet.root, require_content_complete=True)

        fleet.manifest["assembly_state"] = "content-complete"
        self.assertInvalid(fleet, "all 26 skills")

        complete = FleetRoot(self)
        complete.manifest["assembly_state"] = "content-complete"
        for skill, _task in PINNED_SKILLS:
            complete.activate(skill)
        for agent in generate_fleet.CONTENT_COMPLETE_AGENTS:
            complete.add_agent(
                agent,
                required_skills=generate_fleet.PINNED_AGENT_REQUIRED_SKILLS[agent],
            )
        manifest, ready = generate_fleet.load_and_validate(
            complete.root, require_content_complete=True
        )
        self.assertEqual(list(generate_fleet.CONTENT_COMPLETE_AGENTS), ready)
        outputs = generate_fleet.render(complete.root, manifest, ready)
        self.assertEqual(
            5,
            sum(
                path.as_posix().startswith("generated/copilot/agents/")
                for path in outputs
            ),
        )

    def test_write_check_and_ready_to_unready_cleanup_converge(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate("stack-profile")
        fleet.add_agent("builder", required_skills=["stack-profile"])
        fleet.flush()
        generate_fleet.write(fleet.root)
        self.assertEqual([], generate_fleet.check(fleet.root))
        copilot = fleet.root / "generated" / "copilot" / "agents" / "builder.agent.md"
        claude = fleet.root / "generated" / "claude" / "agents" / "builder.md"
        self.assertTrue(copilot.is_file())
        self.assertTrue(claude.is_file())

        record = fleet.skill_record("stack-profile")
        record.clear()
        record.update({"name": "stack-profile", "state": "planned", "activate_task": 10})
        for path in sorted(
            (fleet.root / "skills" / "stack-profile").rglob("*"), reverse=True
        ):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        (fleet.root / "skills" / "stack-profile").rmdir()
        fleet.flush()
        self.assertTrue(generate_fleet.check(fleet.root))
        generate_fleet.write(fleet.root)
        self.assertFalse(copilot.exists())
        self.assertFalse(claude.exists())
        self.assertEqual([], generate_fleet.check(fleet.root))

    def test_check_detects_hand_edits_and_write_removes_any_suffix_stale_file(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        plugin = fleet.root / "plugin.json"
        plugin.write_text("{}\n", encoding="utf-8")
        self.assertTrue(any("plugin.json" in item for item in generate_fleet.check(fleet.root)))

        stale = fleet.root / "generated" / "copilot" / "agents" / "nested" / "stale.bin"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"stale")
        generate_fleet.write(fleet.root)
        self.assertFalse(stale.exists())
        self.assertEqual([], generate_fleet.check(fleet.root))

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_write_refuses_hardlinked_generated_targets(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        target = fleet.root / "plugin.json"
        other = fleet.root / "plugin-hardlink.json"
        try:
            target.unlink()
            other.write_text("unsafe\n", encoding="utf-8")
            os.link(other, target)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        with self.assertRaisesRegex(generate_fleet.ManifestError, "hardlink"):
            generate_fleet.write(fleet.root)

    def test_windows_reparse_attribute_is_link_like(self) -> None:
        metadata = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
        )
        with mock.patch.object(Path, "lstat", return_value=metadata):
            self.assertTrue(generate_fleet._is_link_or_junction(Path("reparse-probe")))

    def test_link_like_canonical_manifest_and_bundle_file_are_rejected(self) -> None:
        fleet = FleetRoot(self)
        manifest_path = fleet.root / "canonical" / "fleet.json"
        original = generate_fleet._is_link_or_junction
        with mock.patch.object(
            generate_fleet,
            "_is_link_or_junction",
            side_effect=lambda path: Path(path) == manifest_path or original(Path(path)),
        ):
            self.assertInvalid(fleet, "link or junction")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate("stack-profile", references={"facts.md": "facts\n"})
        bundle_path = fleet.root / "skills" / "stack-profile" / "references" / "facts.md"
        with mock.patch.object(
            generate_fleet,
            "_is_link_or_junction",
            side_effect=lambda path: Path(path) == bundle_path or original(Path(path)),
        ):
            self.assertInvalid(fleet, "link or junction")

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_hardlinked_canonical_manifest_and_bundle_file_are_rejected(self) -> None:
        fleet = FleetRoot(self)
        manifest = fleet.root / "canonical" / "fleet.json"
        manifest_peer = fleet.root / "manifest-peer.json"
        try:
            os.link(manifest, manifest_peer)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        self.assertInvalid(fleet, "manifest cannot be a hardlink")

        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate("stack-profile", references={"facts.md": "facts\n"})
        bundle = fleet.root / "skills" / "stack-profile" / "references" / "facts.md"
        bundle_peer = fleet.root / "bundle-peer.md"
        try:
            os.link(bundle, bundle_peer)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        self.assertInvalid(fleet, "inventoried file is a hardlink")

    def test_escaping_bundle_path_and_link_like_generated_tree_are_rejected(self) -> None:
        fleet = FleetRoot(self)
        fleet.manifest["assembly_state"] = "content-building"
        fleet.activate("stack-profile", references={"facts.md": "facts\n"})
        fleet.skill_record("stack-profile")["references"] = ["references/../outside.md"]
        self.assertInvalid(fleet, "invalid POSIX-relative path")

        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        generated_tree = fleet.root / "generated" / "copilot" / "agents"
        original = generate_fleet._is_link_or_junction
        with mock.patch.object(
            generate_fleet,
            "_is_link_or_junction",
            side_effect=lambda path: Path(path) == generated_tree or original(Path(path)),
        ):
            with self.assertRaisesRegex(generate_fleet.ManifestError, "link or junction"):
                generate_fleet.check(fleet.root)
            with self.assertRaisesRegex(generate_fleet.ManifestError, "link or junction"):
                generate_fleet.write(fleet.root)


if __name__ == "__main__":
    unittest.main()
