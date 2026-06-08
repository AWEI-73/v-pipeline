"""Tests for video_pipeline_core.shot_slots.

Covers:
  - expand_shot_slots (basic required functions list)
  - expand_shot_slots (padding with optional functions and detail fallback up to n_required)
  - expand_shot_slots (duration divided evenly when segment duration_sec is set)
  - expand_shot_slots (preferred media photo vs video based on still policy)
"""
import unittest

from video_pipeline_core.shot_slots import expand_shot_slots


class TestShotSlots(unittest.TestCase):
    """Test shot slots expansion helper."""

    def test_expand_basic_required(self):
        segment = {
            "segment": 2,
            "sequence_grammar": {
                "required_functions": ["establish", "action", "result"],
            },
            "pacing": {
                "preferred_shot_sec": [3.0, 5.0],
            },
        }
        slots = expand_shot_slots(segment)
        self.assertEqual(len(slots), 3)
        self.assertEqual(slots[0]["slot"], "2.1")
        self.assertEqual(slots[0]["function"], "establish")
        self.assertEqual(slots[0]["target_duration_sec"], 4.0)  # average of [3.0, 5.0]
        self.assertIn("video", slots[0]["preferred_media"])
        self.assertIn("photo", slots[0]["preferred_media"])

        self.assertEqual(slots[1]["slot"], "2.2")
        self.assertEqual(slots[1]["function"], "action")

        self.assertEqual(slots[2]["slot"], "2.3")
        self.assertEqual(slots[2]["function"], "result")

    def test_expand_with_n_required_padding(self):
        segment = {
            "segment": 1,
            "sequence_grammar": {
                "required_functions": ["establish", "action"],
                "optional_functions": ["reaction"],
            },
        }
        # n_required = 4. Starts with ['establish', 'action'],
        # pads with 'reaction' (optional), then 'detail' (fallback).
        slots = expand_shot_slots(segment, n_required=4)
        self.assertEqual(len(slots), 4)
        self.assertEqual(slots[0]["function"], "establish")
        self.assertEqual(slots[1]["function"], "action")
        self.assertEqual(slots[2]["function"], "reaction")
        self.assertEqual(slots[3]["function"], "detail")

    def test_expand_segment_duration_divided_evenly(self):
        segment = {
            "segment": 3,
            "duration_sec": 6.0,
            "sequence_grammar": {
                "required_functions": ["establish", "action", "result"],
            },
        }
        slots = expand_shot_slots(segment)
        self.assertEqual(len(slots), 3)
        # 6.0 / 3 = 2.0s per shot
        self.assertEqual(slots[0]["target_duration_sec"], 2.0)
        self.assertEqual(slots[1]["target_duration_sec"], 2.0)
        self.assertEqual(slots[2]["target_duration_sec"], 2.0)

    def test_expand_still_policy_disallowed(self):
        segment = {
            "segment": 1,
            "still_image_policy": {
                "allowed": False,
            },
        }
        slots = expand_shot_slots(segment)
        # Check that photo is not in preferred media
        self.assertEqual(slots[0]["preferred_media"], ["video"])


if __name__ == "__main__":
    unittest.main()
