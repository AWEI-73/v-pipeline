import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
