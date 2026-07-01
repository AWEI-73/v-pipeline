from pathlib import Path
import json
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillToolContractsTest(unittest.TestCase):
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
        self.assertIn("delivery_candidate.mp4", decision_tree)
        self.assertIn("tools/package_verified_preview.py", material_skill)
        self.assertIn("tools/verified_preview_review_decision.py", material_skill)
        self.assertIn("tools/promote_verified_preview.py", material_skill)


if __name__ == "__main__":
    unittest.main()
