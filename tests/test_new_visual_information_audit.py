import unittest

from video_pipeline_core.new_visual_information_audit import audit_new_visual_information


class NewVisualInformationAuditTest(unittest.TestCase):
    def test_distinct_scene_ids_pass(self):
        result = audit_new_visual_information({"clips": [
            {"scene_id": "a:0", "duration_sec": 2},
            {"scene_id": "a:1", "duration_sec": 2},
            {"scene_id": "b:0", "duration_sec": 2},
        ]}, min_new_visual_ratio=0.6, max_repeated_hold_sec=3)
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["new_visual_information_ratio"], 1.0)

    def test_repeated_scene_and_long_hold_fail(self):
        result = audit_new_visual_information({"clips": [
            {"scene_id": "a:0", "duration_sec": 2},
            {"scene_id": "a:0", "duration_sec": 4},
            {"scene_id": "a:0", "duration_sec": 5},
        ]}, min_new_visual_ratio=0.6, max_repeated_hold_sec=3)
        self.assertFalse(result["pass"])
        self.assertLess(result["metrics"]["new_visual_information_ratio"], 0.6)
        self.assertGreater(result["metrics"]["repeated_visual_hold_sec"], 3)
        self.assertEqual(result["next_action"], "curator")

    def test_legacy_timeline_uses_source_start_to_distinguish_windows(self):
        result = audit_new_visual_information({"clips": [
            {"source_path": "a.mp4", "source_in_sec": 0, "duration_sec": 2},
            {"source_path": "a.mp4", "source_in_sec": 5, "duration_sec": 2},
            {"source_path": "a.mp4", "source_in_sec": 10, "duration_sec": 2},
        ]}, min_new_visual_ratio=0.6, max_repeated_hold_sec=3)
        self.assertTrue(result["pass"])


if __name__ == "__main__":
    unittest.main()
