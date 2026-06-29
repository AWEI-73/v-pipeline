import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class DeliveryGateReportCliTest(unittest.TestCase):
    def test_complete_delivery_run_uses_complete_video_gate_not_dashboard_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "delivery_requirements.json", {
                "requires_audio": True,
                "requires_music": True,
                "requires_soundtrack_probe": True,
            })
            (run / "final.mp4").write_bytes(b"placeholder")
            _write(run / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "version": 1,
                "pass": True,
                "blocking": [],
                "next_action": None,
            })

            complete_gate = {
                "artifact_role": "complete_video_delivery_gate",
                "version": 1,
                "pass": False,
                "blocking": [{
                    "rule": "soundtrack_probe_has_no_section_fit",
                    "artifact": "soundtrack_probe_report.json",
                    "next_action": "rerun_soundtrack_probe",
                }],
                "next_action": "rerun_soundtrack_probe",
            }
            with patch("tools.write_delivery_gate_report.evaluate_complete_video_delivery", return_value=complete_gate) as mocked:
                from tools.write_delivery_gate_report import write_delivery_gate_report
                gate = write_delivery_gate_report(run)

            mocked.assert_called_once_with(run)
            self.assertFalse(gate["pass"])
            self.assertEqual(gate["report_source"], "complete_video_delivery_gate")
            self.assertEqual(gate["next_action"], "rerun_soundtrack_probe")
            self.assertEqual(gate["blocking"][0]["rule"], "soundtrack_probe_has_no_section_fit")

    def test_writes_delivery_gate_json_even_when_verify_result_passes(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "brief.json", {"title": "material mismatch fixture"})
            _write(run / "verify_result.json", {"pass": True})
            _write(run / "material_coverage_map.json", {"coverage": []})
            _write(run / "segment_contract.json", {
                "segments": [{
                    "segment": 2,
                    "material_map_ids": ["commute_001"],
                    "need_refs": ["need_commute_motion"],
                }],
            })
            _write(run / "project_material_map.json", {
                "assets": [
                    {
                        "asset_id": "city_dawn_001",
                        "scenes": [{
                            "scene_id": "city_dawn_001:0",
                            "satisfies": ["need_city_dawn"],
                        }],
                    },
                ],
            })
            _write(run / "timeline_build.json", {
                "clips": [{
                    "segment": 2,
                    "scene_id": "city_dawn_001:0",
                    "source_path": "city_dawn.mp4",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertEqual(summary["next_action"], "revise_material_selection_or_review")

            gate = json.loads((run / "delivery_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(gate["pass"])
            self.assertEqual(gate["generated_by"], "tools/write_delivery_gate_report.py")
            self.assertEqual(gate["report_source"], "dashboard_state.artifacts.delivery_gate")
            self.assertTrue(any(
                item.get("rule") == "timeline_need_ref_mismatch"
                for item in gate.get("blocking", [])
            ))
            self.assertEqual(
                json.loads((run / "verify_result.json").read_text(encoding="utf-8")),
                {"pass": True},
            )

    def test_dashboard_gate_pass_without_video_candidate_fails_closed(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertEqual(summary["next_action"], "create_or_verify_video_candidate")
            self.assertTrue(any(
                item.get("rule") == "missing_video_candidate"
                for item in summary.get("blocking", [])
            ))


if __name__ == "__main__":
    unittest.main()
