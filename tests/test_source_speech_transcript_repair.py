import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from video_pipeline_core.agent_transcript_repair import (
    build_agent_transcript_repair,
    write_agent_transcript_repair_for_run,
)
from video_pipeline_core.human_transcript_review_decision import (
    build_human_transcript_review_decision,
)
from tools.agent_transcript_repair import main as agent_transcript_repair_main


class SourceSpeechTranscriptRepairTest(unittest.TestCase):
    def test_known_asr_errors_are_suggested_but_not_approved(self):
        result = build_agent_transcript_repair({
            "source_type": "source_speech",
            "segments": [
                {
                    "id": "cue01",
                    "start_sec": 1.0,
                    "end_sec": 3.0,
                    "text": "第六四七七楊成班學人們順利節",
                }
            ],
        })

        self.assertEqual(result["artifact_role"], "agent_transcript_repair_suggestions")
        self.assertTrue(result["requires_human_transcript_review"])
        self.assertEqual(result["approval_status"], "agent_draft_not_approved")
        suggestion = result["suggestions"][0]
        self.assertEqual(suggestion["source_type"], "source_speech")
        self.assertEqual(suggestion["original_asr"], "第六四七七楊成班學人們順利節")
        self.assertIn("第六十七期養成班學員們", suggestion["suggested_text"])
        self.assertIn("順利結訓", suggestion["suggested_text"])
        self.assertTrue(suggestion["uncertain_spans"])

    def test_asr_subtitle_route_writes_suggestions_and_draft_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "asr_raw_transcript.json").write_text(
                json.dumps(
                    {
                        "source_type": "generated_subtitle",
                        "segments": [
                            {
                                "id": "cue01",
                                "start_sec": 0.0,
                                "end_sec": 2.5,
                                "text": "五個班院成成",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = write_agent_transcript_repair_for_run(root)

            self.assertTrue((root / "agent_transcript_repair_suggestions.json").exists())
            self.assertTrue((root / "subtitles.draft.srt").exists())
            self.assertTrue(result["requires_human_transcript_review"])
            self.assertEqual(result["approval_status"], "agent_draft_not_approved")
            draft = (root / "subtitles.draft.srt").read_text(encoding="utf-8")
            self.assertIn("五個半月養成", draft)

    def test_nested_probe_segments_are_adapted_and_write_a_draft_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source_speech_asr_probe.json").write_text(
                json.dumps(
                    {
                        "features": {
                            "vocal_analysis": {
                                "segments": [
                                    {"id": "cue01", "start": 0.0, "end": 1.5, "text": "第一句"},
                                    {"id": "cue02", "start": 1.5, "end": 3.0, "text": "第二句"},
                                ]
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = write_agent_transcript_repair_for_run(root)

            self.assertEqual(result["suggestion_count"], 2)
            self.assertEqual(len(json.loads((root / "asr_raw_transcript.json").read_text(encoding="utf-8"))["segments"]), 2)
            self.assertTrue((root / "subtitles.draft.srt").read_text(encoding="utf-8").strip())

    def test_require_cues_is_opt_in_and_fails_closed_for_zero_cues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(StringIO()):
                legacy_exit = agent_transcript_repair_main(["--run", str(root)])
                required_exit = agent_transcript_repair_main(["--run", str(root), "--require-cues"])

            self.assertEqual(legacy_exit, 0)
            self.assertNotEqual(required_exit, 0)

    def test_all_asr_derived_source_types_remain_human_review_drafts(self):
        for source_type in ("source_speech", "voiceover", "generated_subtitle", "interview", "original_audio"):
            with self.subTest(source_type=source_type):
                result = build_agent_transcript_repair({
                    "source_type": source_type,
                    "segments": [{"id": "cue01", "start_sec": 0.0, "end_sec": 1.0, "text": "raw cue"}],
                })

                self.assertEqual(result["suggestions"][0]["source_type"], source_type)
                self.assertTrue(result["suggestions"][0]["requires_human_transcript_review"])
                self.assertEqual(result["suggestions"][0]["approval_status"], "agent_draft_not_approved")

    def test_non_human_transcript_approval_fails_closed(self):
        with self.assertRaises(ValueError):
            build_human_transcript_review_decision(
                {
                    "decision": "approved",
                    "reviewer": "agent",
                    "reviewed_draft": "subtitles.draft.srt",
                    "reviewed_cue_ids": ["cue01"],
                }
            )

    def test_human_approval_requires_reviewed_draft_and_cues(self):
        with self.assertRaises(ValueError):
            build_human_transcript_review_decision(
                {
                    "decision": "approved",
                    "reviewer": "human",
                    "reviewed_draft": "subtitles.draft.srt",
                    "reviewed_cue_ids": [],
                }
            )

        decision = build_human_transcript_review_decision(
            {
                "decision": "approved",
                "reviewer": "human",
                "reviewed_draft": "subtitles.draft.srt",
                "reviewed_cue_ids": ["cue01"],
            }
        )

        self.assertEqual(decision["decision"], "approved")
        self.assertTrue(decision["clears_human_transcript_review"])


if __name__ == "__main__":
    unittest.main()
