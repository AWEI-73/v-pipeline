import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.montage_design_review import evaluate_montage_design_review, write_montage_design_review_for_run


class MontageDesignReviewTest(unittest.TestCase):
    def test_plain_title_card_opener_blocks(self):
        result = evaluate_montage_design_review({
            "montages": [{
                "section_id": "opening_story",
                "story_role": "opener",
                "shot_count": 1,
                "shot_functions": [{"function": "title_card", "duration_sec": 7.0}],
                "story_hook": "",
            }],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "opener_plain_title_card")

    def test_single_long_static_shot_blocks(self):
        result = evaluate_montage_design_review({
            "montages": [{
                "section_id": "opening_story",
                "story_role": "opener",
                "shot_count": 1,
                "shot_functions": [{"function": "static_photo", "duration_sec": 8.0}],
                "story_hook": "roll call starts the day",
                "payoff": "transition to training",
            }],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "opener_single_long_static_shot")

    def test_valid_montage_plan_passes(self):
        result = evaluate_montage_design_review({
            "montages": [{
                "section_id": "opening_story",
                "story_role": "opener",
                "target_mood": "discipline",
                "shot_count": 4,
                "shot_functions": [
                    {"function": "establish_place", "duration_sec": 1.5},
                    {"function": "gather_people", "duration_sec": 1.5},
                    {"function": "prepare_training", "duration_sec": 1.5},
                    {"function": "title_sync", "duration_sec": 1.0},
                ],
                "beat_timing": [{"start_sec": 0.0, "end_sec": 5.5, "energy": "rising"}],
                "title_sync_points": [2.0],
                "transitions": [{"type": "cut", "why": "keeps training rhythm"}],
                "story_hook": "students gather before training",
                "payoff": "moves into basic training",
            }],
        })

        self.assertTrue(result["pass"], result)

    def test_write_for_run_reads_plan_and_writes_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "montage_design_plan.json").write_text(
                json.dumps({
                    "montages": [{
                        "section_id": "opening_story",
                        "story_role": "opener",
                        "target_mood": "discipline",
                        "shot_count": 4,
                        "shot_functions": [
                            {"function": "establish_place", "duration_sec": 1.5},
                            {"function": "gather_people", "duration_sec": 1.5},
                            {"function": "prepare_training", "duration_sec": 1.5},
                            {"function": "title_sync", "duration_sec": 1.0},
                        ],
                        "beat_timing": [{"start_sec": 0.0, "end_sec": 5.5, "energy": "rising"}],
                        "title_sync_points": [2.0],
                        "transitions": [{"type": "cut", "why": "keeps training rhythm"}],
                        "story_hook": "students gather before training",
                        "payoff": "moves into basic training",
                    }]
                }),
                encoding="utf-8",
            )

            report = write_montage_design_review_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "montage_design_review.json").exists())


if __name__ == "__main__":
    unittest.main()
