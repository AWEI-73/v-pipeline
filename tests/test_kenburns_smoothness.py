import unittest
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from video_pipeline_core.mv_cut import _photo_vf
from video_pipeline_core.platform_tools import resolve_ffmpeg


class KenBurnsSmoothnessContractTest(unittest.TestCase):
    def test_slow_push_uses_4k_scale_crop_without_zoompan(self):
        vf = _photo_vf(2.0, kenburns=True, treatment={"mode": "slow_push"})

        self.assertNotIn("zoompan", vf)
        self.assertIn("fps=30", vf)
        self.assertIn("crop=3840:2160", vf)
        self.assertIn("scale=1920:1080", vf)
        self.assertNotIn("s=2560x1440", vf)

    def test_slow_push_does_not_use_truncated_center_motion(self):
        vf = _photo_vf(2.0, kenburns=True, treatment={"mode": "slow_push"})

        self.assertNotIn("trunc(", vf)
        self.assertNotIn("floor(", vf)

    def test_pan_modes_do_not_step_by_fixed_pixels_per_frame(self):
        for mode in ("pan_left", "pan_right"):
            with self.subTest(mode=mode):
                vf = _photo_vf(2.0, kenburns=True, treatment={"mode": mode})

                self.assertNotIn("x+3", vf)
                self.assertNotIn("x-3", vf)
                self.assertIn("n/", vf)


class KenBurnsSmoothnessRenderTest(unittest.TestCase):
    def test_short_still_motion_true_render_is_nonblank_and_stable(self):
        ffmpeg = resolve_ffmpeg()
        d = Path(tempfile.mkdtemp())
        src = d / "source.png"
        out = d / "kenburns.mp4"
        frames_dir = d / "frames"
        frames_dir.mkdir()

        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "testsrc2=size=640x360:duration=1:rate=1",
            "-vframes", "1", str(src),
        ], capture_output=True, check=True)

        subprocess.run([
            ffmpeg, "-y", "-loop", "1", "-framerate", "30", "-i", str(src),
            "-vf", _photo_vf(2.0, kenburns=True, treatment={"mode": "slow_push"}),
            "-t", "2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
        ], capture_output=True, check=True)

        subprocess.run([
            ffmpeg, "-y", "-v", "error", "-i", str(out),
            "-vf", "fps=10,scale=320:180", str(frames_dir / "f_%03d.jpg"),
        ], capture_output=True, check=True)

        frames = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in sorted(frames_dir.glob("f_*.jpg"))]
        frames = [f for f in frames if f is not None]
        self.assertGreaterEqual(len(frames), 15)
        self.assertGreater(float(np.mean([np.std(f) for f in frames])), 10.0)

        diffs = [
            float(np.mean(cv2.absdiff(a, b)))
            for a, b in zip(frames, frames[1:])
        ]
        self.assertGreater(max(diffs), 0.05)
        self.assertLess(max(diffs), 20.0)


if __name__ == "__main__":
    unittest.main()
