import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.source_dialogue_script import (
    build_dialogue_edit_script,
    import_json3_transcript,
)


class SourceDialogueScriptTests(unittest.TestCase):
    def test_import_json3_merges_caption_cues_into_sentence_units(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "subs.json3"
            path.write_text(json.dumps({
                "events": [
                    {"tStartMs": 0, "dDurationMs": 500, "segs": [{"utf8": "(gentle music)"}]},
                    {"tStartMs": 1000, "dDurationMs": 1000, "segs": [{"utf8": "My name is"}]},
                    {"tStartMs": 2000, "dDurationMs": 1000, "segs": [{"utf8": "David Meza."}]},
                    {"tStartMs": 5000, "dDurationMs": 1000, "segs": [{"utf8": "I build"}]},
                    {"tStartMs": 6000, "dDurationMs": 1000, "segs": [{"utf8": "knowledge maps."}]},
                ]
            }), encoding="utf-8")

            transcript = import_json3_transcript(path)

            self.assertEqual(transcript["artifact_role"], "source_transcript")
            self.assertEqual(len(transcript["cues"]), 4)
            self.assertEqual(len(transcript["sentence_units"]), 2)
            self.assertEqual(transcript["sentence_units"][0]["text"], "My name is David Meza.")
            self.assertEqual(transcript["sentence_units"][1]["start_sec"], 5.0)

    def test_dialogue_edit_script_expands_selection_to_complete_sentences(self):
        transcript = {
            "artifact_role": "source_transcript",
            "sentence_units": [
                {"sentence_id": "sent_001", "start_sec": 10.0, "end_sec": 15.0, "text": "First complete sentence."},
                {"sentence_id": "sent_002", "start_sec": 15.2, "end_sec": 22.0, "text": "Second complete sentence."},
                {"sentence_id": "sent_003", "start_sec": 40.0, "end_sec": 45.0, "text": "Closing sentence."},
            ],
        }
        rough = {
            "windows": [
                {"start": 16.0, "end": 18.0, "label": "core"},
                {"start": 41.0, "end": 42.0, "label": "closing"},
            ]
        }

        script = build_dialogue_edit_script(transcript, rough_windows=rough, target_sec=20)

        self.assertEqual(script["artifact_role"], "dialogue_edit_script")
        self.assertEqual(script["planned_duration_sec"], 11.8)
        self.assertEqual(script["clips"][0]["source_in_sec"], 15.2)
        self.assertEqual(script["clips"][0]["source_out_sec"], 22.0)
        self.assertEqual(script["clips"][1]["subtitle_text"], "Closing sentence.")
        self.assertEqual(script["dialogue_highlight_windows"]["windows"][0]["start"], 15.2)


if __name__ == "__main__":
    unittest.main()
