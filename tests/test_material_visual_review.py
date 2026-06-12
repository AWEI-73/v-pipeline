import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import curator


class MaterialVisualReviewTest(unittest.TestCase):
    def test_build_request_uses_montage_for_video_and_photo_as_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_grid(video, out, **kwargs):
                calls.append((video, str(out)))
                return {"grid_path": str(out), "samples": [{"timestamp_sec": 1.0}]}

            request = curator.build_material_review_request(
                {"files": [
                    {"id": "f1", "type": "video", "path": "clip.mp4"},
                    {"id": "f2", "type": "photo", "path": "photo.jpg", "display_path": "display.jpg"},
                ]},
                tmp,
                _gridfn=fake_grid,
            )

        self.assertEqual(calls[0][0], "clip.mp4")
        self.assertIn("material_review", request["assets"][0]["montage"])
        self.assertEqual(request["assets"][1]["montage"], "display.jpg")
        self.assertEqual(request["next_action"], "await_material_visual_review")

    def test_apply_verdict_updates_caption_and_agent_lineage(self):
        db = {"files": [{"id": "f1", "type": "video", "path": "clip.mp4"}]}
        result = curator.apply_material_review_verdict(db, {
            "assets": [{"id": "f1", "caption": "A team meets around a table", "notes": "usable"}]
        })

        self.assertEqual(result["files"][0]["vlm_caption"], "A team meets around a table")
        self.assertEqual(result["files"][0]["caption_source"], "agent_visual_review")
        self.assertEqual(result["files"][0]["caption_notes"], "usable")


if __name__ == "__main__":
    unittest.main()
