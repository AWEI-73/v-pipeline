from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from video_pipeline_core.skill_tool_contract import (
    ALLOWED_CLASS_ROLE,
    CAPABILITY_ROLES,
    EXECUTION_CLASSES,
    audit_repository_contracts,
    load_contracts,
)
from video_pipeline_core.capability_catalog import build_catalog


ROOT = Path(__file__).resolve().parents[1]


class SkillToolContractsTest(unittest.TestCase):
    def test_real_direct_tool_cards_have_registered_tool_path_commands(self):
        contracts, parse_errors = load_contracts(ROOT / "skills")
        self.assertEqual([], parse_errors)

        catalog = build_catalog(contracts)
        self.assertTrue(catalog["ok"], catalog)
        direct_cards = [
            card for card in catalog["cards"] if card["tool"].startswith("tools/")
        ]
        self.assertTrue(direct_cards)
        for card in direct_cards:
            with self.subTest(capability_id=card["capability_id"]):
                self.assertEqual(card["tool"], card["command"])

    def test_direct_tool_identity_does_not_use_dispatch_or_catalog_command_sets(self):
        contract = {
            "_source": "skills/direct-fixture.md",
            "version": 1,
            "skill": "direct-fixture",
            "stage_owner": "direct_fixture",
            "capability_namespace": "cap.direct-fixture.*",
            "capability_lookup_owner": "direct-fixture",
            "triggers": ["fixture"],
            "forbidden_tools": [],
            "canonical_tools": [{
                "capability_id": "cap.direct-fixture.tool.v1",
                "tool": "tools/direct_fixture.py",
                "execution_class": "deterministic",
                "capability_role": "operation",
                "loops": ["L3"],
                "maturity": "bounded",
                "certified_scope": "direct fixture",
            }],
        }

        errors = audit_repository_contracts(
            [contract],
            python_tools=["tools/direct_fixture.py"],
            dispatch_commands=[],
            catalog_commands=[],
        )

        self.assertEqual([], [item for item in errors if item["code"] in {
            "command_not_dispatched", "command_not_cataloged"
        }])

    def test_real_canonical_cards_have_allowed_accountability_pair(self):
        contracts, parse_errors = load_contracts(ROOT / "skills")
        self.assertEqual([], parse_errors)

        canonical_cards = [
            (contract, entry)
            for contract in contracts
            for entry in contract.get("canonical_tools", [])
            if isinstance(entry, dict)
        ]
        self.assertTrue(canonical_cards)
        for contract, entry in canonical_cards:
            capability_id = entry.get("capability_id")
            with self.subTest(
                skill=contract.get("skill"), capability_id=capability_id
            ):
                self.assertIn("execution_class", entry)
                self.assertIn("capability_role", entry)
                execution_class = entry.get("execution_class")
                capability_role = entry.get("capability_role")
                self.assertIn(execution_class, EXECUTION_CLASSES)
                self.assertIn(capability_role, CAPABILITY_ROLES)
                self.assertIn(execution_class, ALLOWED_CLASS_ROLE[capability_role])

    def test_audit_reports_clean_skill_tool_contracts(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/skill_tool_contract_audit.py",
                "--skills-dir",
                "skills",
                "--tools-dir",
                "tools",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        report = json.loads(completed.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual([], report["errors"])
        self.assertEqual([], report["unowned_python_tools"])

    def test_stage_tool_simplification_doc_is_self_contained(self):
        text = (ROOT / "docs" / "stage-tool-simplification.md").read_text(encoding="utf-8")
        for expected in [
            "Stage Tool Matrix",
            "Skill Tool Contract",
            "Tool Visibility Labels",
            "Audit Rules",
            "tools/skill_tool_contract_audit.py",
            "Do not make readers open an attachment to understand the tool route",
        ]:
            self.assertIn(expected, text)

    def test_dialogue_highlight_route_is_documented(self):
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        decision_tree = (ROOT / "docs" / "pipeline-decision-tree.md").read_text(
            encoding="utf-8"
        )
        material_skill = (ROOT / "skills" / "material-map.md").read_text(
            encoding="utf-8"
        )
        verify_skill = (ROOT / "skills" / "verify.md").read_text(encoding="utf-8")

        for text in [runbook, decision_tree, material_skill]:
            self.assertIn("source-dialogue-script", text)
            self.assertIn("dialogue_edit_script.json", text)

        self.assertIn("correct subtitle", runbook)
        self.assertIn("complete sentence", runbook)
        self.assertIn("speech-first highlight", decision_tree)
        self.assertIn("eye / ear / head", material_skill)
        self.assertIn("minimum visual evidence", verify_skill)
        self.assertIn("sparse scene", verify_skill)
        self.assertIn("package_verified_preview.py", runbook)
        self.assertIn("verified_preview_review_decision.py", runbook)
        self.assertIn("promote_verified_preview.py", runbook)
        self.assertIn("verified_preview_package.json", decision_tree)
        self.assertIn("verified_preview_review_decision.json", decision_tree)
        self.assertIn("workbench_revision_request.json", decision_tree)
        self.assertIn("delivery_candidate.mp4", decision_tree)
        self.assertIn("tools/package_verified_preview.py", material_skill)
        self.assertIn("tools/verified_preview_review_decision.py", material_skill)
        self.assertIn("tools/promote_verified_preview.py", material_skill)
        self.assertIn("workbench_revision_request.json", runbook)

    def test_synthetic_audit_reports_missing_accountability_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "skills"
            tools = root / "tools"
            skills.mkdir()
            tools.mkdir()
            (tools / "voiceover_provider_plan.py").write_text("# fixture\n", encoding="utf-8")
            contract = {
                "version": 1,
                "skill": "voiceover-provider",
                "stage_owner": "voiceover_provider_plan",
                "capability_namespace": "cap.voiceover.*",
                "capability_lookup_owner": "voiceover-provider",
                "triggers": ["voiceover"],
                "forbidden_tools": [],
                "canonical_tools": [{
                    "capability_id": "cap.voiceover.voiceover-provider-plan.v1",
                    "tool": "tools/voiceover_provider_plan.py",
                    "loops": ["L2"],
                    "maturity": "bounded",
                    "certified_scope": "synthetic provider planning fixture",
                    "when": "plan provider selection",
                    "inputs": ["voiceover_request.json"],
                    "outputs": ["voiceover_provider_plan.json"],
                    "stop_if": ["request is invalid"],
                }],
            }
            skills.joinpath("voiceover-provider.md").write_text(
                "<!-- TOOL_CONTRACT_START -->\n"
                + json.dumps(contract, ensure_ascii=False)
                + "\n<!-- TOOL_CONTRACT_END -->\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "skill_tool_contract_audit.py"),
                    "--skills-dir",
                    str(skills),
                    "--tools-dir",
                    str(tools),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(
                {"missing_execution_class", "missing_capability_role"},
                {item["code"] for item in report["capability_errors"]},
            )

    def test_retirement_only_audit_context_keeps_live_command_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "skills"
            tools = root / "tools"
            skills.mkdir()
            tools.mkdir()
            contract = {
                "version": 1,
                "skill": "dispatch-capabilities-fixture",
                "stage_owner": "dispatch_capabilities_fixture",
                "capability_namespace": "cap.fixture.*",
                "capability_lookup_owner": "dispatch-capabilities-fixture",
                "triggers": ["fixture"],
                "forbidden_tools": [],
                "canonical_tools": [{
                    "capability_id": "cap.fixture.dispatch-capabilities.v1",
                    "tool": "python .\\video_tools.py dispatch-capabilities",
                    "execution_class": "deterministic",
                    "capability_role": "operation",
                    "loops": ["L3"],
                    "maturity": "bounded",
                    "certified_scope": "retirement-only context should not blank live command discovery",
                    "when": "query the live capability dispatch surface",
                    "inputs": ["capability_query.json"],
                    "outputs": ["capability_query_result.json"],
                    "stop_if": ["selector is invalid"],
                }],
            }
            skills.joinpath("dispatch-capabilities-fixture.md").write_text(
                "<!-- TOOL_CONTRACT_START -->\n"
                + json.dumps(contract, ensure_ascii=False)
                + "\n<!-- TOOL_CONTRACT_END -->\n",
                encoding="utf-8",
            )
            root.joinpath("audit_context.json").write_text(
                json.dumps({
                    "retirement_pre_ids": ["cap.fixture.dispatch-capabilities.v1"],
                    "retirement_post_ids": ["cap.fixture.dispatch-capabilities.v1"],
                    "retirement_rows": [],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "skill_tool_contract_audit.py"),
                    "--skills-dir",
                    str(skills),
                    "--tools-dir",
                    str(tools),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                0,
                completed.returncode,
                completed.stdout + completed.stderr,
            )
            report = json.loads(completed.stdout)
            self.assertTrue(report["ok"], report)
            self.assertEqual([], report["broken_command_references"])
            self.assertEqual([], report["retirement_delta_errors"])


if __name__ == "__main__":
    unittest.main()
