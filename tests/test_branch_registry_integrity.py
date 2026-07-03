import json
import re
import unittest
from pathlib import Path

from video_pipeline_core.next_action_vocabulary import NEXT_ACTION_VOCABULARY


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "branch-contract-registry.json"
ARTIFACT_DICTIONARY_PATH = ROOT / "docs" / "interface-contracts" / "pipeline-product-artifact-dictionary.json"
API_DICTIONARY_PATH = ROOT / "docs" / "interface-contracts" / "pipeline-api-dictionary.json"
STAGE_KEYS = {
    "stage",
    "skill",
    "artifacts_in",
    "artifacts_out",
    "gate",
    "next_actions_on_pass",
    "next_actions_on_fail",
}


class BranchRegistryIntegrityTest(unittest.TestCase):
    def _registry(self):
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def _artifact_names(self):
        dictionary = json.loads(ARTIFACT_DICTIONARY_PATH.read_text(encoding="utf-8"))
        artifact_names = {
            artifact.get("artifact_name")
            for artifact in dictionary.get("artifacts", [])
            if artifact.get("artifact_name")
        }
        api_dictionary = json.loads(API_DICTIONARY_PATH.read_text(encoding="utf-8"))
        for interface in api_dictionary.get("interfaces", []):
            for section in ("request", "response"):
                payload = interface.get(section) or {}
                for key in ("inputs", "outputs"):
                    artifact_names.update(
                        name
                        for name in payload.get(key, [])
                        if isinstance(name, str) and "." in name
                    )
            artifact_names.update(
                name
                for name in interface.get("forbidden_writes", [])
                if isinstance(name, str) and "." in name
            )
        return artifact_names

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

    def test_core_next_action_literals_in_vocabulary(self):
        patterns = [
            re.compile(r'next_action\s*=\s*"([^"]+)"'),
            re.compile(r'"next_action"\s*:\s*"([^"]+)"'),
        ]
        literals = set()
        for source_path in (ROOT / "video_pipeline_core").glob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            for pattern in patterns:
                literals.update(pattern.findall(source))
        literals = sorted(literals)
        missing = [literal for literal in literals if literal not in NEXT_ACTION_VOCABULARY]
        self.assertEqual(missing, [])

    def test_stage_skills_exist(self):
        for branch in self._registry()["branches"]:
            for stage in branch.get("stages", []):
                self.assertEqual(set(stage), STAGE_KEYS, f"{branch.get('branch_id')} stage schema")
                rel = stage["skill"]
                self.assertTrue((ROOT / rel).exists(), f"{branch.get('branch_id')} stage skill missing: {rel}")

    def test_stage_artifacts_in_dictionary(self):
        artifact_names = self._artifact_names()
        missing = sorted(
            {
                artifact
                for branch in self._registry()["branches"]
                for stage in branch.get("stages", [])
                for key in ("artifacts_in", "artifacts_out")
                for artifact in stage.get(key, [])
                if artifact not in artifact_names
            }
        )
        self.assertEqual(missing, [])

    def test_stage_next_actions_in_vocabulary(self):
        missing = sorted(
            {
                action
                for branch in self._registry()["branches"]
                for stage in branch.get("stages", [])
                for key in ("next_actions_on_pass", "next_actions_on_fail")
                for action in stage.get(key, [])
                if action not in NEXT_ACTION_VOCABULARY
            }
        )
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
