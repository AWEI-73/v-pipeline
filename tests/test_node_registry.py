import unittest

from video_pipeline_core.node_registry import NODE_ORDER, NODE_REGISTRY


class VisualJudgeNodeTest(unittest.TestCase):
    def test_visual_judge_is_between_timeline_and_editor_review(self):
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10") + 1], "10.5")
        self.assertEqual(NODE_ORDER[NODE_ORDER.index("10.5") + 1], "11")
        self.assertIn("visual_review_request.json", NODE_REGISTRY["10.5"]["outputs"])
        self.assertIn("visual_review_verdict.json", NODE_REGISTRY["10.5"]["outputs"])


if __name__ == "__main__":
    unittest.main()
