import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_first_golden_path import (
    build_material_first_golden_path_report,
)


class MaterialFirstGoldenPathTest(unittest.TestCase):
    def test_golden_path_generates_fixture_and_boundary_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = build_material_first_golden_path_report(root)

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["scenario"], "material-first-golden-path")
            self.assertEqual(report["next_action"], "ready_for_render")
            self.assertEqual(report["metrics"]["fixture_source"], "tracked_manifest_runtime_generated_media")
            self.assertEqual(report["metrics"]["material_asset_count"], 3)
            self.assertEqual(report["metrics"]["rough_clip_count"], 3)
            self.assertTrue(report["metrics"]["delta_ready_for_build"])
            self.assertTrue(report["metrics"]["final_mp4_absent"])
            self.assertTrue(report["metrics"]["asset_store_imported"])
            self.assertTrue(report["metrics"]["asset_path_audit_strict_ok"])
            self.assertEqual(report["metrics"]["asset_path_audit_strict_finding_count"], 0)
            self.assertTrue(report["metrics"]["review_packet_written"])
            self.assertTrue(report["metrics"]["review_verdict_accepted"])
            self.assertTrue(report["metrics"]["render_readiness_ok"])
            self.assertTrue(report["metrics"]["render_handoff_written"])
            check_ids = {check["id"] for check in report["checks"]}
            self.assertIn("boundary_acceptance", check_ids)
            self.assertIn("asset_store_import", check_ids)
            self.assertIn("asset_path_audit_strict", check_ids)
            self.assertIn("material_review_packet", check_ids)
            self.assertIn("review_verdict_acceptance", check_ids)
            self.assertIn("render_promotion_gate", check_ids)
            self.assertIn("project_material_map", check_ids)
            self.assertIn("material_delta", check_ids)
            self.assertIn("stage5_final_review", check_ids)
            artifacts = "\n".join(report["artifacts"])
            self.assertIn("assets/materials/real_0001.jpg", artifacts)
            self.assertIn("material_review_packet.json", artifacts)
            self.assertIn("material_first_review_verdict_acceptance.json", artifacts)
            self.assertIn("render_readiness_report.json", artifacts)
            self.assertIn("render_handoff.json", artifacts)
            self.assertIn("project_material_map.json", artifacts)
            self.assertIn("material_delta.json", artifacts)
            self.assertIn("material_first_boundary_acceptance_report.json", artifacts)
            self.assertNotIn("runs/storybook-stock-story", artifacts)
            self.assertNotIn(".tmp/r3_acceptance_probe", artifacts)

    def test_replay_cli_material_first_golden_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "material_first_golden_replay.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "replay-acceptance",
                    "--scenario",
                    "material-first-golden-path",
                    "--out",
                    str(out),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["scenario"], "material-first-golden-path")
            self.assertEqual(report["next_action"], "ready_for_render")


if __name__ == "__main__":
    unittest.main()
