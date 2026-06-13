import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import verify_evidence


TIMELINE = {"clips": [
    {"segment": 1, "timeline_in_sec": 0, "timeline_out_sec": 3, "duration_sec": 3},
    {"segment": 1, "timeline_in_sec": 3, "timeline_out_sec": 5, "duration_sec": 2},
    {"segment": 2, "timeline_in_sec": 5, "timeline_out_sec": 9, "duration_sec": 4,
     "keep_audio": True},
    {"segment": 3, "timeline_in_sec": 9, "timeline_out_sec": 11, "duration_sec": 2,
     "adjustment_reason": "motion_phase"},
]}


class VerifyEvidencePlanTest(unittest.TestCase):
    def test_builds_four_layer_plan(self):
        plan = verify_evidence.build_evidence_plan(TIMELINE)
        self.assertEqual(plan["artifact_role"], "verify_evidence_plan")
        self.assertEqual(plan["overview"]["sample_count"], 48)
        self.assertEqual(len(plan["chapters"]), 3)
        self.assertEqual([x["segment"] for x in plan["critical_segments"]], [2, 3])
        self.assertEqual(plan["rhythm_strip"]["clip_count"], 4)

    def test_chapter_timestamps_stay_inside_chapter(self):
        plan = verify_evidence.build_evidence_plan(TIMELINE, chapter_samples=12)
        chapter = plan["chapters"][1]
        self.assertTrue(all(5 <= ts <= 9 for ts in chapter["timestamps"]))

    def test_rhythm_strip_writes_svg(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rhythm.svg"
            meta = verify_evidence.write_rhythm_strip(TIMELINE, path)
            self.assertTrue(path.exists())
            self.assertEqual(meta["clip_count"], 4)
            self.assertIn("<svg", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
