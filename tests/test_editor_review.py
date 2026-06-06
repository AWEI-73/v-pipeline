"""editor_review — Node 11/12 clip checks for V3 P3."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import editor_review as er


class EditorReviewTest(unittest.TestCase):
    def test_review_timeline_passes_clean_clips(self):
        timeline = {"clips": [
            {"segment": 1, "source_path": "a.mp4", "start_sec": 0, "end_sec": 3,
             "duration_sec": 3, "target_duration_sec": 3, "timeline_in_sec": 0,
             "timeline_out_sec": 3},
            {"segment": 2, "source_path": "b.mp4", "start_sec": 10, "end_sec": 12,
             "duration_sec": 2, "target_duration_sec": 2, "timeline_in_sec": 3,
             "timeline_out_sec": 5},
        ]}
        review = er.review_timeline_build(timeline)
        self.assertEqual(review["status"], "pass")
        self.assertEqual(review["clip_checks"][0]["status"], "pass")
        self.assertTrue(review["clip_checks"][0]["checks"]["duration_match"])

    def test_review_timeline_flags_overlap_duration_and_stitch_gap(self):
        timeline = {"clips": [
            {"segment": 1, "source_path": "a.mp4", "start_sec": 0, "end_sec": 4,
             "duration_sec": 4, "target_duration_sec": 3, "timeline_in_sec": 0,
             "timeline_out_sec": 4},
            {"segment": 2, "source_path": "a.mp4", "start_sec": 3, "end_sec": 5,
             "duration_sec": 2, "target_duration_sec": 2, "timeline_in_sec": 4,
             "timeline_out_sec": 6},
            {"segment": 3, "source_path": "a.mp4", "start_sec": 20, "end_sec": 21,
             "duration_sec": 1, "target_duration_sec": 1, "timeline_in_sec": 6,
             "timeline_out_sec": 7, "is_stitched": True, "stitch_gap_sec": 4.0},
        ]}
        review = er.review_timeline_build(timeline, duration_tolerance_sec=0.25,
                                          max_stitch_gap_sec=2.0)
        findings = [f["check"] for c in review["clip_checks"] for f in c["findings"]]
        self.assertEqual(review["status"], "fail")
        self.assertIn("duration_match", findings)
        self.assertIn("overlap_free", findings)
        self.assertIn("duplicate_footage", findings)
        self.assertIn("stitch_gap_ok", findings)

    def test_write_editor_review(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "editor_review.json"
            result = er.write_editor_review({"clips": []}, p)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(result["editor_review"], str(p))
            self.assertEqual(saved["editor_review_version"], 1)


if __name__ == "__main__":
    unittest.main()
