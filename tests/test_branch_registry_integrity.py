import json
import re
import unittest
from pathlib import Path

from video_pipeline_core.next_action_vocabulary import NEXT_ACTION_VOCABULARY


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "branch-contract-registry.json"


class BranchRegistryIntegrityTest(unittest.TestCase):
    def _registry(self):
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_parses(self):
        registry = self._registry()
        branches = registry.get("branches")
        self.assertIsInstance(branches, list)
        branch_ids = {branch.get("branch_id") for branch in branches}
        self.assertEqual(
            branch_ids,
            {
                "main-pipeline",
                "material-map",
                "soundtrack-arranger",
                "subtitle-voiceover",
                "effect-factory",
                "workbench-brownfield",
                "verify-delivery",
            },
        )

    def test_skills_exist(self):
        for branch in self._registry()["branches"]:
            for rel in branch.get("skills", []):
                self.assertTrue((ROOT / rel).exists(), f"{branch.get('branch_id')} skill missing: {rel}")

    def test_docs_exist(self):
        for branch in self._registry()["branches"]:
            for rel in branch.get("docs", []):
                self.assertTrue((ROOT / rel).exists(), f"{branch.get('branch_id')} doc missing: {rel}")

    def test_registry_next_actions_in_vocabulary(self):
        missing = sorted(
            {
                action
                for branch in self._registry()["branches"]
                for action in branch.get("next_actions", [])
                if action not in NEXT_ACTION_VOCABULARY
            }
        )
        self.assertEqual(missing, [])

    def test_dashboard_state_literals_in_vocabulary(self):
        source = (ROOT / "video_pipeline_core" / "dashboard_state.py").read_text(encoding="utf-8")
        literals = sorted(set(re.findall(r'next_action\s*=\s*"([^"]+)"', source)))
        missing = [literal for literal in literals if literal not in NEXT_ACTION_VOCABULARY]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
