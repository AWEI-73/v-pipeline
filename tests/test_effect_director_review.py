import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_director_review import evaluate_effect_director_review, write_effect_director_review_for_run


class EffectDirectorReviewTest(unittest.TestCase):
    def test_metadata_only_review_cannot_pass(self):
        result = evaluate_effect_director_review({
            "review_basis": "metadata_only",
            "effects": [{"effect_id": "opening_title"}],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "effect_review_requires_visual_evidence")

    def test_lingering_overlay_blocks(self):
        result = evaluate_effect_director_review({
            "review_basis": "frame_sequence",
            "frame_sequence": ["before.jpg", "active.jpg", "after.jpg"],
            "effects": [{"effect_id": "opening_title"}],
            "findings": [{"severity": "blocking", "rule": "lingering_overlay", "message": "title remains after section"}],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "lingering_overlay")

    def test_valid_frame_sequence_review_passes(self):
        result = evaluate_effect_director_review({
            "review_basis": "frame_sequence",
            "frame_sequence": ["before.jpg", "active.jpg", "after.jpg"],
            "effects": [{"effect_id": "opening_title"}],
            "checks": {
                "lingering_overlays": "pass",
                "subject_obstruction": "pass",
                "style_match": "pass",
                "title_disappearance": "pass",
            },
            "findings": [],
        })

        self.assertTrue(result["pass"], result)

    def test_write_for_run_reads_packet_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "effect_director_review_packet.json").write_text(
                json.dumps({
                    "review_basis": "frame_sequence",
                    "frame_sequence": ["before.jpg", "active.jpg", "after.jpg"],
                    "effects": [{"effect_id": "opening_title"}],
                    "checks": {"lingering_overlays": "pass", "subject_obstruction": "pass", "style_match": "pass", "title_disappearance": "pass"},
                    "findings": [],
                }),
                encoding="utf-8",
            )

            report = write_effect_director_review_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "effect_director_review.json").exists())


if __name__ == "__main__":
    unittest.main()
