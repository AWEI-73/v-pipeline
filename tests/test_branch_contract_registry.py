from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "branch-contract-registry.json"


class BranchContractRegistryTest(unittest.TestCase):
    def _registry(self):
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_has_required_branches_and_contract_fields(self):
        data = self._registry()
        self.assertEqual(data["artifact_role"], "branch_contract_registry")
        branches = {branch["branch_id"]: branch for branch in data["branches"]}

        required_ids = {
            "main-pipeline",
            "material-map",
            "soundtrack-arranger",
            "subtitle-voiceover",
            "effect-factory",
            "workbench-brownfield",
            "verify-delivery",
        }
        self.assertEqual(required_ids, set(branches))

        required_fields = {
            "name",
            "purpose",
            "docs",
            "skills",
            "entry_conditions",
            "required_inputs",
            "canonical_outputs",
            "handoff_outputs",
            "next_actions",
            "stop_gates",
            "forbidden_writes",
            "return_to",
        }
        for branch_id, branch in branches.items():
            missing = required_fields - set(branch)
            self.assertEqual(set(), missing, branch_id)
            for field in required_fields:
                self.assertTrue(branch[field], f"{branch_id}.{field} is empty")

    def test_registry_references_existing_docs_and_skills(self):
        data = self._registry()
        for branch in data["branches"]:
            for rel in branch["docs"] + branch["skills"]:
                path = ROOT / rel
                self.assertTrue(path.exists(), f"{branch['branch_id']} references missing {rel}")

    def test_registry_is_announced_by_operator_entry_docs(self):
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        decision_tree = (ROOT / "docs" / "pipeline-decision-tree.md").read_text(
            encoding="utf-8"
        )

        for text in [runbook, decision_tree]:
            self.assertIn("docs/branch-contract-registry.json", text)
            self.assertIn("branch", text.lower())

        registry_md = (ROOT / "docs" / "branch-contract-registry.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Material Map", registry_md)
        self.assertIn("Effect Factory", registry_md)
        self.assertIn("Workbench / Brownfield", registry_md)
        self.assertIn("Verify / Delivery Gate", registry_md)

    def test_pipeline_map_includes_branch_contract_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/pipeline_map.py",
                    "--out-dir",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

            payload = json.loads((Path(tmp) / "pipeline_map.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "branch_contract_registry",
                payload["branch_contract_registry"]["artifact_role"],
            )
            branch_ids = {branch["branch_id"] for branch in payload["branches"]}
            self.assertIn("workbench-brownfield", branch_ids)
            self.assertIn("soundtrack-arranger", branch_ids)


if __name__ == "__main__":
    unittest.main()
