import unittest
import tempfile
from pathlib import Path
from video_pipeline_core import vt_verify


class VtVerifyTest(unittest.TestCase):
    def test_verify_script_coverage_with_clips(self):
        # Script expects segment 1 and 2
        script = [
            {"segment": 1, "text": "Hello"},
            {"segment": 2, "text": "World"}
        ]
        # Edit log has clips instead of segments
        edit_log_clips = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4"},
                {"segment": 2, "source_path": "b.mp4"}
            ]
        }
        res = vt_verify._verify_script_coverage(script, edit_log_clips)
        self.assertEqual(res["score"], 100)
        self.assertIsNone(res["fix_target"])

        # Missing segment 2
        edit_log_missing = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4"}
            ]
        }
        res_missing = vt_verify._verify_script_coverage(script, edit_log_missing)
        self.assertEqual(res_missing["score"], 50)
        self.assertEqual(res_missing["fix_target"], "editor")

    def test_verify_subtitle_accuracy_extracts_cjk_fields(self):
        # Script uses CJK text layer subtitle
        script = [
            {"segment": 1, "subtitle": "我們今天去學習"},
            {"segment": 2, "subtitle": "現場操作"}
        ]
        with tempfile.TemporaryDirectory() as d:
            srt_path = Path(d) / "subtitles.srt"
            srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\n我們今天去學習\n\n2\n00:00:02,000 --> 00:00:04,000\n現場操作\n", encoding="utf-8")

            res = vt_verify._verify_subtitle_accuracy(script, srt_path)
            self.assertGreaterEqual(res["score"], 90)
            self.assertIsNone(res["fix_target"])

    def test_verify_subtitle_accuracy_passes_empty_script_with_music_srt(self):
        # Script has no text fields
        script = [
            {"segment": 1},
            {"segment": 2}
        ]
        with tempfile.TemporaryDirectory() as d:
            srt_path = Path(d) / "subtitles.srt"
            # SRT has [Music]
            srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\n[Music]\n", encoding="utf-8")

            res = vt_verify._verify_subtitle_accuracy(script, srt_path)
            self.assertEqual(res["score"], 100)
            self.assertIsNone(res["fix_target"])

    def test_verify_subtitle_accuracy_fails_empty_script_with_unexpected_subtitles(self):
        script = [
            {"segment": 1},
            {"segment": 2}
        ]
        with tempfile.TemporaryDirectory() as d:
            srt_path = Path(d) / "subtitles.srt"
            srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\n有字幕出現了\n", encoding="utf-8")

            res = vt_verify._verify_subtitle_accuracy(script, srt_path)
            self.assertEqual(res["score"], 0)
            self.assertEqual(res["fix_target"], "subtitle")


if __name__ == "__main__":
    unittest.main()
