import json
import tempfile
import unittest
import wave
from pathlib import Path

from video_pipeline_core.delivery_gate import evaluate_complete_video_delivery
from video_pipeline_core.voiceover_provider import build_voiceover_provider_plan


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)


class ParentAgentDeliveryContractTest(unittest.TestCase):
    def test_old_parent_cut_no_narration_and_synthetic_music_blocks_delivery(self):
        run = Path(".tmp/parent_agent_delivery_cut_20260706-065345/run")
        if not run.is_dir():
            self.skipTest("parent delivery cut fixture is not present")

        result = evaluate_complete_video_delivery(run)

        self.assertFalse(result["pass"], result)
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("narration_required_for_complete_real_material_delivery", rules)
        self.assertIn("synthetic_music_not_delivery_allowed", rules)
        self.assertIn("missing_soundtrack_probe_report", rules)

    def test_delivery_gate_blocks_synthetic_music_even_when_manifest_has_tracks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"probe injected")
            (root / "delivery_requirements.json").write_text(json.dumps({
                "artifact_role": "delivery_requirements",
                "version": 1,
                "requires_audio": True,
                "requires_narration": True,
                "requires_music": True,
                "requires_subtitles": True,
                "requires_frame_evidence": False,
            }), encoding="utf-8")
            _write_wav(root / "narration.wav")
            (root / "narration_manifest.json").write_text(json.dumps({
                "artifact_role": "narration_manifest",
                "version": 1,
                "provider": "voxcpm",
                "segments": [{"id": "n1", "text": "旁白", "audio_ref": "narration.wav"}],
            }), encoding="utf-8")
            (root / "music_manifest.json").write_text(json.dumps({
                "artifact_role": "music_manifest",
                "version": 1,
                "source_type": "synthetic_generated_audio_bed",
                "source_file": "generated_bgm.wav",
                "tracks": [{"id": "m1", "source_ref": "generated_bgm.wav"}],
                "cues": [{"track_id": "m1", "start_sec": 0, "end_sec": 10}],
            }), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "version": 1,
                "pass": True,
                "features": {"mean_dbfs": -18.0},
                "sections": [{"start_sec": 0, "end_sec": 10}],
                "editing_fit": {"montage": "medium"},
                "section_fit": [{"video_section": "all", "fit": "medium"}],
            }), encoding="utf-8")
            (root / "audio_mix_report.json").write_text(json.dumps({
                "artifact_role": "audio_mix_report",
                "version": 1,
                "audio_stream_present": True,
                "music_included": True,
                "narration_included": True,
            }), encoding="utf-8")
            (root / "subtitles.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n旁白\n",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [
                    {"codec_type": "video", "duration": "10.0"},
                    {"codec_type": "audio", "duration": "10.0"},
                ],
            })

        self.assertFalse(result["pass"], result)
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("synthetic_music_not_delivery_allowed", rules)

    def test_voxcpm_provider_does_not_fallback_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.json"
            script.write_text(json.dumps([
                {"segment": 1, "text": "這是必要旁白。"},
            ], ensure_ascii=False), encoding="utf-8")

            payload = build_voiceover_provider_plan(
                script_path=script,
                out_dir=root / "voice",
                voxcpm_bin=str(root / "missing-voxcpm.exe"),
                voxcpm_repo=root / "missing-voxcpm-repo",
            )

        self.assertEqual(payload["plan"]["selected_provider"], "voxcpm")
        self.assertFalse(payload["plan"]["fallback_allowed"])
        self.assertFalse(payload["plan"]["provider_available"])
        self.assertEqual(payload["plan"]["errors"][0]["rule"], "provider_unavailable")


if __name__ == "__main__":
    unittest.main()
