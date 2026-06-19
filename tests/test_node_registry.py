import unittest

from video_pipeline_core.node_registry import NODE_ORDER, NODE_REGISTRY, verify_revision


class VisualJudgeNodeTest(unittest.TestCase):
    def test_visual_judge_is_between_timeline_and_editor_review(self):
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10") + 1], "10.5")
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10.5") + 1], "11")
        self.assertIn("visual_review_request.json", NODE_REGISTRY["10.5"]["outputs"])
        self.assertIn("visual_review_verdict.json", NODE_REGISTRY["10.5"]["outputs"])


class RevisionNodeTest(unittest.TestCase):
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
