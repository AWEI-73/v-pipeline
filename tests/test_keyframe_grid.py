"""keyframe_grid — Node 12 deterministic contact-sheet generation (P1-B)."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import keyframe_grid as kg


def _ffmpeg_available():
    try:
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        resolve_ffmpeg()
        return True
    except Exception:
        return False


class KeyframeTimestampTest(unittest.TestCase):
    def test_even_spacing_midpoints(self):
        ts = kg.select_timestamps(12.0, 4)
        self.assertEqual(ts, [1.5, 4.5, 7.5, 10.5])

    def test_single_sample_is_middle(self):
        self.assertEqual(kg.select_timestamps(10.0, 1), [5.0])

    def test_deterministic(self):
        self.assertEqual(kg.select_timestamps(33.0, 7), kg.select_timestamps(33.0, 7))

    def test_zero_duration_returns_empty(self):
        self.assertEqual(kg.select_timestamps(0.0, 4), [])

    def test_grid_dimensions(self):
        self.assertEqual(kg.grid_dimensions(12, 4), (4, 3))
        self.assertEqual(kg.grid_dimensions(10, 4), (4, 3))
        self.assertEqual(kg.grid_dimensions(6, 3), (3, 2))
        self.assertEqual(kg.grid_dimensions(1, 4), (1, 1))

    def test_explicit_timestamps_are_preserved(self):
        timestamps, sampling = kg.resolve_grid_timestamps(
            10, 4, explicit=[1.25, 8.75], shots=[(0, 5), (5, 10)])
        self.assertEqual(timestamps, [1.25, 8.75])
        self.assertEqual(sampling, "explicit")


@unittest.skipUnless(_ffmpeg_available(), "ffmpeg not available")
class KeyframeGridSmokeTest(unittest.TestCase):
    def setUp(self):
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        self.ffmpeg = resolve_ffmpeg()
        self.tmp = tempfile.mkdtemp()
        self.video = os.path.join(self.tmp, "clip.mp4")
        # generate a short deterministic test video
        subprocess.run(
            [self.ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=10",
             "-pix_fmt", "yuv420p", self.video],
            capture_output=True, check=True,
        )

    def test_generates_non_empty_grid_with_metadata(self):
        out = os.path.join(self.tmp, "keyframe_grid.jpg")
        meta = kg.generate_keyframe_grid(self.video, out, sample_count=6, columns=3)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)
        self.assertEqual(meta["sample_count"], 6)
        self.assertEqual(len(meta["samples"]), 6)
        self.assertEqual((meta["columns"], meta["rows"]), (3, 2))
        for s in meta["samples"]:
            self.assertGreaterEqual(s["timestamp_sec"], 0.0)
            self.assertLessEqual(s["timestamp_sec"], 3.0)
        # cells are 1-indexed and sequential
        self.assertEqual([s["cell"] for s in meta["samples"]], [1, 2, 3, 4, 5, 6])


class SceneMidpointsTest(unittest.TestCase):
    def test_midpoints_per_scene(self):
        from video_pipeline_core.keyframe_grid import scene_midpoints
        self.assertEqual(scene_midpoints([(0, 10), (10, 30)], 12), [5.0, 20.0])

    def test_subsamples_when_too_many_scenes(self):
        from video_pipeline_core.keyframe_grid import scene_midpoints
        shots = [(i, i + 1) for i in range(40)]
        out = scene_midpoints(shots, 12)
        self.assertEqual(len(out), 12)
        self.assertEqual(out, sorted(out))

    def test_empty_and_degenerate(self):
        from video_pipeline_core.keyframe_grid import scene_midpoints
        self.assertEqual(scene_midpoints([], 12), [])
        self.assertEqual(scene_midpoints([(5, 5)], 12), [])

if __name__ == "__main__":
    unittest.main()
