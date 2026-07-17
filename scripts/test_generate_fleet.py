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
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
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

GATE_A_MODULE_PATH = ROOT / "scripts" / "gate_a.py"
GATE_A_SPEC = importlib.util.spec_from_file_location("gate_a", GATE_A_MODULE_PATH)
if GATE_A_SPEC is None or GATE_A_SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"cannot load {GATE_A_MODULE_PATH}")
gate_a = importlib.util.module_from_spec(GATE_A_SPEC)
GATE_A_SPEC.loader.exec_module(gate_a)


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

TASK32_DEPENDENCIES = PINNED_SKILL_DEPENDENCIES["service-onboarding"]
TASK32_INVENTORIES = {
    "obs-pipeline": {
        "references": ["references/alloy.md", "references/otel-sdk.md"],
        "assets": [],
        "scripts": [],
    },
    "service-onboarding": {
        "references": [],
        "assets": [],
        "scripts": [],
    },
}
TASK32_SERVICE_DESCRIPTION = (
    "Onboard a service onto the platform and the observability stack — or audit an existing one "
    "against the standard. Invoke it explicitly by name. Triggers: 'onboard this service', "
    "'bring X up to standard', 'audit this service'. Works the checklist in order; audit mode "
    "reports evidence-cited findings and the top three fixes."
)
TASK32_SERVICE_INVOCATION_COMMENT = (
    "# Side-effect-shaped: invoke explicitly by name; never auto-load."
)
TASK32_SERVICE_CHASSIS = """Work through every step in order; when one is skipped, say so explicitly and why — silence reads
as "done." This checklist grants no permission of its own — a step being on the list is not
approval to run it. Before any prod-facing step, load its gate from the dependency block below
(canonical `production-change-gate`) and re-enter it.

<!-- required-skill-dependencies:start -->
## Required on-demand skill dependencies
- canonical `production-change-gate`
- canonical `obs-pipeline`
- canonical `obs-dashboards`
- canonical `obs-alerting`
- canonical `ci-actions`
- canonical `runbook`
<!-- required-skill-dependencies:end -->

Before each dependent checklist step, load that row's skill from this block; the canonical names are
executable load requirements, not decorative cross-references.

1. **Manifest & health** — version-controlled `manifest.yml`; http health-check endpoint; ≥2 instances.
2. **Instrument** — OTel SDK wired (metrics + traces + structured logs); RED metrics named per
   convention; cardinality reviewed. [read canonical `obs-pipeline` before this step]
3. **Ship telemetry** — Alloy/collector config routes logs → Loki (and Splunk where required),
   metrics → Mimir, traces → Tempo. Prove arrival with one query per signal, quoted.
4. **Dashboard** — the service page in Grafana: top-level health → drill-down (load the owner:
   canonical `obs-dashboards`).
5. **Alerts** — burn-rate alert on the SLI + one saturation alert; each linked to a runbook
   (load the owner: canonical `obs-alerting`). No runbook, no alert.
6. **SLO** — SLI formula + target + window recorded where the team keeps them.
7. **CI/CD** — build + deploy via Actions (canonical `ci-actions`); promotion gates on.
8. **Runbook** — check/restart/recover doc exists (canonical `runbook`); on-call knows where it is.

**Audit mode** (bringing an existing service up to standard): run the checks below and report like
a code review of the service — severity-ranked, evidence-cited, **no finding without the command
output that proves it**. End with the top three fixes — not a list of thirty.

Checks (run what applies; list what you couldn't run and why): route/auth exposure · app hygiene
(crash counts, instance flapping, memory headroom via `cf app`) · certificate expiry ·
service-backup existence (**a backup that has never been restored is a hope, not a backup**) ·
monitoring gaps (steps 3–7 above, absent) · manifest drift vs running config · capacity headroom ·
platform-deprecation notices.

Output: `[P0]`–`[P3]` findings, each with the evidence (command + output) and the one-line fix.
**P0 = exposed without auth, or stateful and unbacked-up.**
"""


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
    lines.extend(f"- canonical `{name}`" for name in skills)
    lines.extend(["<!-- required-skill-dependencies:end -->", ""])
    return "\n".join(lines)


def _skill_parts(text: str) -> tuple[dict[str, str], list[str], str]:
    """Parse the small frontmatter subset needed by production content contracts."""
    if not text.startswith("---\n"):
        raise AssertionError("skill frontmatter is missing")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError("skill frontmatter is not closed")
    lines = text[4:end].splitlines()
    values: dict[str, str] = {}
    comments: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            comments.append(line)
            index += 1
            continue
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9-]*):(?:[ \t]*(.*))?", line)
        if match is None:
            index += 1
            continue
        key, raw = match.group(1), (match.group(2) or "")
        if raw in {">", ">-", "|", "|-"}:
            chunks: list[str] = []
            index += 1
            while index < len(lines) and lines[index].startswith((" ", "\t")):
                chunks.append(lines[index].strip())
                index += 1
            values[key] = " ".join(chunks)
            continue
        values[key] = raw.strip()
        index += 1
    return values, comments, text[end + len("\n---\n") :]


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
                "directory": f".github/skills/{name}",
                "references": [f"references/{path}" for path in references],
                "assets": [f"assets/{path}" for path in assets],
                "scripts": [f"scripts/{path}" for path in scripts],
            }
        )
        skill_root = self.root / ".github" / "skills" / name
        skill_root.mkdir(parents=True, exist_ok=True)
        dependency_names = self.manifest["skill_dependencies"].get(name, [])
        manual_only = (
            "disable-model-invocation: true\n"
            if name in generate_fleet.MANUAL_ONLY_SKILLS
            else ""
        )
        body = (
            "---\n"
            f"name: {name}\n"
            f"description: Exercise {name}. Triggers: \"use {name}\", \"run {name}\".\n"
            f"{manual_only}"
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

    def test_gate_a_requires_exact_content_complete_step_once(self) -> None:
        expected = (
            "Fleet content complete",
            ["scripts/generate_fleet.py", "--require-content-complete"],
            None,
        )
        self.assertEqual(1, gate_a.STEPS.count(expected))

    def test_cli_requires_a_mode_when_no_completion_assertion_is_requested(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                generate_fleet.main([])
        self.assertEqual(2, raised.exception.code)

    def test_cli_preserves_explicit_write_and_check_modes(self) -> None:
        with mock.patch.object(generate_fleet, "write") as write:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, generate_fleet.main(["--write"]))
        write.assert_called_once_with(ROOT, require_content_complete=False)

        with mock.patch.object(generate_fleet, "check", return_value=[]) as check:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, generate_fleet.main(["--check"]))
        check.assert_called_once_with(ROOT, require_content_complete=False)

    def test_cli_completion_assertion_standalone_performs_a_check(self) -> None:
        with mock.patch.object(generate_fleet, "check", return_value=[]) as check:
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                try:
                    result = generate_fleet.main(["--require-content-complete"])
                except SystemExit as exc:
                    self.fail(
                        "standalone --require-content-complete exited with "
                        f"status {exc.code} instead of checking the fleet"
                    )
        self.assertEqual(0, result)
        check.assert_called_once_with(ROOT, require_content_complete=True)

    def test_task32_service_onboarding_has_exact_dependency_identities_and_chassis(self) -> None:
        path = ROOT / ".github" / "skills" / "service-onboarding" / "SKILL.md"
        self.assertTrue(path.is_file(), "Task 32 service-onboarding source is missing")
        text = path.read_text(encoding="utf-8")
        frontmatter, comments, body = _skill_parts(text)
        normalized = " ".join(text.split())

        self.assertEqual("service-onboarding", frontmatter["name"])
        self.assertEqual(TASK32_SERVICE_DESCRIPTION, frontmatter["description"])
        self.assertEqual("true", frontmatter["disable-model-invocation"])
        self.assertEqual([TASK32_SERVICE_INVOCATION_COMMENT], comments)

        chassis_at = body.index("Work through every step in order;")
        evidence_prologue = body[:chassis_at]
        self.assertEqual(TASK32_SERVICE_CHASSIS, body[chassis_at:])
        self.assertTrue(
            all(not line or line.startswith(">") for line in evidence_prologue.splitlines()),
            "only the repository evidence prologue may precede the plan-supplied chassis",
        )
        evidence_normalized = " ".join(
            line[2:] if line.startswith("> ") else line
            for line in evidence_prologue.splitlines()
        )
        evidence_normalized = " ".join(evidence_normalized.split())
        for required in (
            "sanitized commands",
            "minimal redacted output excerpt",
            "identify every redaction",
            "[REDACTED:token]",
            "access-controlled source link",
            "smallest excerpt needed",
            "Never run or request credential-bearing reads",
            "`cf env`",
            "`cf service-key`",
            "`CF_TRACE`",
            "credential endpoints",
        ):
            with self.subTest(evidence_boundary=required):
                self.assertIn(required, evidence_normalized)

        self.assertEqual(
            ["## Required on-demand skill dependencies"],
            re.findall(r"^#{1,6} .+$", body, re.MULTILINE),
        )
        self.assertEqual(1, text.count("<!-- required-skill-dependencies:start -->"))
        self.assertEqual(1, text.count("<!-- required-skill-dependencies:end -->"))
        block_start = body.index("<!-- required-skill-dependencies:start -->")
        block_end = body.index("<!-- required-skill-dependencies:end -->") + len(
            "<!-- required-skill-dependencies:end -->"
        )
        self.assertEqual(_dependency_block(TASK32_DEPENDENCIES).rstrip(), body[block_start:block_end])
        self.assertIn("**no finding without the command output that proves it**", normalized)
        self.assertIn("top three fixes — not a list of thirty", normalized)
        self.assertIn("**P0 = exposed without auth, or stateful and unbacked-up.**", text)

    def test_real_content_complete_dependency_slice_projects_all_five_agents(self) -> None:
        manifest, ready = generate_fleet.load_and_validate(ROOT)
        self.assertEqual("content-complete", manifest["assembly_state"])
        self.assertEqual(26, sum(skill["state"] == "active" for skill in manifest["skills"]))
        self.assertEqual(0, sum(skill["state"] == "planned" for skill in manifest["skills"]))
        self.assertEqual(7, sum(len(row) for row in manifest["skill_dependencies"].values()))
        self.assertEqual(28, sum(len(agent["required_skills"]) for agent in manifest["agents"]))
        for name, inventory in TASK32_INVENTORIES.items():
            record = next(skill for skill in manifest["skills"] if skill["name"] == name)
            self.assertEqual("active", record["state"])
            self.assertEqual(f".github/skills/{name}", record["directory"])
            for kind, expected in inventory.items():
                self.assertEqual(expected, record[kind])
        self.assertEqual(list(generate_fleet.CONTENT_COMPLETE_AGENTS), ready)
        outputs = generate_fleet.render(ROOT, manifest, ready)
        wrapper_paths = {
            path.as_posix()
            for path in outputs
            if "/agents/" in path.as_posix()
        }
        self.assertEqual(
            {
                ".github/agents/reviewer.agent.md",
                ".github/agents/sde.agent.md",
                ".github/agents/sre.agent.md",
                ".github/agents/observer.agent.md",
                ".github/agents/scribe.agent.md",
                "generated/claude/agents/reviewer.md",
                "generated/claude/agents/sde.md",
                "generated/claude/agents/sre.md",
                "generated/claude/agents/observer.md",
                "generated/claude/agents/scribe.md",
            },
            wrapper_paths,
        )
        self.assertEqual(
            "./.github/agents/",
            json.loads(outputs[Path("plugin.json")])["agents"],
        )
        self.assertEqual(
            [
                "./generated/claude/agents/reviewer.md",
                "./generated/claude/agents/sde.md",
                "./generated/claude/agents/sre.md",
                "./generated/claude/agents/observer.md",
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

        for runtime_dir, pattern in (
            (ROOT / ".github" / "agents", "*.agent.md"),
            (ROOT / "generated" / "claude" / "agents", "*.md"),
        ):
            actual = sorted(path.name for path in runtime_dir.glob(pattern))
            expected = sorted(
                f"{name}.agent.md" if pattern == "*.agent.md" else f"{name}.md"
                for name in ready
            )
            self.assertEqual(expected, actual)

    def test_projected_agent_bodies_carry_only_their_runtime_identity(self) -> None:
        manifest, ready = generate_fleet.load_and_validate(ROOT)
        outputs = generate_fleet.render(ROOT, manifest, ready)
        by_name = {agent["name"]: agent for agent in manifest["agents"]}
        for name in ready:
            copilot = outputs[Path(f".github/agents/{name}.agent.md")].decode("utf-8")
            claude = outputs[Path(f"generated/claude/agents/{name}.md")].decode("utf-8")
            _fm, _, copilot_body = copilot.partition("\n---\n")
            _fm2, _, claude_body = claude.partition("\n---\n")
            # The Copilot file never names Claude's runtime; the dual-identity clause is gone.
            self.assertNotIn("sre-agents:", copilot_body)
            self.assertNotIn("(Claude:", copilot_body)
            self.assertNotIn("Copilot uses `<skill-name>`", copilot_body)
            for skill in by_name[name]["required_skills"]:
                self.assertIn(f"- `{skill}` —", copilot_body)
                self.assertIn(f"- `sre-agents:{skill}` —", claude_body)
            # The Claude file uses only the namespaced form -- no bare "(Claude:" pairing survives.
            self.assertNotIn("(Claude:", claude_body)
            self.assertNotIn("Copilot uses `<skill-name>`", claude_body)

    def test_copilot_selector_manifest_is_an_exact_copilot_alias(self) -> None:
        manifest, ready = generate_fleet.load_and_validate(ROOT)
        outputs = generate_fleet.render(ROOT, manifest, ready)

        root_manifest = outputs[Path("plugin.json")]
        selector_manifest = outputs[Path(".plugin/plugin.json")]
        self.assertEqual(root_manifest, selector_manifest)
        self.assertEqual(
            {
                "agents": "./.github/agents/",
                "skills": "./.github/skills/",
                "commands": "./generated/copilot/commands/",
            },
            {
                key: json.loads(selector_manifest)[key]
                for key in ("agents", "skills", "commands")
            },
        )
        self.assertNotIn("generated/claude", selector_manifest.decode("utf-8"))

    def test_check_rejects_missing_copilot_selector_manifest(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        selector = fleet.root / ".plugin" / "plugin.json"
        self.assertTrue(selector.is_file())

        selector.unlink()
        self.assertIn(
            "missing generated output: .plugin/plugin.json",
            generate_fleet.check(fleet.root),
        )

    def test_check_rejects_stale_copilot_selector_manifest(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        selector = fleet.root / ".plugin" / "plugin.json"
        selector.parent.mkdir(parents=True, exist_ok=True)
        selector.write_text("{}\n", encoding="utf-8", newline="\n")

        self.assertIn(
            "stale generated output: .plugin/plugin.json",
            generate_fleet.check(fleet.root),
        )

    def test_copilot_selector_directory_rejects_and_cleans_rogue_files(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        rogue = fleet.root / ".plugin" / "nested" / "rogue.agent.md"
        rogue.parent.mkdir(parents=True, exist_ok=True)
        rogue.write_text("rogue\n", encoding="utf-8", newline="\n")

        self.assertIn(
            "unexpected generated output: .plugin/nested/rogue.agent.md",
            generate_fleet.check(fleet.root),
        )
        generate_fleet.write(fleet.root)
        self.assertFalse(rogue.exists())
        self.assertEqual([], generate_fleet.check(fleet.root))

    def test_check_rejects_unexpected_empty_copilot_selector_directory(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        unexpected = fleet.root / ".plugin" / "nested"
        unexpected.mkdir()

        self.assertIn(
            "unexpected generated output: .plugin/nested",
            generate_fleet.check(fleet.root),
        )
        generate_fleet.write(fleet.root)
        self.assertFalse(unexpected.exists())
        self.assertTrue((fleet.root / ".plugin").is_dir())
        self.assertEqual([], generate_fleet.check(fleet.root))

    def test_check_preserves_directories_implied_by_generated_files(self) -> None:
        fleet = FleetRoot(self)
        content = b"generated\n"
        generated = fleet.root / ".plugin" / "nested" / "plugin.json"
        generated.parent.mkdir(parents=True)
        generated.write_bytes(content)

        with mock.patch.object(
            generate_fleet,
            "render",
            return_value={Path(".plugin/nested/plugin.json"): content},
        ):
            self.assertEqual([], generate_fleet.check(fleet.root))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "filesystem FIFOs unavailable")
    def test_check_rejects_special_copilot_selector_entry(self) -> None:
        fleet = FleetRoot(self)
        generate_fleet.write(fleet.root)
        special = fleet.root / ".plugin" / "unexpected.pipe"
        try:
            os.mkfifo(special)
        except OSError as exc:
            self.skipTest(f"filesystem FIFO creation unavailable: {exc}")

        with self.assertRaisesRegex(
            generate_fleet.ManifestError, "unsupported filesystem entry"
        ):
            generate_fleet.check(fleet.root)

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_write_refuses_hardlinked_copilot_selector_manifest(self) -> None:
        fleet = FleetRoot(self)
        selector = fleet.root / ".plugin" / "plugin.json"
        selector.parent.mkdir(parents=True)
        source = fleet.root / "selector-hardlink-source.json"
        source.write_text("unsafe\n", encoding="utf-8", newline="\n")
        try:
            os.link(source, selector)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")

        with self.assertRaisesRegex(generate_fleet.ManifestError, "hardlink"):
            generate_fleet.write(fleet.root)

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
        crossover["skills"][0]["directory"] = ".github/skills/stack-profile"
        mutations.append((crossover, "planned skill"))
        for manifest, fragment in mutations:
            with self.subTest(fragment=fragment):
                candidate = FleetRoot(self)
                candidate.manifest = manifest
                self.assertInvalid(candidate, fragment)

        planned_dir = FleetRoot(self)
        (planned_dir.root / ".github" / "skills" / "stack-profile").mkdir(parents=True)
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

        unexpected = fleet.root / ".github" / "skills" / "stack-profile" / "references" / "extra.md"
        unexpected.write_text("extra\n", encoding="utf-8")
        self.assertInvalid(fleet, "unexpected")
        unexpected.unlink()
        (fleet.root / ".github" / "skills" / "stack-profile" / "assets" / "sample.txt").unlink()
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

        skill_body = fleet.root / ".github" / "skills" / "ops-tooling" / "SKILL.md"
        skill_body.write_text(
            skill_body.read_text(encoding="utf-8").replace(
                "- canonical `eng-ladder`", "- canonical `craft`"
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

    def test_hidden_load_scope_does_not_cross_into_a_parenthetical_owner_load(self) -> None:
        def onboarding_fixture(body_extra: str) -> FleetRoot:
            candidate = FleetRoot(self)
            candidate.manifest["assembly_state"] = "content-building"
            for target in TASK32_DEPENDENCIES:
                candidate.activate(target)
            candidate.activate("service-onboarding", body_extra=body_extra)
            return candidate

        canonical_owner = "load the owner: canonical `obs-alerting`"
        fleet = onboarding_fixture(
            "5. **Alerts** — each alert links to a runbook "
            f"({canonical_owner}). No runbook, no alert.\n"
        )
        generate_fleet.load_and_validate(fleet.root)

        hidden_cases = (
            "Keep the runbook (load this method) before continuing.\n",
            f"Keep the runbook ({canonical_owner}; follow it) before continuing.\n",
            f"Keep the runbook ({canonical_owner}), then follow it before continuing.\n",
            f"Keep the runbook, then follow it ({canonical_owner}).\n",
        )
        for body_extra in hidden_cases:
            with self.subTest(hidden_parenthetical=body_extra):
                self.assertInvalid(
                    onboarding_fixture(body_extra),
                    "mandatory load lacks the canonical skill identity",
                )

    def test_manual_only_skill_control_must_be_true_and_inside_frontmatter(self) -> None:
        moved = FleetRoot(self)
        moved.manifest["assembly_state"] = "content-building"
        for target in TASK32_DEPENDENCIES:
            moved.activate(target)
        moved.activate("service-onboarding")
        path = moved.root / ".github" / "skills" / "service-onboarding" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                "disable-model-invocation: true\n---\n",
                "---\n\ndisable-model-invocation: true\n",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalid(moved, "frontmatter must contain disable-model-invocation: true")

        widened = FleetRoot(self)
        widened.manifest["assembly_state"] = "content-building"
        widened.activate("stack-profile")
        path = widened.root / ".github" / "skills" / "stack-profile" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "---\n\n# stack-profile",
                "disable-model-invocation: true\n---\n\n# stack-profile",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalid(widened, "only pcf-deploy and service-onboarding")

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
            Path(".github/agents/builder.agent.md")
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
                "'execute'", outputs[Path(f".github/agents/{name}.agent.md")].decode()
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
            Path(".github/prompts/adr.prompt.md"),
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
            Path(".github/prompts/adr.prompt.md"): (
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
            fleet.root / ".github" / "prompts" / "adr.prompt.md",
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
                path.as_posix().startswith(".github/agents/")
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
        copilot = fleet.root / ".github" / "agents" / "builder.agent.md"
        claude = fleet.root / "generated" / "claude" / "agents" / "builder.md"
        self.assertTrue(copilot.is_file())
        self.assertTrue(claude.is_file())

        record = fleet.skill_record("stack-profile")
        record.clear()
        record.update({"name": "stack-profile", "state": "planned", "activate_task": 10})
        for path in sorted(
            (fleet.root / ".github" / "skills" / "stack-profile").rglob("*"), reverse=True
        ):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        (fleet.root / ".github" / "skills" / "stack-profile").rmdir()
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

        stale = fleet.root / ".github" / "agents" / "nested" / "stale.bin"
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
        bundle_path = fleet.root / ".github" / "skills" / "stack-profile" / "references" / "facts.md"
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
        bundle = fleet.root / ".github" / "skills" / "stack-profile" / "references" / "facts.md"
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
        generated_tree = fleet.root / ".github" / "agents"
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
