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

    def test_source_folder_case_builds_dry_artifacts_without_using_final_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "opening").mkdir(parents=True)
            (source / "training").mkdir(parents=True)
            (source / "closing").mkdir(parents=True)
            (source / "最終版的最終版.mp4").write_bytes(b"finished master")
            (source / "opening" / "進場.MOV").write_bytes(b"video")
            (source / "training" / "實習片段.mp4").write_bytes(b"video")
            (source / "closing" / "隊呼.mp4").write_bytes(b"video")
            run_dir = root / "run"

            result = run_material_first_landing_case(run_dir, source_dir=source, max_assets=10)

            self.assertTrue(result["ok"], result)
            materials = json.loads((run_dir / "materials_db.json").read_text(encoding="utf-8"))
            self.assertEqual(materials["total"], 3)
            self.assertTrue(any("final/master" in item["reason"] for item in materials["skipped"]))
            rough = json.loads((run_dir / "rough_cut_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(rough["ok"], rough)
            self.assertEqual(rough["clip_count"], 3)
            self.assertFalse(any("最終版" in clip["source_path"] for clip in rough["clips"]))

    def test_source_folder_case_prefers_training_semantic_folder_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            for folder, filename in (
                ("0325素材", "隊呼.mp4"),
                ("進場", "entry.mov"),
                ("工安體感", "safety.mp4"),
                ("主任勉勵", "director.mp4"),
                ("zz_unused", "other.mp4"),
            ):
                path = source / folder / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"video")

            run_dir = root / "run"
            result = run_material_first_landing_case(run_dir, source_dir=source, max_assets=5)

            self.assertTrue(result["ok"], result)
            rough = json.loads((run_dir / "rough_cut_plan.json").read_text(encoding="utf-8"))
            by_need = {clip["need_id"]: clip["source_path"] for clip in rough["clips"]}
            self.assertIn("進場", by_need["nd_opening"])
            self.assertIn("工安體感", by_need["nd_training"])
            self.assertIn("主任勉勵", by_need["nd_closing"])


if __name__ == "__main__":
    unittest.main()
