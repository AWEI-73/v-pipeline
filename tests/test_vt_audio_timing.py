import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.vt_audio import (
    _audio_duration,
    _finalize_segment_timing,
    _render_silence_mp3,
)


class SpeechTailTimingTest(unittest.TestCase):
    def test_non_final_segment_gets_breathing_tail(self):
        segment, cursor = _finalize_segment_timing(
            1, "opening", 0.0, 3.2, [{"phrase": 1}], 0, 3,
        )

        self.assertEqual(segment["speech_end_sec"], 3.2)
        self.assertEqual(segment["tail_padding_sec"], 0.4)
        self.assertEqual(segment["end_sec"], 3.6)
        self.assertEqual(segment["duration_sec"], 3.6)
        self.assertEqual(cursor, 3.6)

    def test_final_segment_has_no_transition_tail(self):
        segment, cursor = _finalize_segment_timing(
            3, "closing", 7.0, 10.0, [{"phrase": 1}], 2, 3,
        )

        self.assertEqual(segment["tail_padding_sec"], 0.0)
        self.assertEqual(segment["end_sec"], 10.0)
        self.assertEqual(cursor, 10.0)


class SilenceRenderTest(unittest.TestCase):
    def test_silence_file_matches_edge_tts_audio_shape_and_duration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tail.mp3"

            _render_silence_mp3(path, 0.4)

            self.assertTrue(path.exists())
            self.assertAlmostEqual(_audio_duration(path), 0.4, delta=0.08)


if __name__ == "__main__":
    unittest.main()
