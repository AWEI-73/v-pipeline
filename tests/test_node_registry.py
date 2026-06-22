import unittest

from video_pipeline_core.node_registry import (
    NODE_ORDER,
    NODE_REGISTRY,
    verify_material_coverage,
    verify_revision,
)


class VisualJudgeNodeTest(unittest.TestCase):
    def test_visual_judge_is_between_timeline_and_editor_review(self):
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10") + 1], "10.5")
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10.5") + 1], "11")
        self.assertIn("visual_review_request.json", NODE_REGISTRY["10.5"]["outputs"])
        self.assertIn("visual_review_verdict.json", NODE_REGISTRY["10.5"]["outputs"])


class MaterialCoverageNodeTest(unittest.TestCase):
    def test_stock_first_empty_picks_do_not_pass_as_optional(self):
        status, reason = verify_material_coverage("", {
            "contract": {
                "material_source_mode": "stock_first",
                "segments": [{"segment": 1, "visual_desc": "sunrise establishing shot"}],
            },
            "material_coverage": {
                "artifact_role": "material_coverage_map",
                "version": 1,
                "assignments": [{
                    "segment": 1,
                    "visual_desc": "sunrise establishing shot",
                    "picks": [],
                    "gap": True,
                }],
                "gaps": [{"segment": 1, "must_include": True}],
                "covered": [],
                "weak": [],
                "missing": [{"segment": 1, "must_include": True}],
                "blocking": [{"segment": 1, "must_include": True}],
            },
        }, {})

        self.assertEqual(status, "warn")
        self.assertIn("stock_first", reason)
        self.assertIn("empty picks", reason)

    def test_stock_first_with_segment_picks_passes(self):
        status, reason = verify_material_coverage("", {
            "contract": {
                "material_source_mode": "stock_first",
                "segments": [{"segment": 1, "visual_desc": "sunrise establishing shot"}],
            },
            "material_coverage": {
                "artifact_role": "material_coverage_map",
                "version": 1,
                "assignments": [{
                    "segment": 1,
                    "visual_desc": "sunrise establishing shot",
                    "picks": [{"path": "seg1_stock.mp4", "score": 1.0}],
                    "gap": False,
                }],
                "gaps": [],
                "covered": [{"segment": 1}],
                "weak": [],
                "missing": [],
                "blocking": [],
            },
        }, {})

        self.assertEqual(status, "done")
        self.assertIn("Material coverage map exists", reason)


class RevisionNodeTest(unittest.TestCase):
    def test_revision_node_is_labeled_as_brownfield_edit_route(self):
        self.assertEqual(NODE_REGISTRY["14"]["label"], "Brownfield Edit")
        self.assertIn("local patch", NODE_REGISTRY["14"]["description"])
        self.assertIn("brownfield-edit", NODE_REGISTRY["14"]["skill"])

    def test_revision_node_declares_effect_revision_request_output(self):
        self.assertIn("effect_revision_request.json", NODE_REGISTRY["14"]["outputs"])
        self.assertIn("effect_recipe_patch.json", NODE_REGISTRY["14"]["outputs"])

    def test_revision_node_prefers_pending_effect_revision_request(self):
        status, reason = verify_revision("", {
            "light_effects_baseline_review": {
                "status": "gaps_found",
                "metrics": {"gap_count": 2},
            },
            "effect_revision_request": {
                "status": "pending",
                "summary": {"request_count": 2},
            },
        }, {})

        self.assertEqual(status, "warn")
        self.assertIn("2 effect revision request", reason)

    def test_revision_node_prefers_pending_effect_recipe_patch(self):
        status, reason = verify_revision("", {
            "effect_revision_request": {
                "status": "pending",
                "summary": {"request_count": 2},
            },
            "effect_recipe_patch": {
                "status": "pending",
                "summary": {"patch_count": 2},
            },
        }, {})

        self.assertEqual(status, "warn")
        self.assertIn("2 effect recipe patch", reason)


if __name__ == "__main__":
    unittest.main()
