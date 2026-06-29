import unittest

from video_pipeline_core.source_motion_profile import build_motion_profile_from_samples


class SourceMotionProfileTests(unittest.TestCase):
    def test_detects_blur_transition_and_scene_entry_from_sample_scores(self):
        samples = [
            {"time_sec": 194.0, "diff_score": 0.08, "hist_score": 0.05, "blur_score": 0.15, "black_score": 0.0},
            {"time_sec": 196.0, "diff_score": 0.52, "hist_score": 0.40, "blur_score": 0.88, "black_score": 0.0},
            {"time_sec": 198.0, "diff_score": 0.24, "hist_score": 0.18, "blur_score": 0.80, "black_score": 0.0},
            {"time_sec": 200.0, "diff_score": 0.66, "hist_score": 0.55, "blur_score": 0.20, "black_score": 0.0},
            {"time_sec": 202.0, "diff_score": 0.11, "hist_score": 0.07, "blur_score": 0.18, "black_score": 0.0},
        ]
        audio_curve = [
            {"start_sec": 192.0, "end_sec": 200.0, "relative_energy": 0.15},
            {"start_sec": 200.0, "end_sec": 204.0, "relative_energy": 0.20},
        ]

        result = build_motion_profile_from_samples(
            duration_sec=204.0,
            samples=samples,
            audio_curve=audio_curve,
            shot_boundaries=[200.0],
        )

        self.assertEqual(result["artifact_role"], "source_motion_profile")
        blur = next(point for point in result["ranked_edit_points"] if point["type"] == "blur_transition")
        entry = next(point for point in result["ranked_edit_points"] if point["type"] == "scene_entry")
        self.assertEqual(blur["time_sec"], 196.0)
        self.assertIn("low_audio", blur["tags"])
        self.assertEqual(entry["time_sec"], 200.0)
        self.assertIn("shot_boundary_nearby", entry["tags"])


if __name__ == "__main__":
    unittest.main()
