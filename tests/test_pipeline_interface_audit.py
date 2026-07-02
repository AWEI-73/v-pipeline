import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.pipeline_interface_audit import audit_dictionary


class TestPipelineInterfaceAudit(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.dict_path = self.project_root / "docs" / "interface-contracts" / "pipeline-api-dictionary.json"
        self.registry_path = self.project_root / "docs" / "branch-contract-registry.json"

    def test_dictionary_parses_and_audits_ok(self):
        errors, warnings, count = audit_dictionary(self.dict_path, self.registry_path, self.project_root)
        self.assertEqual(errors, [], f"Audit failed with errors: {errors}")
        self.assertEqual(count, 16)

    def test_required_interfaces_exist(self):
        with open(self.dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        interfaces = {face["api_id"] for face in data.get("interfaces", [])}
        expected = {
            "main.to.material_map.quick_inventory",
            "main.to.material_map.understanding_matrix",
            "material_map.to.main.build_handoff",
            "main.to.soundtrack_arranger.plan",
            "soundtrack_arranger.to.audio_director.handoff",
            "main.to.subtitle_voiceover.acceptance",
            "subtitle_voiceover.to.main.build_handoff",
            "main.to.effect_factory.plan",
            "effect_factory.to.main.effect_handoff",
            "main.to.workbench_brownfield.review",
            "workbench_brownfield.to.main.route_back_handoff",
            "verify.to.material_map.repair",
            "verify.to.soundtrack_arranger.repair",
            "verify.to.subtitle_voiceover.repair",
            "verify.to.effect_factory.repair",
            "verify.to.workbench_brownfield.repair",
        }
        for api_id in expected:
            self.assertIn(api_id, interfaces, f"Required interface '{api_id}' is missing from dictionary")

    def test_missing_final_mp4_in_forbidden_writes_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "bad_dict.json"
            
            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Remove final.mp4 from forbidden_writes of first interface
            data["interfaces"][0]["forbidden_writes"] = []
            
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")
            
            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("forbidden_writes must contain 'final.mp4'" in err for err in errors))

    def test_duplicate_api_id_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "dup_dict.json"
            
            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Create a duplicate
            dup = dict(data["interfaces"][0])
            data["interfaces"].append(dup)
            
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")
            
            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("Duplicate api_id found" in err for err in errors))

    def test_nonexistent_branch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "bad_branch_dict.json"
            
            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Set invalid from_branch
            data["interfaces"][0]["from_branch"] = "non-existent-branch"
            
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")
            
            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("is not in registry" in err for err in errors))

    def test_missing_subtitle_branch_coverage_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "missing_subtitle_dict.json"

            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["interfaces"] = [
                face for face in data["interfaces"]
                if face.get("to_branch") != "subtitle-voiceover"
                and face.get("from_branch") != "subtitle-voiceover"
            ]

            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("subtitle-voiceover" in err for err in errors))

    def test_missing_response_next_action_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "bad_response_dict.json"

            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["interfaces"][0]["response"].pop("success_next_action", None)

            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("response.success_next_action is required" in err for err in errors))

    def test_artifact_filename_next_action_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "artifact_next_action_dict.json"

            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["interfaces"][0]["response"]["failure_next_action"] = "revision_packet.json"

            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("must be an action id, not artifact filename" in err for err in errors))

    def test_unknown_next_action_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "unknown_next_action_dict.json"

            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["interfaces"][0]["response"]["success_next_action"] = "invented_route_that_does_not_exist"

            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("is not declared in branch next_actions or global actions" in err for err in errors))

    def test_cli_json_mode(self):
        script = self.project_root / "tools" / "pipeline_interface_audit.py"
        res = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        self.assertEqual(res.returncode, 0)
        report = json.loads(res.stdout)
        self.assertEqual(report["artifact_role"], "pipeline_interface_audit_report")
        self.assertTrue(report["ok"])
        self.assertEqual(report["interface_count"], 16)


if __name__ == "__main__":
    unittest.main()
