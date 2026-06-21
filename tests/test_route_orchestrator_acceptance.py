import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.route_orchestrator_acceptance import run_route_orchestrator_acceptance


class RouteOrchestratorAcceptanceTest(unittest.TestCase):
    def test_existing_material_replay_advances_four_stages(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_route_orchestrator_acceptance(
                Path(td),
                route="existing-material-first",
                stage_count=4,
                base_epoch=2000.0,
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["route"], "existing-material-first")
            self.assertEqual(report["final_state"]["current_stage"], 4)
            self.assertEqual([s["status"] for s in report["steps"]], ["done"] * 4)
            self.assertTrue((Path(td) / "project_material_map.json").exists())

    def test_story_first_generated_replay_writes_route_specific_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_route_orchestrator_acceptance(
                Path(td),
                route="story-first",
                stage_count=5,
                base_epoch=3000.0,
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["route"], "story-first")
            self.assertEqual(report["final_state"]["current_stage"], 5)
            material_delta = json.loads((Path(td) / "material_delta.json").read_text(encoding="utf-8"))
            self.assertEqual(material_delta["route"], "story-first")
            self.assertEqual(material_delta["fake_worker_note"], "deterministic route replay artifact")

    def test_bad_artifact_injection_rejects_before_advancing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "final.mp4").write_bytes(b"ORIGINAL")

            report = run_route_orchestrator_acceptance(
                root,
                route="existing-material-first",
                stage_count=3,
                inject_bad_stage=0,
                base_epoch=4000.0,
            )

            self.assertFalse(report["ok"])
            self.assertEqual(report["blocked_at_stage"], 0)
            self.assertIn("must_not_touch changed", report["errors"][0])
            self.assertFalse((root / "route_orchestrator_state.json").exists())

    def test_cli_acceptance_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "report.json"
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "route-orchestrator-acceptance",
                    str(root),
                    "--route",
                    "hybrid",
                    "--stage-count",
                    "3",
                    "--out",
                    str(out),
                    "--base-epoch",
                    "5000",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                stdout=subprocess.DEVNULL,
            )

            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["route"], "hybrid")
            self.assertEqual(report["final_state"]["current_stage"], 3)


if __name__ == "__main__":
    unittest.main()
