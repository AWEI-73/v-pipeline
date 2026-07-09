import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.voiceover_output_qa import evaluate_voiceover_output_qa, write_voiceover_output_qa_for_run


class VoiceoverOutputQATest(unittest.TestCase):
    def test_blocks_control_text_in_output_probe_transcript(self):
        result = evaluate_voiceover_output_qa({
            "voiceover_output_probe": {
                "method": "faster_whisper",
                "segments": [{"segment_id": "opening", "recognized_text": "firm documentary delivery"}],
                "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "faster_whisper"}],
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "voiceover_control_text_leak")

    def test_blocks_mandarin_narrator_leakage(self):
        result = evaluate_voiceover_output_qa({
            "voiceover_output_probe": {
                "method": "faster_whisper",
                "transcript": "Mandarin narrator introduces the scene",
                "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "faster_whisper"}],
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["term"], "Mandarin narrator")

    def test_missing_output_probe_blocks(self):
        result = evaluate_voiceover_output_qa({
            "narration_manifest": {"segments": [{"text": "clean line"}]},
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "needs_voiceover_output_probe")

    def test_clearneration_independent_asr_blocks(self):
        result = evaluate_voiceover_output_qa({
            "voiceover_output_probe": {
                "method": "faster_whisper",
                "segments": [{"segment_id": "opening", "recognized_text": "ClearNeration opening line"}],
                "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "faster_whisper"}],
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["term"], "ClearNeration")

    def test_provider_manifest_text_alone_does_not_pass(self):
        result = evaluate_voiceover_output_qa({
            "voiceover_output_probe": {
                "method": "provider_manifest_text_review",
                "segments": [{"segment_id": "opening", "recognized_text": "clean narration"}],
                "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "provider_manifest_text_review"}],
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "independent_asr_required")

    def test_valid_independent_asr_probe_passes(self):
        result = evaluate_voiceover_output_qa({
            "voiceover_output_probe": {
                "method": "faster_whisper",
                "segments": [{"segment_id": "opening", "recognized_text": "clean narration"}],
                "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "faster_whisper"}],
            },
        })

        self.assertTrue(result["pass"], result)

    def test_write_for_run_reads_probe_and_writes_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voiceover_output_probe.json").write_text(
                json.dumps({
                    "artifact_role": "voiceover_output_probe",
                    "method": "faster_whisper",
                    "segments": [{"segment_id": "opening", "recognized_text": "clean narration"}],
                    "evidence": [{"audio_ref": "voiceover/seg01.wav", "method": "faster_whisper"}],
                }),
                encoding="utf-8",
            )

            report = write_voiceover_output_qa_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "voiceover_output_qa.json").exists())


if __name__ == "__main__":
    unittest.main()
