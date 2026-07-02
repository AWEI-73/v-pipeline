import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SoundtrackProbeTest(unittest.TestCase):
    def test_builds_basic_probe_report_from_ffmpeg_text_outputs(self):
        from video_pipeline_core.soundtrack_probe import build_soundtrack_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake")

            def fake_run(cmd, **kwargs):
                class Result:
                    returncode = 0
                    stdout = json.dumps({
                        "format": {"duration": "120.0"},
                        "streams": [{"codec_type": "audio", "codec_name": "mp3", "duration": "120.0"}],
                    }) if "ffprobe" in cmd[0] else ""
                    stderr = (
                        "[Parsed_volumedetect] mean_volume: -18.5 dB\n"
                        "[Parsed_volumedetect] max_volume: -2.1 dB\n"
                    ) if "volumedetect" in cmd else (
                        "[silencedetect] silence_start: 10\n"
                        "[silencedetect] silence_end: 12 | silence_duration: 2\n"
                    )
                return Result()

            with (
                patch("video_pipeline_core.soundtrack_probe.subprocess.run", side_effect=fake_run),
                patch("video_pipeline_core.soundtrack_probe._music_features", return_value={}),
            ):
                report = build_soundtrack_probe(audio)

        self.assertEqual(report["artifact_role"], "soundtrack_probe_report")
        self.assertTrue(report["pass"])
        self.assertEqual(report["duration_sec"], 120.0)
        self.assertEqual(report["features"]["mean_dbfs"], -18.5)
        self.assertEqual(report["features"]["peak_dbfs"], -2.1)
        self.assertEqual(report["features"]["silence_total_sec"], 2.0)
        self.assertTrue(report["sections"])
        self.assertIn("montage", report["editing_fit"])
        speech = next(item for item in report["section_fit"] if item["video_section"] == "speech_underlay")
        self.assertEqual(speech["fit"], "high")
        self.assertIn("no detected vocal load", speech["reason"])

    def test_merges_optional_music_features_when_available(self):
        from video_pipeline_core.soundtrack_probe import build_soundtrack_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake")

            def fake_run(cmd, **kwargs):
                class Result:
                    returncode = 0
                    stdout = json.dumps({
                        "format": {"duration": "90.0"},
                        "streams": [{"codec_type": "audio", "codec_name": "mp3", "duration": "90.0"}],
                    }) if "ffprobe" in cmd[0] else ""
                    stderr = "[Parsed_volumedetect] mean_volume: -18.5 dB\n[Parsed_volumedetect] max_volume: -2.1 dB\n"
                return Result()

            with (
                patch("video_pipeline_core.soundtrack_probe.subprocess.run", side_effect=fake_run),
                patch("video_pipeline_core.soundtrack_probe._music_features", return_value={
                    "tempo_bpm": 124.0,
                    "beat_times": [0.5, 1.0, 1.5],
                    "energy_curve": [{"start_sec": 0.0, "end_sec": 4.0, "rms": 0.1}],
                    "semantic_tags": ["energetic_candidate"],
                }),
            ):
                report = build_soundtrack_probe(audio)

        self.assertEqual(report["analysis_depth"], "basic_ffmpeg+music_features")
        self.assertEqual(report["features"]["tempo_bpm"], 124.0)
        self.assertEqual(report["features"]["beat_times"], [0.5, 1.0, 1.5])
        self.assertIn("energetic_candidate", report["features"]["semantic_tags"])

    def test_video_without_audio_stream_returns_no_audio_probe_instead_of_crashing(self):
        from video_pipeline_core.soundtrack_probe import build_soundtrack_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "silent.mp4"
            video.write_bytes(b"fake")

            def fake_run(cmd, **kwargs):
                class Result:
                    returncode = 0
                    stdout = json.dumps({
                        "format": {"duration": "133.28"},
                        "streams": [{"codec_type": "video", "codec_name": "h264", "duration": "133.28"}],
                    })
                    stderr = ""
                return Result()

            with (
                patch("video_pipeline_core.soundtrack_probe.subprocess.run", side_effect=fake_run),
                patch("video_pipeline_core.soundtrack_probe._music_features", return_value={}) as music_features,
            ):
                report = build_soundtrack_probe(video)

        self.assertTrue(report["pass"])
        self.assertEqual(report["analysis_depth"], "no_audio_stream")
        self.assertFalse(report["features"]["has_audio"])
        self.assertEqual(report["features"]["codec"], None)
        self.assertEqual(report["duration_sec"], 133.28)
        self.assertEqual(report["editing_fit"]["speech_underlay"], "not_applicable")
        self.assertIn("no audio stream", " ".join(report["limitations"]).lower())
        music_features.assert_not_called()

    def test_enable_asr_adds_vocal_analysis_and_section_fit(self):
        from video_pipeline_core.soundtrack_probe import build_soundtrack_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake")

            def fake_run(cmd, **kwargs):
                class Result:
                    returncode = 0
                    stdout = json.dumps({
                        "format": {"duration": "60.0"},
                        "streams": [{"codec_type": "audio", "codec_name": "mp3", "duration": "60.0"}],
                    }) if "ffprobe" in cmd[0] else ""
                    stderr = "[Parsed_volumedetect] mean_volume: -16.0 dB\n[Parsed_volumedetect] max_volume: -3.0 dB\n"
                return Result()

            with (
                patch("video_pipeline_core.soundtrack_probe.subprocess.run", side_effect=fake_run),
                patch("video_pipeline_core.soundtrack_probe._music_features", return_value={
                    "tempo_bpm": 132.0,
                    "beat_times": [0.5, 1.0, 1.5],
                    "energy_curve": [{"start_sec": 0.0, "end_sec": 4.0, "relative_energy": 0.8}],
                    "semantic_tags": ["fast_tempo"],
                }),
                patch("video_pipeline_core.soundtrack_probe._asr_vocal_analysis", return_value={
                    "has_vocals": True,
                    "method": "faster_whisper",
                    "language": "zh",
                    "vocal_density": "medium",
                    "vocal_ratio": 0.35,
                    "segments": [{"start_sec": 10.0, "end_sec": 20.0, "text": "一起向前"}],
                    "instrumental_windows": [{"start_sec": 0.0, "end_sec": 10.0}],
                    "transcript_preview": "一起向前",
                }),
            ):
                report = build_soundtrack_probe(audio, enable_asr=True, asr_model="small", language="zh")

        self.assertEqual(report["features"]["vocal_analysis"]["has_vocals"], True)
        self.assertEqual(report["features"]["vocal_analysis"]["transcript_preview"], "一起向前")
        self.assertTrue(report["section_fit"])
        speech = next(item for item in report["section_fit"] if item["video_section"] == "speech_underlay")
        self.assertEqual(speech["fit"], "low")
        montage = next(item for item in report["section_fit"] if item["video_section"] == "hotblooded_montage")
        self.assertIn(montage["fit"], {"medium", "high"})

    def test_cli_writes_soundtrack_probe_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "song.mp3"
            out = root / "soundtrack_probe_report.json"
            audio.write_bytes(b"fake")

            def fake_probe(audio_path, **kwargs):
                return {
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": str(audio_path),
                    "duration_sec": 30.0,
                    "features": {"mean_dbfs": -20.0, "peak_dbfs": -3.0},
                    "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "full_track"}],
                    "editing_fit": {"montage": "medium"},
                    "limitations": [],
                }

            with patch("tools.soundtrack_probe.build_soundtrack_probe", side_effect=fake_probe):
                from tools.soundtrack_probe import main
                rc = main(["--audio", str(audio), "--out", str(out), "--enable-asr", "--asr-model", "tiny", "--language", "zh", "--json"])

            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "soundtrack_probe_report")
            self.assertTrue(payload["pass"])

    def test_script_help_runs_from_repo_root(self):
        proc = subprocess.run(
            [sys.executable, "tools/soundtrack_probe.py", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("soundtrack_probe_report", proc.stdout)


if __name__ == "__main__":
    unittest.main()
