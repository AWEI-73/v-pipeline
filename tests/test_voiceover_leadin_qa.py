import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.voiceover_leadin_qa import (
    evaluate_voiceover_leadin_qa,
    write_voiceover_leadin_qa_for_run,
)


class VoiceoverLeadInQATest(unittest.TestCase):
    def test_blocks_extra_single_token_before_expected_text(self):
        result = evaluate_voiceover_leadin_qa(
            {
                "expected_segments": [
                    {"segment_id": "seg02", "text": "基本訓練讓每一個動作扎實。"}
                ],
                "asr_segments": [
                    {"segment_id": "seg02", "recognized_text": "抗,基本訓練讓每一個動作扎實。"}
                ],
            }
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "voiceover_extra_leadin")
        self.assertEqual(result["blocking"][0]["detected_extra_leadin"], "抗")

    def test_blocks_extra_phrase_before_expected_text(self):
        result = evaluate_voiceover_leadin_qa(
            {
                "expected_segments": [{"segment_id": "seg01", "text": "這一天我們一起回到訓練現場。"}],
                "asr_segments": [{"segment_id": "seg01", "recognized_text": "看我們這一天我們一起回到訓練現場。"}],
            }
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["detected_extra_leadin"], "看我們")

    def test_blocks_kang_leadin_before_expected_text(self):
        result = evaluate_voiceover_leadin_qa(
            {
                "expected_segments": [{"segment_id": "seg01", "text": "這一天我們一起回到訓練現場。"}],
                "asr_segments": [{"segment_id": "seg01", "recognized_text": "康,這一天我們一起回到訓練現場。"}],
            }
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["detected_extra_leadin"], "康")

    def test_passes_matching_content_prefix(self):
        result = evaluate_voiceover_leadin_qa(
            {
                "expected_segments": [{"segment_id": "seg01", "text": "這一天我們一起回到訓練現場。"}],
                "asr_segments": [{"segment_id": "seg01", "recognized_text": "這一天我們一起回到訓練現場。"}],
            }
        )

        self.assertTrue(result["pass"], result)

    def test_missing_independent_asr_blocks(self):
        result = evaluate_voiceover_leadin_qa(
            {"expected_segments": [{"segment_id": "seg01", "text": "這一天我們一起回到訓練現場。"}]}
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "independent_asr_missing")

    def test_write_for_run_reads_manifest_and_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "narration_manifest.json").write_text(
                json.dumps(
                    {
                        "segments": [
                            {"id": "seg01", "text": "這一天我們一起回到訓練現場。"}
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "voiceover_output_probe.json").write_text(
                json.dumps(
                    {
                        "method": "faster_whisper",
                        "segments": [
                            {"segment_id": "seg01", "recognized_text": "這一天我們一起回到訓練現場。"}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = write_voiceover_leadin_qa_for_run(root)

            self.assertTrue(result["pass"], result)
            self.assertTrue((root / "voiceover_leadin_qa.json").exists())


if __name__ == "__main__":
    unittest.main()
