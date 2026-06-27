import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class DeliveryGateReportCliTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
