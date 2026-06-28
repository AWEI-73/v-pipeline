import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe


class SafeHighlightCutTest(unittest.TestCase):
    def test_reencodes_precise_windows_to_h264_aac_and_writes_report(self):
        ffmpeg = resolve_ffmpeg()
        ffprobe = resolve_ffprobe()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            windows = root / "windows.json"
            out = root / "highlight.mp4"
            report = root / "highlight_cut_report.json"

            subprocess.run([
                ffmpeg,
                "-y",
                "-f", "lavfi",
                "-i", "testsrc=duration=4:size=320x180:rate=30",
                "-f", "lavfi",
                "-i", "sine=frequency=440:duration=4",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(source),
            ], check=True, capture_output=True, text=True)
            windows.write_text(json.dumps({
                "windows": [
                    {"start": 0.25, "end": 1.25, "label": "opening"},
                    {"start": 2.1, "end": 3.1, "label": "middle"},
                ]
            }), encoding="utf-8")

            result = subprocess.run([
                "python",
                "tools/safe_highlight_cut.py",
                "--source", str(source),
                "--windows", str(windows),
                "--out", str(out),
                "--report", str(report),
            ], capture_output=True, text=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            self.assertTrue(report.exists())
            probe = subprocess.run([
                ffprobe,
                "-v", "error",
                "-show_entries", "stream=codec_name,codec_type",
                "-of", "json",
                str(out),
            ], check=True, capture_output=True, text=True)
            streams = json.loads(probe.stdout)["streams"]
            codecs = {item["codec_type"]: item["codec_name"] for item in streams}
            self.assertEqual(codecs["video"], "h264")
            self.assertEqual(codecs["audio"], "aac")

            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "highlight_cut_report")
            self.assertEqual(payload["cut_mode"], "reencode_filtergraph")
            self.assertFalse(payload["stream_copy"])
            self.assertEqual(payload["window_count"], 2)
            self.assertAlmostEqual(payload["duration_sec"], 2.0, delta=0.25)
