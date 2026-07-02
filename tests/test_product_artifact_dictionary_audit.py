import json
import tempfile
import unittest
from pathlib import Path

from tools.product_artifact_dictionary_audit import audit_product_dictionary


class TestProductArtifactDictionaryAudit(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.dict_path = (
            self.project_root
            / "docs"
            / "interface-contracts"
            / "pipeline-product-artifact-dictionary.json"
        )

    def test_product_dictionary_audits_ok(self):
        errors, warnings, count = audit_product_dictionary(self.dict_path)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertGreaterEqual(count, 8)

    def test_required_product_artifacts_exist(self):
        data = json.loads(self.dict_path.read_text(encoding="utf-8-sig"))
        artifacts = {item["artifact_name"] for item in data["artifacts"]}
        expected = {
            "source_media_review.json",
            "material_matrix.json",
            "edit_decision_plan.json",
            "audio_decision_plan.json",
            "effect_decision_plan.json",
            "subtitle_voiceover_decision_plan.json",
            "build_handoff.json",
            "final_review_bundle.json",
        }
        self.assertTrue(expected.issubset(artifacts))

    def test_edit_decision_plan_has_functional_parameter_groups(self):
        data = json.loads(self.dict_path.read_text(encoding="utf-8-sig"))
        edit_plan = next(
            item for item in data["artifacts"]
            if item["artifact_name"] == "edit_decision_plan.json"
        )
        params = {item["name"] for item in edit_plan["functional_parameters"]}
        self.assertTrue({"cuts", "overlays", "audio", "effects", "subtitles", "transitions"}.issubset(params))

    def test_missing_owner_branch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dict = Path(temp) / "bad_product_dictionary.json"
            data = json.loads(self.dict_path.read_text(encoding="utf-8-sig"))
            data["artifacts"][0].pop("owner_branch", None)
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_product_dictionary(temp_dict)
            self.assertTrue(any("missing owner_branch" in err for err in errors))

    def test_missing_functional_parameters_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dict = Path(temp) / "bad_product_dictionary.json"
            data = json.loads(self.dict_path.read_text(encoding="utf-8-sig"))
            for item in data["artifacts"]:
                if item["artifact_name"] == "edit_decision_plan.json":
                    item["functional_parameters"] = []
                    break
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_product_dictionary(temp_dict)
            self.assertTrue(any("functional_parameters must be a non-empty list" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
