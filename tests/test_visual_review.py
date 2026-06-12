import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import visual_review


class VisualReviewTest(unittest.TestCase):
    def test_request_groups_all_stock_clips_into_one_gate(self):
        request = visual_review.build_request([
            {
                "segment": 2,
                "clip": "mvstock_2.mp4",
                "montage": "visual_review/seg2.jpg",
                "verify_desc": "workers installing cable",
                "candidate_windows": [{"start": 1.0, "end": 3.0}],
            },
            {
                "segment": 3,
                "clip": "mvstock_3.mp4",
                "montage": "visual_review/seg3.jpg",
                "verify_desc": "team celebration",
                "candidate_windows": [{"start": 4.0, "end": 6.0}],
            },
        ])

        self.assertEqual(request["artifact_role"], "visual_review_request")
        self.assertEqual(request["next_action"], "await_visual_review")
        self.assertEqual(len(request["clips"]), 2)

    def test_verdict_map_validates_and_indexes_segments(self):
        verdict = {
            "clips": [{
                "segment": 2,
                "accept": True,
                "picked_windows": [{"start": 1.0, "end": 3.0}],
                "notes": "best evidence",
            }],
        }

        indexed = visual_review.verdict_by_segment(verdict)

        self.assertEqual(indexed[2]["picked_windows"][0], {"start": 1.0, "end": 3.0})

    def test_verdict_rejects_invalid_window(self):
        with self.assertRaises(ValueError):
            visual_review.verdict_by_segment({
                "clips": [{
                    "segment": 2,
                    "accept": True,
                    "picked_windows": [{"start": 3.0, "end": 1.0}],
                }],
            })

    def test_write_request_includes_verdict_template(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "visual_review_request.json"
            visual_review.write_request([{
                "segment": 2,
                "clip": "mvstock_2.mp4",
                "montage": "visual_review/seg2.jpg",
                "verify_desc": "workers",
                "candidate_windows": [{"start": 1.0, "end": 3.0}],
            }], out)
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(payload["verdict_template"]["clips"][0]["segment"], 2)
        self.assertIsNone(payload["verdict_template"]["clips"][0]["accept"])


if __name__ == "__main__":
    unittest.main()
