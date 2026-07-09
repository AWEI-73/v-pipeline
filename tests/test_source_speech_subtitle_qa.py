import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.source_speech_subtitle_qa import evaluate_source_speech_subtitle_qa, write_source_speech_subtitle_qa_for_run


class SourceSpeechSubtitleQATest(unittest.TestCase):
    def test_missing_later_subtitle_coverage_blocks(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [{"start_sec": 24.2, "end_sec": 31.0, "text": "early cue"}],
            "human_transcript_present": True,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_later_subtitle_coverage_missing")

    def test_placeholder_review_marker_subtitles_block(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.0, "end_sec": 32.0, "text": "review marker"},
                {"start_sec": 32.0, "end_sec": 42.0, "text": "coverage marker"},
            ],
            "subtitle_source": "asr",
            "human_transcript_present": False,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_placeholder_subtitles")
        self.assertEqual(result["next_action"], "human_transcript_review")

    def test_subtitle_outside_source_speech_segment_blocks(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [{"start_sec": 21.0, "end_sec": 25.0, "text": "outside cue"}],
            "human_transcript_present": True,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_subtitle_timing_outside_segment")

    def test_asr_without_human_transcript_marks_human_review_needed_but_honest(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                {"start_sec": 32.2, "end_sec": 41.7, "text": "later cue"},
            ],
            "subtitle_source": "asr",
            "human_transcript_present": False,
        })

        self.assertTrue(result["pass"], result)
        self.assertTrue(result["needs_human_transcript_review"])
        self.assertEqual(result["warnings"][0]["rule"], "needs_human_transcript_review")

    def test_valid_human_transcript_coverage_passes(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                {"start_sec": 32.2, "end_sec": 41.8, "text": "later cue"},
            ],
            "human_transcript_present": True,
        })

        self.assertTrue(result["pass"], result)
        self.assertFalse(result["needs_human_transcript_review"])

    def test_write_for_run_reads_artifact_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source_speech_subtitle_evidence.json").write_text(
                json.dumps({
                    "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
                    "subtitle_cues": [
                        {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                        {"start_sec": 32.2, "end_sec": 41.8, "text": "later cue"},
                    ],
                    "human_transcript_present": True,
                }),
                encoding="utf-8",
            )

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "source_speech_subtitle_qa.json").exists())


if __name__ == "__main__":
    unittest.main()
