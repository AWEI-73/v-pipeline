import unittest
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


class RoughCutPlanExecuteTest(unittest.TestCase):
    def test_ffmpeg_command_uses_input_level_seek_for_each_clip(self):
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
        self.assertEqual(command[command.index("-ss") + 1], "12.000")
        first_input = command.index(str(Path("a.mp4")))
        second_seek = command.index("-ss", first_input + 1)
        self.assertLess(second_seek, command.index(str(Path("b.mp4"))))
        self.assertEqual(command[second_seek + 1], "30.500")
        self.assertIn("-t", command)
        self.assertEqual(command[command.index("-t") + 1], "6.000")

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
