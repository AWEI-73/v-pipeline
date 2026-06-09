"""Tests for pacing_review — the gold-calibrated pacing gate."""
import unittest

from video_pipeline_core import pacing_review as pr


def _tl(durs):
    return {"clips": [{"segment": i + 1, "duration_sec": d} for i, d in enumerate(durs)]}


class TestPacingReview(unittest.TestCase):
    def test_bakery_disaster_fails(self):
        # the real bakery smoke_test profile: 43 / 0.4 / 1.5 / 53 s (mech verify gave 95.5)
        r = pr.review_pacing(_tl([43.4, 0.4, 1.5, 53.5]), mode="promo", target_sec=30)
        self.assertFalse(r["pass"])
        self.assertLess(r["score"], 70)
        checks = {f["dimension"] for f in r["findings"] if f["level"] == "error"}
        self.assertIn("hold_discipline", checks)   # the 43s/53s dead holds
        self.assertIn("flash_avoidance", checks)   # the 0.4s flash
        self.assertIn("duration_fit", checks)      # 99s vs 30s

    def test_sane_promo_passes(self):
        r = pr.review_pacing(_tl([3.8, 2.0, 2.5, 3.0, 1.9, 2.3, 2.8, 2.5, 3.0, 2.4, 3.5, 2.3]),
                             mode="promo", target_sec=30)
        self.assertTrue(r["pass"])
        self.assertGreaterEqual(r["score"], 90)
        self.assertEqual(r["findings"], [])

    def test_justified_long_hold_not_penalized(self):
        # a long group-photo hold WITH a payoff reason should not be a dead-hold error
        tl = {"clips": [
            {"segment": 1, "duration_sec": 3.0},
            {"segment": 2, "duration_sec": 11.0, "hold_reason": "group_photo"},
            {"segment": 3, "duration_sec": 3.0},
        ]}
        r = pr.review_pacing(tl, mode="warm_documentary", target_sec=17)
        self.assertFalse(any(f["dimension"] == "hold_discipline" and f["level"] == "error"
                             for f in r["findings"]))

    def test_empty_timeline_fails(self):
        r = pr.review_pacing({"clips": []}, mode="promo")
        self.assertFalse(r["pass"])
        self.assertEqual(r["score"], 0)


if __name__ == "__main__":
    unittest.main()
