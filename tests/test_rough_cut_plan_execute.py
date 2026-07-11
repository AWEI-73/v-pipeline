import unittest
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


class RoughCutPlanExecuteTest(unittest.TestCase):
    def test_ffmpeg_command_uses_decoder_preroll_and_filter_precise_trim(self):
        from tools.rough_cut_plan_execute import build_rough_cut_ffmpeg_command

        clips = [
            {
                "source_path": str(Path("a.mp4")),
                "start_sec": 12.0,
                "duration_sec": 6.0,
            },
            {
                "source_path": str(Path("b.mp4")),
                "start_sec": 30.5,
                "duration_sec": 4.5,
            },
        ]

        command = build_rough_cut_ffmpeg_command(
            clips,
            out=Path("out.mp4"),
            audio=None,
            width=640,
            height=360,
        )

        self.assertLess(command.index("-ss"), command.index("-i"))
        self.assertEqual(command[command.index("-ss") + 1], "11.000")
        first_input = command.index(str(Path("a.mp4")))
        second_seek = command.index("-ss", first_input + 1)
        self.assertLess(second_seek, command.index(str(Path("b.mp4"))))
        self.assertEqual(command[second_seek + 1], "29.500")
        self.assertNotIn("-t", command)
        filtergraph = command[command.index("-filter_complex") + 1]
        self.assertIn("trim=start=1.000:end=7.000", filtergraph)
        self.assertIn("trim=start=1.000:end=5.500", filtergraph)

    def test_ffmpeg_command_pins_preview_frame_rate(self):
        from tools.rough_cut_plan_execute import build_rough_cut_ffmpeg_command

        command = build_rough_cut_ffmpeg_command(
            [{
                "source_path": str(Path("a.mp4")),
                "start_sec": 0.0,
                "duration_sec": 2.0,
            }],
            out=Path("out.mp4"),
            audio=None,
            width=640,
            height=360,
            fps=30,
        )

        filtergraph = command[command.index("-filter_complex") + 1]
        self.assertIn("fps=30", filtergraph)
        self.assertIn("setpts=N/(30*TB)", filtergraph)
        self.assertIn("-r", command)
        self.assertEqual(command[command.index("-r") + 1], "30")

    def test_nonzero_source_seek_preserves_exact_frames_and_external_audio(self):
        from tools.rough_cut_plan_execute import execute_rough_cut_plan
        from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "main10_hevc_source.mp4"
            external_audio = root / "continuous_speech.wav"
            plan = root / "rough_cut_plan.json"
            out = root / "preview.mp4"
            report = root / "rough_cut_preview_report.json"
            subprocess.run([
                resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=duration=5:size=320x180:rate=30",
                "-vf", "format=yuv420p10le", "-c:v", "libx265",
                "-x265-params", "keyint=90:min-keyint=90:scenecut=0:pools=1:frame-threads=1:log-level=error",
                "-pix_fmt", "yuv420p10le", str(source),
            ], check=True, capture_output=True, text=True)
            subprocess.run([
                resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                "-c:a", "pcm_s16le", str(external_audio),
            ], check=True, capture_output=True, text=True)
            plan.write_text(json.dumps({
                "clips": [{
                    "source_path": str(source),
                    "start_sec": 1.1,
                    "duration_sec": 2.0,
                }]
            }), encoding="utf-8")

            payload = execute_rough_cut_plan(
                plan,
                out,
                report,
                audio_path=external_audio,
                width=320,
                height=180,
                fps=30,
                timeout_sec=30,
            )

            self.assertTrue(payload["ok"])
            probe = subprocess.run([
                resolve_ffprobe(), "-v", "error", "-count_frames",
                "-show_entries", "stream=codec_type,duration,nb_read_frames",
                "-of", "json", str(out),
            ], check=True, capture_output=True, text=True)
            streams = json.loads(probe.stdout)["streams"]
            video = next(stream for stream in streams if stream["codec_type"] == "video")
            audio = next(stream for stream in streams if stream["codec_type"] == "audio")
            self.assertEqual(int(video["nb_read_frames"]), round(2.0 * 30))
            self.assertAlmostEqual(float(video["duration"]), 2.0, places=3)
            self.assertAlmostEqual(float(audio["duration"]), 2.0, places=2)

    def test_execute_clamps_clip_duration_to_source_duration(self):
        from tools.rough_cut_plan_execute import execute_rough_cut_plan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            source.write_bytes(b"fake-video")
            plan = root / "rough_cut_plan.json"
            plan.write_text(json.dumps({
                "clips": [{
                    "source_path": str(source),
                    "start_sec": 1.0,
                    "duration_sec": 8.0,
                }]
            }), encoding="utf-8")
            out = root / "preview.mp4"
            report = root / "rough_cut_preview_report.json"

            def fake_probe(path):
                if Path(path) == source:
                    return {"duration_sec": 5.25, "streams": []}
                return {"duration_sec": 4.25, "streams": [{"codec_type": "video", "codec_name": "h264"}]}

            def fake_run(*_args, **_kwargs):
                out.write_bytes(b"preview")
                return subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr="")

            with patch("tools.rough_cut_plan_execute.resolve_ffmpeg", return_value="ffmpeg"), \
                    patch("tools.rough_cut_plan_execute.subprocess.run", side_effect=fake_run), \
                    patch("tools.rough_cut_plan_execute._probe", side_effect=fake_probe):
                payload = execute_rough_cut_plan(plan, out, report, timeout_sec=1)

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["planned_duration_sec"], 8.0)
            self.assertEqual(payload["rendered_plan_duration_sec"], 4.25)
            self.assertEqual(payload["duration_adjustments"][0]["original_duration_sec"], 8.0)
            self.assertEqual(payload["duration_adjustments"][0]["adjusted_duration_sec"], 4.25)

    def test_timeout_writes_fail_closed_report_and_removes_partial_output(self):
        from tools.rough_cut_plan_execute import execute_rough_cut_plan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            source.write_bytes(b"fake-video")
            plan = root / "rough_cut_plan.json"
            plan.write_text(json.dumps({
                "clips": [{
                    "source_path": str(source),
                    "start_sec": 0,
                    "duration_sec": 4,
                }]
            }), encoding="utf-8")
            out = root / "preview.mp4"
            out.write_bytes(b"partial")
            report = root / "rough_cut_preview_report.json"

            def timeout_run(*_args, **_kwargs):
                raise subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=1)

            with patch("tools.rough_cut_plan_execute.resolve_ffmpeg", return_value="ffmpeg"), \
                    patch("tools.rough_cut_plan_execute._probe", return_value={"duration_sec": 10.0, "streams": []}), \
                    patch("tools.rough_cut_plan_execute.subprocess.run", side_effect=timeout_run):
                payload = execute_rough_cut_plan(plan, out, report, timeout_sec=1)

            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error_type"], "timeout")
            self.assertEqual(payload["next_action"], "use_rough_cut_storyboard_preview_or_reduce_clip_count")
            self.assertFalse(out.exists())
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(saved["ok"])
            self.assertTrue(saved["partial_output_removed"])


if __name__ == "__main__":
    unittest.main()
