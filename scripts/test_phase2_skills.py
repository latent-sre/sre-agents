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
ROOT_CAUSE_DESCRIPTION = (
    "Use when debugging any bug, test failure, or unexpected behavior — before proposing a fix — and "
    "especially after a fix attempt has already failed, or when guessing has started (\"maybe it's X, "
    "let me try changing it\"). Triggers: 'debug this failure', 'why did this test fail', 'the fix did "
    "not work'. For a production incident with an unknown cause, the `sre` agent owns the investigation; "
    "this skill is the method it (and sde) load."
)
RUNBOOK_DESCRIPTION = (
    "Write or update an operational runbook or operating doc — how to check, restart, and recover a "
    "service, written for the stressed 3am reader. Triggers: 'write a runbook', 'document this "
    "procedure', 'how do we handle X at 3am'. Every slot is filled or marked 'n/a — why'; commands "
    "carry evidence labels. Ownership map only—not a load: canonical `postmortem` owns post-incident "
    "retrospective structure."
)
ENG_LADDER_DESCRIPTION = (
    "Set your altitude before the task — engineering (builder: a scoped change in one component; "
    "principal: cross-cutting design, contract/schema change, migration, real blast radius; "
    "distinguished: high-ambiguity architecture, build-vs-buy, a standard others follow) or SRE "
    "(responder → investigator → elite for alerts and incidents). Triggers: 'how rigorous should this "
    "be', 'review this at the principal level', 'what tier is this incident work'. Read exactly one "
    "tier file."
)
EXPECTED_ACTIVE = {"stack-profile", "root-cause", "runbook", "eng-ladder"}


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
        normalized = " ".join(
            line.strip().removeprefix("> ").strip() for line in text.splitlines()
        )
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

    def test_task11_root_cause_preserves_the_winner_and_legacy_example(self):
        record = self.record("root-cause")
        self.assertEqual(
            {
                "name": "root-cause",
                "state": "active",
                "directory": "skills/root-cause",
                "references": [],
                "assets": [],
                "scripts": [],
            },
            record,
        )
        self.assert_inventory("root-cause", {"SKILL.md"})
        text = (ROOT / "skills/root-cause/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(ROOT_CAUSE_DESCRIPTION, frontmatter_description(text))
        self.assertIn('argument-hint: "[the bug or unexpected behavior]"', text)
        for required in (
            'Announce at start: "Using root-cause: reproduce → evidence → hypothesis → verify → fix."',
            "## The loop",
            "## The three-strikes rule",
            "## Red flags — stop and restart the loop",
            "## Worked example (the hypothesis table is the method)",
            "CI uses a different TZ → date assertion off by one",
            "Causal chain: *unpinned test clock → asserts a localized date → passes in ET, fails in UTC CI.*",
            "**regression test** asserts the export under a fixed TZ",
        ):
            self.assertIn(required, text)
        self.assertNotIn("debug-rca", text)
        _manifest, ready = generate_fleet.load_and_validate(ROOT)
        self.assertEqual([], ready)

    def test_task12_runbook_merges_sde_body_and_linked_sre_template(self):
        record = self.record("runbook")
        self.assertEqual(
            {
                "name": "runbook",
                "state": "active",
                "directory": "skills/runbook",
                "references": [],
                "assets": ["assets/runbook-template.md"],
                "scripts": [],
            },
            record,
        )
        self.assert_inventory("runbook", {"SKILL.md", "assets/runbook-template.md"})
        text = (ROOT / "skills/runbook/SKILL.md").read_text(encoding="utf-8")
        asset = (ROOT / "skills/runbook/assets/runbook-template.md").read_text(encoding="utf-8")
        self.assertEqual(RUNBOOK_DESCRIPTION, frontmatter_description(text))
        self.assertIn('argument-hint: "[service or tool]"', text)
        normalized = " ".join(
            line.strip().removeprefix("> ").strip() for line in text.splitlines()
        )
        for required in (
            "Full fill-in template: [runbook template](./assets/runbook-template.md) — copy it to start.",
            "## Runbook vs playbook vs SOP",
            "## Authoring rules",
            "Machine-linkable frontmatter",
            "verified in ~90 days",
            "Ownership map only—not a load: canonical `incident-command` owns live-incident coordination",
            "Crawl → Walk → Run",
            "**Splunk:** `... | lookup instructions_lookup alert_type OUTPUT runbook_url`.",
            "**Grafana:** a `runbook_url` annotation",
            "**Wavefront:** the alert's resolution/runbook link",
            "**Moogsoft:** enrichment that attaches the runbook URL",
            "### Worked excerpt — tier-marked steps with provenance",
            "⚠️ (Tier 2 — needs explicit human approval for this command/target)",
            "[verified] (transcript 2026-07-02)",
            "first checks and procedure step 1 [sourced] from incident #2026-07-02 transcript",
            "any later step is [unverified] until a human tests it",
            "mark it `[unverified]` rather than presenting it as tested",
            "mark anything `[unverified]`",
        ):
            self.assertIn(required, normalized)
        self.assertNotIn("steps 1–2 [verified]", normalized)
        self.assertNotIn("step 3 [unverified", normalized)
        for required in (
            "Tier 2/3: record explicit human approval for the exact command/target plus rollback evidence before execution",
            "Hand over: trigger, evidence, attempted steps, current state, and the current owner.",
            "after recovery, hand the timeline and evidence to the `scribe` agent for retrospective documentation.",
        ):
            self.assertIn(required, asset)
        for forbidden in (
            "production-change-gate",
            "handoff-protocol",
            "incident-severity",
            "sre-monitor",
            "sde-engineer",
        ):
            self.assertNotIn(forbidden, text + asset)

    def test_task13_eng_ladder_is_self_sovereign_and_dependency_free(self):
        references = [
            "references/builder.md",
            "references/principal.md",
            "references/distinguished.md",
            "references/responder.md",
            "references/investigator.md",
            "references/elite.md",
            "references/golden-signals.md",
        ]
        record = self.record("eng-ladder")
        self.assertEqual(
            {
                "name": "eng-ladder",
                "state": "active",
                "directory": "skills/eng-ladder",
                "references": references,
                "assets": [],
                "scripts": [],
            },
            record,
        )
        self.assert_inventory("eng-ladder", {"SKILL.md", *references})
        root = ROOT / "skills/eng-ladder"
        text = (root / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(ENG_LADDER_DESCRIPTION, frontmatter_description(text))
        self.assertIn('argument-hint: "[task, diff, file, or design doc]"', text)
        for relative in references:
            self.assertIn(f"({('./' + relative)})", text)
        for required in (
            "## The SRE track — altitude for an alert or incident",
            "Each rung's reference file is its full bar.",
            "Ownership map only—not a load: canonical `ops-tooling` applies this altitude routing inside its build pipeline.",
            "Application-operations work routes to the `sre` agent; platform internals route to the platform team",
        ):
            self.assertIn(required, text)
        self.assertNotIn("eng-ladder", self.fleet["skill_dependencies"])
        self.assertNotIn("required-skill-dependencies:start", text)

        builder = (root / "references/builder.md").read_text(encoding="utf-8")
        principal = (root / "references/principal.md").read_text(encoding="utf-8")
        distinguished = (root / "references/distinguished.md").read_text(encoding="utf-8")
        responder = (root / "references/responder.md").read_text(encoding="utf-8")
        investigator = (root / "references/investigator.md").read_text(encoding="utf-8")
        elite = (root / "references/elite.md").read_text(encoding="utf-8")
        golden = (root / "references/golden-signals.md").read_text(encoding="utf-8")
        builder_flat = " ".join(builder.split())
        principal_flat = " ".join(principal.split())
        distinguished_flat = " ".join(distinguished.split())
        responder_flat = " ".join(responder.split())
        investigator_flat = " ".join(investigator.split())
        elite_flat = " ".join(elite.split())
        golden_flat = " ".join(golden.split())
        self.assertIn("This file is the bar for the builder rung — self-contained.", builder_flat)
        self.assertIn("This file is the bar for the principal rung — self-contained.", principal_flat)
        self.assertIn("This file is the bar for the distinguished rung — self-contained.", distinguished_flat)
        self.assertIn(
            "Ownership map only—not a load: canonical `backend-craft` covers backend work and canonical `frontend-craft` covers UI work",
            builder_flat,
        )
        self.assertIn("A third failed fix means the diagnosis is wrong", builder_flat)
        self.assertIn("**Conventional Commits**", builder_flat)
        self.assertIn("loading [principal](./principal.md)", builder_flat)
        self.assertIn("load [builder](./builder.md) (or hand execution to the `sde` agent)", principal_flat)
        self.assertIn("loading [distinguished](./distinguished.md)", principal_flat)
        self.assertIn("New operational steps → the `scribe` agent; deployment execution → the human release owner.", principal_flat)
        self.assertIn("Execution of the chosen design → the `sde` agent; operating evidence → `sre`/`observer`", distinguished_flat)
        self.assertIn("read [investigator](./investigator.md)", responder_flat)
        self.assertIn("What you hand over", responder_flat)
        self.assertIn("Logs in Splunk or Loki", investigator_flat)
        self.assertIn("Metrics in Wavefront, Prometheus, or Grafana", investigator_flat)
        self.assertIn("canonical `observer` owns the follow-up SLI/alert", elite_flat)
        self.assertIn("canonical `postmortem` owns the durable write-up", elite_flat)
        self.assertIn("this file defines the signal set, not backend query methods", golden_flat)

        all_text = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.md"))
        )
        for forbidden in (
            "agents/",
            "${CLAUDE_PLUGIN_ROOT}",
            "sde-agents",
            "sre-engineer",
            "sre-monitor",
            "incident-severity",
            "handoff-protocol",
            "blameless-postmortem",
            "load `pcf-ops`",
            "load `sde-agents:root-cause`",
        ):
            self.assertNotIn(forbidden, all_text)
        self.assertEqual(1, all_text.count("**Make it work, make it right, make it fast"))
        self.assertEqual(1, all_text.count("**Rule of Three**"))
        self.assertEqual(1, all_text.count("Hyrum's"))
        self.assertEqual(1, all_text.count("SemVer"))
        self.assertEqual(1, all_text.count("**Conventional Commits**"))

    def test_completed_slice_has_exact_planned_active_partition_and_zero_ready_agents(self):
        active = {
            record["name"] for record in self.fleet["skills"] if record["state"] == "active"
        }
        planned = {
            record["name"] for record in self.fleet["skills"] if record["state"] == "planned"
        }
        self.assertEqual(EXPECTED_ACTIVE, active)
        self.assertEqual(26 - len(EXPECTED_ACTIVE), len(planned))
        self.assertEqual(set(), active & planned)
        _manifest, ready = generate_fleet.load_and_validate(ROOT)
        self.assertEqual([], ready)


if __name__ == "__main__":
    unittest.main()
