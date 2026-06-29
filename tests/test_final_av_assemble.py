import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.final_av_assemble import assemble_final_av, build_video_filter, parse_label


class FinalAvAssembleTest(unittest.TestCase):
    def test_build_video_filter_contains_title_and_labels(self):
        filt = build_video_filter(
            title="HERMES",
            labels=[{"start_sec": 0.0, "end_sec": 5.0, "text": "OPENING"}],
        )
        self.assertIn("drawtext=text='HERMES'", filt)
        self.assertIn("drawtext=text='OPENING'", filt)
        self.assertIn("between(t,0.000,5.000)", filt)

    def test_parse_label(self):
        self.assertEqual(parse_label("1.5:3.0:ACTION"), {
            "start_sec": 1.5,
            "end_sec": 3.0,
            "text": "ACTION",
        })

    def test_assemble_maps_only_selected_audio_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            audio = root / "final_audio.wav"
            out = root / "final.mp4"
            video.write_bytes(b"video")
            audio.write_bytes(b"audio")

            def fake_run(cmd, check):
                self.assertTrue(check)
                self.assertIn("-map", cmd)
                self.assertIn("1:a:0", cmd)
                self.assertNotIn("0:a:0", cmd)
                out.write_bytes(b"final")

            with patch("tools.final_av_assemble.subprocess.run", side_effect=fake_run):
                payload = assemble_final_av(
                    video=video,
                    audio=audio,
                    out=out,
                    title="Demo",
                    labels=[{"start_sec": 0.0, "end_sec": 2.0, "text": "OPENING"}],
                )

            self.assertTrue(out.is_file())
            self.assertFalse(payload["source_audio_mapped"])
            self.assertEqual(payload["audio_map"], "-map 1:a:0")
            self.assertTrue((root / "assembly_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
