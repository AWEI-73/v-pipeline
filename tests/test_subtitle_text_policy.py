import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import video_tools
from video_pipeline_core import vt_editor
from video_pipeline_core import subtitle_presentation
from video_tools import cmd_burnsub


class SubtitleTextPolicyTest(unittest.TestCase):
    def test_exact_policy_yields_the_original_srt_bytes(self):
        source_bytes = (
            "1\r\n"
            "00:00:00,300 --> 00:00:03,400\r\n"
            "第67期養成班的學員們，大家好。\r\n"
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "subtitles.srt"
            source.write_bytes(source_bytes)

            self.assertTrue(
                hasattr(subtitle_presentation, "subtitle_srt_file"),
                "shared subtitle_srt_file policy boundary is missing",
            )
            with subtitle_presentation.subtitle_srt_file(str(source), subtitle_text_policy="exact") as rendered:
                rendered_path = Path(rendered)
                self.assertEqual(rendered_path.resolve(), source.resolve())
                self.assertEqual(rendered_path.read_bytes(), source_bytes)

    def test_default_policy_still_uses_the_existing_polish_behavior(self):
        source_text = (
            "1\n"
            "00:00:00,300 --> 00:00:03,400\n"
            "第一句，第二句。\n"
        )

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "subtitles.srt"
            source.write_text(source_text, encoding="utf-8")

            self.assertTrue(hasattr(subtitle_presentation, "subtitle_srt_file"))
            with subtitle_presentation.subtitle_srt_file(str(source)) as rendered:
                polished = Path(rendered).read_text(encoding="utf-8")

            self.assertIn("第一句　第二句", polished)
            self.assertNotIn("第一句，第二句。", polished)

    def test_unknown_policy_fails_closed_before_render_input_is_opened(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "subtitles.srt"
            source.write_text("1\n00:00:00,000 --> 00:00:01,000\ntext\n", encoding="utf-8")

            self.assertTrue(hasattr(subtitle_presentation, "subtitle_srt_file"))
            with self.assertRaises(ValueError):
                with subtitle_presentation.subtitle_srt_file(str(source), subtitle_text_policy="rewrite"):
                    self.fail("unknown subtitle text policy must not yield a render path")

    def test_burnsub_passes_exact_policy_to_the_shared_input_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "subtitles.srt"
            source.write_text("1\n00:00:00,000 --> 00:00:01,000\ntext\n", encoding="utf-8")
            args = SimpleNamespace(
                video="input.mp4",
                srt=str(source),
                out=str(Path(td) / "out.mp4"),
                subtitle_text_policy="exact",
            )
            fake_result = SimpleNamespace(returncode=0, stderr="")

            with patch("video_pipeline_core.subtitle_presentation.subtitle_srt_file", create=True) as srt_file, \
                    patch("video_pipeline_core.subtitle_presentation.polished_srt_file") as polished_srt_file, \
                    patch("video_pipeline_core.platform_tools.resolve_font", return_value="C:/fonts/fake.ttf"), \
                    patch("video_pipeline_core.subtitle_presentation.build_ass_style", return_value="style"), \
                    patch("video_pipeline_core.subtitle_presentation.probe_video_height", return_value=1080), \
                    patch("video_tools.run", return_value=fake_result), \
                    contextlib.redirect_stdout(io.StringIO()):
                srt_file.return_value.__enter__.return_value = str(source)
                polished_srt_file.return_value.__enter__.return_value = str(source)
                cmd_burnsub(args)

            srt_file.assert_called_once_with(str(source), subtitle_text_policy="exact")

    def test_merge_final_passes_exact_policy_to_the_shared_input_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            visual = root / "visual.mp4"
            audio = root / "audio.wav"
            source = root / "subtitles.srt"
            for path in (visual, audio, source):
                path.write_bytes(b"fixture")
            args = SimpleNamespace(
                visual=str(visual),
                audio=str(audio),
                subs=str(source),
                out=str(root / "out.mp4"),
                subtitle_text_policy="exact",
            )
            fake_result = SimpleNamespace(returncode=0, stderr="")

            with patch("video_pipeline_core.subtitle_presentation.subtitle_srt_file", create=True) as srt_file, \
                    patch("video_pipeline_core.subtitle_presentation.polished_srt_file") as polished_srt_file, \
                    patch("video_pipeline_core.platform_tools.resolve_font", return_value="C:/fonts/fake.ttf"), \
                    patch("video_pipeline_core.subtitle_presentation.build_ass_style", return_value="style"), \
                    patch("video_pipeline_core.subtitle_presentation.probe_video_height", return_value=1080), \
                    patch("video_pipeline_core.vt_editor.run", return_value=fake_result), \
                    patch("video_pipeline_core.vt_editor._audio_duration", return_value=1.0), \
                    contextlib.redirect_stdout(io.StringIO()):
                srt_file.return_value.__enter__.return_value = str(source)
                polished_srt_file.return_value.__enter__.return_value = str(source)
                vt_editor.cmd_merge_final(args)

            srt_file.assert_called_once_with(str(source), subtitle_text_policy="exact")


class SubtitleTextPolicyCliTest(unittest.TestCase):
    def test_burnsub_and_merge_final_parser_forward_exact_policy(self):
        cases = [
            ("burnsub", ["video.mp4", "subtitles.srt"]),
            ("merge-final", ["--visual", "visual.mp4", "--audio", "audio.wav", "--subs", "subtitles.srt"]),
        ]

        for command, command_args in cases:
            with self.subTest(command=command):
                received = MagicMock()
                argv = ["video_tools.py", command, *command_args, "--subtitle-text-policy", "exact"]
                with patch.object(video_tools, "VIDEO_TOOLS_DISPATCH", {command: received}), \
                        patch.object(video_tools.sys, "argv", argv):
                    try:
                        video_tools.main()
                    except SystemExit as exc:
                        self.fail(f"parser rejected {command} exact policy with exit {exc.code}")

                self.assertEqual(received.call_args.args[0].subtitle_text_policy, "exact")

    def test_parser_defaults_subtitle_text_policy_to_polish(self):
        received = MagicMock()
        with patch.object(video_tools, "VIDEO_TOOLS_DISPATCH", {"burnsub": received}), \
                patch.object(video_tools.sys, "argv", ["video_tools.py", "burnsub", "video.mp4", "subtitles.srt"]):
            video_tools.main()

        self.assertEqual(getattr(received.call_args.args[0], "subtitle_text_policy", None), "polish")

    def test_parser_rejects_unknown_subtitle_text_policy(self):
        stderr = io.StringIO()
        with patch.object(video_tools, "VIDEO_TOOLS_DISPATCH", {"burnsub": MagicMock()}), \
                patch.object(video_tools.sys, "argv", [
                    "video_tools.py", "burnsub", "video.mp4", "subtitles.srt",
                    "--subtitle-text-policy", "rewrite",
                ]), \
                contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                video_tools.main()

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
