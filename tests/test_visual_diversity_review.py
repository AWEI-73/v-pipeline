import json
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core import visual_diversity_coverage as vdc
from video_pipeline_core import visual_diversity_review as vdr
from video_tools import cmd_visual_diversity_review


def _project():
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [
            {"asset_id": "a", "source": "a.mp4", "scenes": [{}, {}]},
            {"asset_id": "b", "source": "b.jpg", "scenes": [{}]},
        ],
    }


def _review(scenes):
    return {
        "artifact_role": "visual_diversity_review",
        "version": 1,
        "reviewer": "agent-a",
        "at": "2026-06-15T15:30:00+08:00",
        "scenes": scenes,
    }


class ApplyReviewTest(unittest.TestCase):
    def test_applies_shallow_labels_and_lineage_without_mutating_input(self):
        source = _project()
        result = vdr.apply_visual_diversity_review(source, _review([
            {"asset_id": "a", "scene_index": 1, "visual_family": "classroom",
             "angle_scale": "wide", "action_family": "lecture", "subject": "students"},
        ]))
        scene = result["project_map"]["assets"][0]["scenes"][1]
        self.assertTrue(result["ok"])
        self.assertEqual(scene["visual_family"], "classroom")
        self.assertEqual(scene["angle_scale"], "wide")
        self.assertEqual(
            scene["visual_diversity_lineage"],
            [{"reviewer": "agent-a", "at": "2026-06-15T15:30:00+08:00",
              "axes": ["action_family", "angle_scale", "subject", "visual_family"]}],
        )
        self.assertNotIn("visual_family", source["assets"][0]["scenes"][1])

    def test_unknown_or_duplicate_scene_reference_fails_closed(self):
        for scenes in (
            [{"asset_id": "missing", "scene_index": 0, "visual_family": "x"}],
            [{"asset_id": "a", "scene_index": 9, "visual_family": "x"}],
            [{"asset_id": "a", "scene_index": 0, "visual_family": "x"},
             {"asset_id": "a", "scene_index": 0, "angle_scale": "wide"}],
        ):
            result = vdr.apply_visual_diversity_review(_project(), _review(scenes))
            self.assertFalse(result["ok"])
            self.assertIsNone(result["project_map"])

    def test_invalid_review_metadata_and_label_shapes_fail_closed(self):
        cases = [
            {**_review([]), "reviewer": ""},
            {**_review([]), "at": 123},
            _review([{"asset_id": "a", "scene_index": True, "visual_family": "x"}]),
            _review([{"asset_id": [], "scene_index": 0, "visual_family": "x"}]),
            _review([{"asset_id": "a", "scene_index": [], "visual_family": "x"}]),
            _review([{"asset_id": "a", "scene_index": 0, "angle_scale": "extreme-wide"}]),
            _review([{"asset_id": "a", "scene_index": 0, "visual_family": " "}]),
            _review([{"asset_id": "a", "scene_index": 0}]),
        ]
        for review in cases:
            result = vdr.apply_visual_diversity_review(_project(), review)
            self.assertFalse(result["ok"])
            self.assertIsNone(result["project_map"])

    def test_unreviewed_scenes_remain_unlabeled(self):
        result = vdr.apply_visual_diversity_review(_project(), _review([
            {"asset_id": "b", "scene_index": 0, "visual_family": "group_photo",
             "angle_scale": "wide"},
        ]))
        self.assertTrue(result["ok"])
        self.assertEqual(result["applied_scene_count"], 1)
        self.assertEqual(result["project_map"]["assets"][0]["scenes"], [{}, {}])

    def test_malformed_existing_lineage_fails_closed(self):
        source = _project()
        source["assets"][0]["scenes"][0]["visual_diversity_lineage"] = {}
        result = vdr.apply_visual_diversity_review(source, _review([
            {"asset_id": "a", "scene_index": 0, "visual_family": "classroom"},
        ]))
        self.assertFalse(result["ok"])
        self.assertIsNone(result["project_map"])

    def test_malformed_project_map_shapes_fail_closed_without_crash(self):
        cases = [
            {**_project(), "assets": {}},
            {**_project(), "assets": [123]},
            {**_project(), "assets": [{"asset_id": "", "scenes": []}]},
            {**_project(), "assets": [
                {"asset_id": "a", "scenes": []},
                {"asset_id": "a", "scenes": []},
            ]},
            {**_project(), "assets": [{"asset_id": "a", "scenes": {}}]},
            {**_project(), "assets": [{"asset_id": "a", "scenes": [123]}]},
        ]
        for project in cases:
            result = vdr.apply_visual_diversity_review(project, _review([]))
            self.assertFalse(result["ok"])
            self.assertIsNone(result["project_map"])

    def test_baseline_review_does_not_bypass_independent_consistency_gate(self):
        result = vdr.apply_visual_diversity_review(_project(), _review([
            {"asset_id": "a", "scene_index": 0, "visual_family": "classroom",
             "angle_scale": "wide"},
            {"asset_id": "a", "scene_index": 1, "visual_family": "practice",
             "angle_scale": "close"},
            {"asset_id": "b", "scene_index": 0, "visual_family": "group_photo",
             "angle_scale": "wide"},
        ]))
        coverage = vdc.build_visual_diversity_coverage(
            result["project_map"], min_consistency_scenes=2)
        self.assertFalse(coverage["ready_for_vd2"])
        self.assertIn("consistency_evidence_missing",
                      coverage["decision"]["blocking_reasons"])


class WriterAndCliTest(unittest.TestCase):
    def test_writer_and_cli_write_reviewed_project_map(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            project = d / "project.json"
            review = d / "review.json"
            out = d / "reviewed.json"
            project.write_text(json.dumps(_project()), encoding="utf-8")
            review.write_text(json.dumps(_review([
                {"asset_id": "a", "scene_index": 0, "visual_family": "classroom",
                 "angle_scale": "medium"},
            ])), encoding="utf-8")
            args = types.SimpleNamespace(project_map=str(project), review=str(review), out=str(out))
            cmd_visual_diversity_review(args)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["assets"][0]["scenes"][0]["visual_family"], "classroom")

    def test_writer_failure_does_not_create_or_replace_output(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            project = d / "project.json"
            review = d / "review.json"
            out = d / "reviewed.json"
            project.write_text(json.dumps(_project()), encoding="utf-8")
            review.write_text(json.dumps(_review([
                {"asset_id": "missing", "scene_index": 0, "visual_family": "x"},
            ])), encoding="utf-8")
            out.write_text("OLD", encoding="utf-8")
            with self.assertRaises(ValueError):
                vdr.write_visual_diversity_review(project, review, out)
            self.assertEqual(out.read_text(encoding="utf-8"), "OLD")


if __name__ == "__main__":
    unittest.main()
