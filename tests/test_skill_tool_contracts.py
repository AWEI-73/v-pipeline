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


if __name__ == "__main__":
    unittest.main()
