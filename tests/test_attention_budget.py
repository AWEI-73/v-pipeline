import unittest

from video_pipeline_core.attention_budget import resolve_attention_budget


class TestAttentionBudget(unittest.TestCase):
    def test_narration_channel_owns_time_and_allows_longer_hold(self):
        segment = {
            "execution_plan": {
                "narration": {"mode": "voiceover"},
                "music": {"intensity": "low"},
            },
            "treatment": "single_hold",
        }

        budget = resolve_attention_budget(segment, mode="warm_documentary")

        self.assertEqual(budget["owner"], "narration")
        self.assertEqual(budget["shot_sec"], [3.0, 8.0])

    def test_untreated_still_without_narration_is_limited_to_two_seconds(self):
        segment = {
            "execution_plan": {
                "narration": {"mode": "none"},
                "music": {"intensity": "medium"},
            },
            "treatment": "single_hold",
            "still_motion": "none",
        }

        budget = resolve_attention_budget(segment, mode="rhythmic_mv")

        self.assertEqual(budget["owner"], "visual")
        self.assertEqual(budget["shot_sec"], [1.0, 2.0])

    def test_photo_stack_is_fast_even_without_high_energy_music(self):
        segment = {
            "execution_plan": {
                "narration": {"mode": "none"},
                "music": {"intensity": "medium"},
            },
            "treatment": "photo_stack_beat",
        }

        budget = resolve_attention_budget(segment, mode="training_recap")

        self.assertEqual(budget["owner"], "visual")
        self.assertEqual(budget["shot_sec"], [0.5, 1.0])

    def test_high_energy_music_requires_fast_cutting_when_no_narration(self):
        segment = {
            "execution_plan": {
                "narration": {"mode": "none"},
                "music": {"intensity": "high"},
            },
            "treatment": "video_primary",
        }

        budget = resolve_attention_budget(segment, mode="promo")

        self.assertEqual(budget["owner"], "music")
        self.assertEqual(budget["shot_sec"], [0.8, 2.0])


if __name__ == "__main__":
    unittest.main()
