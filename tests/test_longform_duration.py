"""Longform Duration Policy — TTS actual duration must drive material selection
and render, and a too-short video must be recoverable (loop/pad), never abort.

Regression target: 5-min story+MV stress test (2026-06-01) hard-failed because
candidate validity + scoring used script `duration_sec` while render required the
real TTS `actual_dur + xfade`. A video stock clip 0.3s short crashed the pipeline.
"""
import unittest

import video_pipeline as vp


class SegTargetLenTest(unittest.TestCase):
    def test_non_last_segment_includes_xfade_tail(self):
        script = [{"segment": 1}, {"segment": 2}, {"segment": 3}]
        actual_dur = {1: 5.0, 2: 7.5, 3: 4.0}
        self.assertAlmostEqual(vp._seg_target_len(2, script, actual_dur, 0.4), 7.9)

    def test_last_segment_has_no_xfade_tail(self):
        script = [{"segment": 1}, {"segment": 2}, {"segment": 3}]
        actual_dur = {1: 5.0, 2: 7.5, 3: 4.0}
        self.assertAlmostEqual(vp._seg_target_len(3, script, actual_dur, 0.4), 4.0)


class VideoCandidateFilterTest(unittest.TestCase):
    """Validity filter must key off the real TTS target, not script duration_sec."""

    def test_filter_uses_tts_target_not_script_duration(self):
        cands = [
            {"id": "a", "duration": 6},   # ok for script(5) but short for TTS(7.9)
            {"id": "b", "duration": 9},   # long enough for TTS target
            {"id": "c", "duration": 12},
        ]
        # TTS target 7.9 → need >= 7.9 + 1
        valid = vp._filter_video_candidates(cands, target_len=7.9)
        ids = {c["id"] for c in valid}
        self.assertNotIn("a", ids)
        self.assertEqual(ids, {"b", "c"})

    def test_score_penalizes_short_against_tts_target(self):
        short = {"alt": "x", "duration": 6}
        long = {"alt": "x", "duration": 10}
        s_short, _ = vp.score_candidate(short, "x", target_dur=7.9, is_video=True)
        s_long, _ = vp.score_candidate(long, "x", target_dur=7.9, is_video=True)
        self.assertLess(s_short, s_long)


class VideoFillPlanTest(unittest.TestCase):
    """Too-short video must be recoverable, never abort."""

    def test_long_enough_clip_is_trimmed(self):
        plan = vp._video_fill_plan(raw_d=12.0, target_len=7.9)
        self.assertEqual(plan["mode"], "trim")

    def test_short_clip_loops_instead_of_aborting(self):
        plan = vp._video_fill_plan(raw_d=6.0, target_len=7.9)
        self.assertEqual(plan["mode"], "loop")
        self.assertGreaterEqual(plan["loops"], 1)

    def test_marginally_short_clip_still_recoverable(self):
        # the exact 5-min regression: 0.3s short must not abort
        plan = vp._video_fill_plan(raw_d=7.6, target_len=7.9)
        self.assertIn(plan["mode"], ("loop", "pad"))


if __name__ == "__main__":
    unittest.main()
