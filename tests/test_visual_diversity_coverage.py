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

    def test_visual_family_alone_does_not_allow_vd2(self):
        report = vdc.build_visual_diversity_coverage(
            _project_map([
                {"visual_family": "a"},
                {"visual_family": "b"},
                {"visual_family": "c"},
            ]),
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertIn("angle_scale_coverage_below_threshold",
                      report["decision"]["blocking_reasons"])

    def test_missing_consistency_evidence_blocks_vd2(self):
        report = vdc.build_visual_diversity_coverage(
            _project_map([
                {"visual_family": "a", "angle_scale": "wide"},
                {"visual_family": "b", "angle_scale": "close"},
            ]),
            min_consistency_scenes=2,
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertIn("consistency_evidence_missing",
                      report["decision"]["blocking_reasons"])

    def test_coverage_and_independent_consistency_allow_vd2(self):
        baseline = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        independent_review = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        report = vdc.build_visual_diversity_coverage(
            baseline,
            consistency_reviews=[independent_review],
            min_consistency_scenes=2,
            min_consistency_ratio=0.7,
        )
        self.assertTrue(report["ready_for_vd2"])
        self.assertEqual(report["consistency"]["comparable_scene_count"], 2)
        self.assertEqual(report["consistency"]["agreement_ratio"], 1.0)

    def test_too_few_or_inconsistent_review_samples_block_vd2(self):
        baseline = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        one_labeled = _project_map([
            {"visual_family": "x", "angle_scale": "medium"},
            {},
        ])
        report = vdc.build_visual_diversity_coverage(
            baseline,
            consistency_reviews=[one_labeled],
            min_consistency_scenes=2,
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertIn("visual_family_consistency_sample_below_threshold",
                      report["decision"]["blocking_reasons"])

    def test_each_required_axis_needs_independent_consistency_evidence(self):
        baseline = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        family_only_review = _project_map([
            {"visual_family": "a"},
            {"visual_family": "b"},
        ])
        report = vdc.build_visual_diversity_coverage(
            baseline,
            consistency_reviews=[family_only_review],
            min_consistency_scenes=2,
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertIn("angle_scale_consistency_sample_below_threshold",
                      report["decision"]["blocking_reasons"])

    def test_each_required_axis_must_reach_consistency_ratio(self):
        baseline = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        bad_angle_review = _project_map([
            {"visual_family": "a", "angle_scale": "close"},
            {"visual_family": "b", "angle_scale": "wide"},
        ])
        report = vdc.build_visual_diversity_coverage(
            baseline,
            consistency_reviews=[bad_angle_review],
            min_consistency_scenes=2,
        )
        self.assertFalse(report["ready_for_vd2"])
        self.assertIn("angle_scale_consistency_ratio_below_threshold",
                      report["decision"]["blocking_reasons"])

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
            project_map=str(source), out=str(out), min_visual_family_coverage=0.7,
            min_angle_scale_coverage=0.6, consistency_review=[],
            min_consistency_ratio=0.7, min_consistency_scenes=10)
        cmd_visual_diversity_coverage(args)
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["artifact_role"], "visual_diversity_coverage")
        self.assertFalse(written["ready_for_vd2"])

    def test_writer_loads_independent_review_maps(self):
        d = Path(tempfile.mkdtemp())
        baseline = _project_map([
            {"visual_family": "a", "angle_scale": "wide"},
            {"visual_family": "b", "angle_scale": "close"},
        ])
        source = d / "project_material_map.json"
        review = d / "reviewer_b.json"
        out = d / "visual_diversity_coverage.json"
        source.write_text(json.dumps(baseline), encoding="utf-8")
        review.write_text(json.dumps(baseline), encoding="utf-8")
        report = vdc.write_visual_diversity_coverage(
            source, out, consistency_review_paths=[review],
            min_consistency_scenes=2)
        self.assertTrue(report["ready_for_vd2"])


if __name__ == "__main__":
    unittest.main()
