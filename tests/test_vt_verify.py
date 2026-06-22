import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
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

    def test_duration_fit_uses_timeline_out_for_xfade_total(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "final.mp4"
            video.write_bytes(b"video")
            edit_log = {"clips": [
                {"segment": 1, "duration_sec": 2.0, "timeline_in_sec": 0.0, "timeline_out_sec": 2.0},
                {"segment": 2, "duration_sec": 2.0, "timeline_in_sec": 1.5, "timeline_out_sec": 3.5,
                 "transition": "xfade", "transition_duration_sec": 0.5},
            ]}

            with patch("video_pipeline_core.vt_verify._audio_duration", return_value=3.5):
                result = vt_verify._verify_duration_fit({}, edit_log, video_path=str(video))

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["issues"], [])

    def test_target_duration_fit_compares_video_to_brief_target(self):
        with patch("video_pipeline_core.vt_verify._audio_duration", return_value=48.0):
            result = vt_verify._verify_target_duration_fit(
                {"target_length": "3 minutes"},
                video_path="final.mp4",
            )

        self.assertLess(result["score"], 80)
        self.assertEqual(result["fix_target"], "director")
        self.assertEqual(result["target_duration_sec"], 180.0)
        self.assertEqual(result["actual_duration_sec"], 48.0)

    def test_subtitle_readability_flags_long_rendered_lines(self):
        with tempfile.TemporaryDirectory() as d:
            srt_path = Path(d) / "subtitles.srt"
            srt_path.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n"
                "This subtitle line is intentionally far too long for a safe readable video subtitle line\n",
                encoding="utf-8",
            )

            result = vt_verify._verify_subtitle_readability(srt_path, max_chars_per_line=24)

        self.assertLess(result["score"], 80)
        self.assertEqual(result["fix_target"], "subtitle")

    def test_content_alignment_surfaces_vlm_no(self):
        result = vt_verify._verify_content_alignment({
            "segments": [{"segment": 9, "vlm_verdict": "no", "reason": "wrong closing shot"}]
        })

        self.assertLess(result["score"], 80)
        self.assertEqual(result["fix_target"], "curator")
        self.assertIn("seg9", result["note"])

    def test_content_alignment_reads_content_qa_low_segments(self):
        result = vt_verify._verify_content_alignment({
            "segments": [{"segment": 3, "score": 42, "image_desc": "unrelated street"}]
        })

        self.assertLess(result["score"], 80)
        self.assertEqual(result["fix_target"], "curator")
        self.assertIn("seg3", result["note"])

    def test_content_alignment_reads_material_coverage_gaps(self):
        result = vt_verify._verify_content_alignment({
            "artifact_role": "material_coverage_map",
            "gaps": [{"segment": 4, "reason": "no matching ceremony footage"}],
        })

        self.assertLess(result["score"], 80)
        self.assertEqual(result["fix_target"], "curator")
        self.assertIn("seg4", result["note"])


class RuntimeHeartbeatTest(unittest.TestCase):
    def test_heartbeat_line_includes_node_and_segment_progress(self):
        from video_pipeline_core.runtime_orchestrator import format_heartbeat

        line = format_heartbeat("render", "rendered mv segment", segment=9, total=17)

        self.assertEqual(line, "[runtime] [heartbeat][render][seg 9/17] rendered mv segment")


if __name__ == "__main__":
    unittest.main()
