import json
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
            self.assertEqual(report["next_action"], "ready_for_render_or_human_review")
            self.assertEqual(report["metrics"]["fixture_source"], "tracked_manifest_runtime_generated_media")
            self.assertEqual(report["metrics"]["material_asset_count"], 3)
            self.assertEqual(report["metrics"]["rough_clip_count"], 3)
            self.assertTrue(report["metrics"]["delta_ready_for_build"])
            self.assertTrue(report["metrics"]["final_mp4_absent"])
            check_ids = {check["id"] for check in report["checks"]}
            self.assertIn("boundary_acceptance", check_ids)
            self.assertIn("project_material_map", check_ids)
            self.assertIn("material_delta", check_ids)
            self.assertIn("stage5_final_review", check_ids)
            artifacts = "\n".join(report["artifacts"])
            self.assertIn("project_material_map.json", artifacts)
            self.assertIn("material_delta.json", artifacts)
            self.assertIn("material_first_boundary_acceptance_report.json", artifacts)
            self.assertNotIn("runs/storybook-stock-story", artifacts)
            self.assertNotIn(".tmp/r3_acceptance_probe", artifacts)


if __name__ == "__main__":
    unittest.main()
