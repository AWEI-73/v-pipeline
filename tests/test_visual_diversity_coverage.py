import json
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core import visual_diversity_coverage as vdc
from video_tools import cmd_visual_diversity_coverage


def _project_map(scenes):
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{"asset_id": "asset-a", "scenes": scenes}],
    }


class CoverageTest(unittest.TestCase):
    def test_reports_each_axis_and_missing_scene_references(self):
        report = vdc.build_visual_diversity_coverage(_project_map([
            {"visual_family": "classroom", "angle_scale": "wide",
             "action_family": "lecture", "subject": "students"},
            {"visual_family": "practice", "angle_scale": "close"},
            {},
        ]))
        self.assertEqual(report["metrics"]["scene_count"], 3)
        self.assertEqual(report["axes"]["visual_family"]["labeled_count"], 2)
        self.assertEqual(report["axes"]["visual_family"]["coverage_ratio"], 0.6667)
        self.assertEqual(
            report["axes"]["action_family"]["missing"],
            [{"asset_id": "asset-a", "scene_index": 1},
             {"asset_id": "asset-a", "scene_index": 2}],
        )
        self.assertEqual(report["metrics"]["fully_labeled_scene_ratio"], 0.3333)

    def test_visual_family_threshold_honestly_blocks_vd2(self):
        report = vdc.build_visual_diversity_coverage(
            _project_map([{"visual_family": "a"}, {}, {}]),
            min_visual_family_coverage=0.7,
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertEqual(report["decision"]["reason"], "visual_family_coverage_below_threshold")

    def test_sufficient_visual_family_coverage_allows_vd2_evaluation(self):
        report = vdc.build_visual_diversity_coverage(
            _project_map([{"visual_family": "a"}, {"visual_family": "b"}, {}]),
            min_visual_family_coverage=0.6,
        )
        self.assertTrue(report["ready_for_vd2"])

    def test_empty_project_is_not_ready_for_vd2(self):
        report = vdc.build_visual_diversity_coverage(_project_map([]))
        self.assertFalse(report["ready_for_vd2"])
        self.assertEqual(report["decision"]["reason"], "no_scenes")

    def test_invalid_project_map_fails(self):
        with self.assertRaises(ValueError):
            vdc.build_visual_diversity_coverage({"assets": [{"scenes": []}]})


class WriterAndCliTest(unittest.TestCase):
    def test_writer_and_cli_emit_coverage_artifact(self):
        d = Path(tempfile.mkdtemp())
        source = d / "project_material_map.json"
        source.write_text(json.dumps(_project_map([{"visual_family": "a"}])), encoding="utf-8")
        out = d / "visual_diversity_coverage.json"
        args = types.SimpleNamespace(
            project_map=str(source), out=str(out), min_visual_family_coverage=0.7)
        cmd_visual_diversity_coverage(args)
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["artifact_role"], "visual_diversity_coverage")
        self.assertTrue(written["ready_for_vd2"])


if __name__ == "__main__":
    unittest.main()
