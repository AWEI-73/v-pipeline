import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.pipeline_interface_discovery import run_discovery


class TestPipelineInterfaceDiscovery(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.dict_path = self.project_root / "docs" / "interface-contracts" / "pipeline-api-dictionary.json"
        self.registry_path = self.project_root / "docs" / "branch-contract-registry.json"
        self.skills_dir = self.project_root / "skills"
        self.tools_dir = self.project_root / "tools"

    def test_discovery_basic_run(self):
        # Run run_discovery
        report = run_discovery(
            self.dict_path,
            self.registry_path,
            self.skills_dir,
            self.tools_dir,
            self.project_root
        )
        self.assertEqual(report["artifact_role"], "pipeline_interface_discovery_report")
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        self.assertGreaterEqual(report["existing_interface_count"], 16)
        self.assertGreater(report["discovered_tool_count"], 0)

    def test_bom_handling(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            bom_dict = temp_dir / "bom_dict.json"
            
            # Write with UTF-8 BOM
            content = json.dumps({
                "artifact_role": "pipeline_api_dictionary",
                "version": 1,
                "interfaces": []
            })
            bom_dict.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
            
            report = run_discovery(
                bom_dict,
                self.registry_path,
                self.skills_dir,
                self.tools_dir,
                self.project_root
            )
            self.assertEqual(report["existing_interface_count"], 0)
            self.assertEqual(report["errors"], [])

    def test_missing_dictionary_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            temp_dict = temp_dir / "missing_dict.json"
            
            with open(self.dict_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            
            # Remove subtitle_voiceover.to.main.build_handoff from dictionary
            orig_len = len(data["interfaces"])
            data["interfaces"] = [
                face for face in data["interfaces"]
                if face["api_id"] != "subtitle_voiceover.to.main.build_handoff"
            ]
            
            self.assertEqual(len(data["interfaces"]), orig_len - 1)
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")
            
            report = run_discovery(
                temp_dict,
                self.registry_path,
                self.skills_dir,
                self.tools_dir,
                self.project_root
            )
            
            missing_ids = {cand["api_id"] for cand in report["missing_dictionary_candidates"]}
            self.assertIn("coverage_gap.subtitle-voiceover.handoff", missing_ids)

    def test_discovery_excludes_infrastructure_tools(self):
        report = run_discovery(
            self.dict_path,
            self.registry_path,
            self.skills_dir,
            self.tools_dir,
            self.project_root
        )
        candidate_tools = {cand["request"]["tool"] for cand in report["candidate_interfaces"]}
        self.assertNotIn("tools/api_surface_manifest.py", candidate_tools)
        self.assertNotIn("tools/pipeline_interface_discovery.py", candidate_tools)
        self.assertNotIn("tools/pipeline_interface_audit.py", candidate_tools)
        self.assertNotIn("tools/dashboard_server.py", candidate_tools)
        self.assertNotIn("tools/workbench_server.py", candidate_tools)

    def test_discovery_does_not_treat_suffix_literals_as_outputs(self):
        report = run_discovery(
            self.dict_path,
            self.registry_path,
            self.skills_dir,
            self.tools_dir,
            self.project_root
        )
        all_outputs = {
            output
            for cand in report["candidate_interfaces"]
            for output in cand["response"].get("outputs", [])
        }
        self.assertNotIn("_handoff.json", all_outputs)
        self.assertNotIn("_acceptance.json", all_outputs)
        self.assertNotIn("_revision_packet.json", all_outputs)

    def test_cli_out_and_json(self):
        script = self.project_root / "tools" / "pipeline_interface_discovery.py"
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            report_out = temp_dir / "report.json"
            
            res = subprocess.run(
                [sys.executable, str(script), "--json", "--out", str(report_out)],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.assertEqual(res.returncode, 0)
            # JSON printed to stdout
            stdout_report = json.loads(res.stdout)
            self.assertEqual(stdout_report["artifact_role"], "pipeline_interface_discovery_report")
            
            # Output file is created
            self.assertTrue(report_out.exists())
            file_report = json.loads(report_out.read_text(encoding="utf-8-sig"))
            self.assertEqual(file_report["artifact_role"], "pipeline_interface_discovery_report")


if __name__ == "__main__":
    unittest.main()
