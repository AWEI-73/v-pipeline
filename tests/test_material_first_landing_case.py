import json
import tempfile
import unittest
from pathlib import Path

from tools.material_first_landing_case import run_material_first_landing_case
from tools.pipeline_home import summarize_run


class MaterialFirstLandingCaseTest(unittest.TestCase):
    def test_existing_material_boundary_case_reaches_stable_review_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "material_first_case"

            result = run_material_first_landing_case(run_dir)

            self.assertTrue(result["ok"], result)
            for name in (
                "video_intent.json",
                "material_needs.json",
                "project_material_map.json",
                "material_delta.json",
                "material_map_lifecycle.json",
                "segment_contract.json",
                "rough_cut_plan.json",
                "timeline_build.json",
                "editor_review.json",
                "boundary_report.json",
            ):
                self.assertTrue((run_dir / name).exists(), name)

            lifecycle = json.loads((run_dir / "material_map_lifecycle.json").read_text(encoding="utf-8"))
            self.assertEqual(lifecycle["stage"], "build_ready")
            rough = json.loads((run_dir / "rough_cut_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(rough["ok"], rough)

            summary = summarize_run(run_dir)
            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage5_final_review")


if __name__ == "__main__":
    unittest.main()
