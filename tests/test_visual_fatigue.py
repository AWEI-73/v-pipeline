"""Tests for video_pipeline_core.visual_fatigue.

Covers:
  - single_source_fatigue (pass with reason, fail without)
  - still_image_fatigue (pass with treatment/reason, fail without)
  - shot_density_fit (pass >= min_shots, warn otherwise)
  - source_repetition (pass within limits, warn reuse/cooldown gap)
  - pacing_fit (pass within bounds/reason, warn outside)
"""
import unittest

from video_pipeline_core.visual_fatigue import audit_visual_fatigue


class TestSingleSourceFatigue(unittest.TestCase):
    """Test same-source consecutive duration limits."""

    def test_single_source_fatigue_fail(self):
        plan = {"mode": "rhythmic_mv", "segments": [{"segment": 1}]}
        # rhythmic_mv max single source is 6s.
        # Two consecutive clips total 7s of 'a.mp4' without any reason.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0},
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 3.0, "timeline_in_sec": 4.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "single_source_fatigue"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")
        self.assertEqual(findings[0]["route"], "editor")

    def test_single_source_fatigue_pass_with_reason(self):
        plan = {"mode": "rhythmic_mv", "segments": [{"segment": 1}]}
        # One clip has reason, so it should pass.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0, "shot_reason": "long cut action"},
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 3.0, "timeline_in_sec": 4.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "single_source_fatigue"]
        self.assertEqual(len(findings), 0)


class TestStillImageFatigue(unittest.TestCase):
    """Test hold limits for photos/stills."""

    def test_still_image_fatigue_fail(self):
        plan = {"mode": "rhythmic_mv", "segments": [{"segment": 1}]}
        # rhythmic_mv max still hold is 3s.
        # Photo 'p.jpg' held for 5s with no reason or treatment.
        build = {
            "clips": [
                {"segment": 1, "source_path": "p.jpg", "duration_sec": 5.0, "timeline_in_sec": 0.0}
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "still_image_fatigue"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")
        self.assertEqual(findings[0]["route"], "editor/effects-director")

    def test_still_image_fatigue_pass_with_treatment(self):
        plan = {"mode": "rhythmic_mv", "segments": [{"segment": 1}]}
        # Held 5s, but has a still treatment -> pass.
        build = {
            "clips": [
                {
                    "segment": 1,
                    "source_path": "p.jpg",
                    "duration_sec": 5.0,
                    "timeline_in_sec": 0.0,
                    "still_treatment": {"mode": "slow_push"},
                }
            ]
        }
        res = audit_visual_fatigue(plan, build)
        # Note: it will warn about pacing_fit (5s is outside [1.5, 4.0] for rhythmic_mv)
        # but the still_image_fatigue check should be clean.
        still_findings = [f for f in res["findings"] if f["check"] == "still_image_fatigue"]
        self.assertEqual(len(still_findings), 0)

    def test_still_image_fatigue_pass_with_reason(self):
        plan = {"mode": "rhythmic_mv", "segments": [{"segment": 1}]}
        # Held 5s, but has reason -> pass.
        build = {
            "clips": [
                {
                    "segment": 1,
                    "source_path": "p.jpg",
                    "duration_sec": 5.0,
                    "timeline_in_sec": 0.0,
                    "reason": "showing high resolution proof detail",
                }
            ]
        }
        res = audit_visual_fatigue(plan, build)
        still_findings = [f for f in res["findings"] if f["check"] == "still_image_fatigue"]
        self.assertEqual(len(still_findings), 0)


    def test_creative_exception_keeps_still_fatigue_as_acknowledged_warning(self):
        exception = {
            "rule_bent": "still_image_fatigue",
            "reason": "The still is the only proof image.",
            "risk": "The hold may feel static.",
            "requires_review": True,
        }
        plan = {"mode": "rhythmic_mv", "segments": [{
            "segment": 1,
            "creative_exception": exception,
        }]}
        build = {"clips": [{
            "segment": 1,
            "source_path": "p.jpg",
            "duration_sec": 5.0,
            "timeline_in_sec": 0.0,
        }]}

        res = audit_visual_fatigue(plan, build)

        finding = next(f for f in res["findings"] if f["check"] == "still_image_fatigue")
        self.assertTrue(res["pass"])
        self.assertEqual(finding["level"], "warn")
        self.assertTrue(finding["acknowledged_exception"])
        self.assertEqual(finding["creative_exception"], exception)


class TestShotDensityFit(unittest.TestCase):
    """Test shot density within segments."""

    def test_shot_density_fit_warn(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}]}
        # Only 1 clip in segment 1, but default min_shots_per_segment is 2.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 5.0, "timeline_in_sec": 0.0}
            ]
        }
        res = audit_visual_fatigue(plan, build)
        # Warning does not fail the audit
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "shot_density_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "editor")

    def test_shot_density_fit_pass(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}]}
        # 2 clips in segment 1 -> pass
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0},
                {"segment": 1, "source_path": "b.mp4", "duration_sec": 4.0, "timeline_in_sec": 4.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        findings = [f for f in res["findings"] if f["check"] == "shot_density_fit"]
        self.assertEqual(len(findings), 0)


class TestSourceRepetition(unittest.TestCase):
    """Test source repetition limits and cooldown gaps."""

    def test_source_repetition_max_reuse_warn(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}, {"segment": 2}, {"segment": 3}]}
        # 'a.mp4' used across 3 segments, max_reuse_per_run is 2.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0},
                {"segment": 2, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 4.0},
                {"segment": 3, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 8.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "source_repetition" and "exceeding the limit" in f["message"]]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "curator")

    def test_source_repetition_cooldown_warn(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}, {"segment": 2}]}
        # 'a.mp4' is used, then another source 'b.mp4', then 'a.mp4' is reused.
        # The end of first 'a' is 4s, the start of second 'a' is 8s. Gap is 4s.
        # 4s gap is less than default cooldown (25s) -> warn.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0},
                {"segment": 1, "source_path": "b.mp4", "duration_sec": 4.0, "timeline_in_sec": 4.0},
                {"segment": 2, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 8.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "source_repetition" and "reused too soon" in f["message"]]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "curator")

    def test_source_repetition_pass(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}, {"segment": 2}]}
        # 'a.mp4' is used once, 'b.mp4' is used once -> pass.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 4.0, "timeline_in_sec": 0.0},
                {"segment": 2, "source_path": "b.mp4", "duration_sec": 4.0, "timeline_in_sec": 4.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        findings = [f for f in res["findings"] if f["check"] == "source_repetition"]
        self.assertEqual(len(findings), 0)


class TestPacingFit(unittest.TestCase):
    """Test shot durations alignment with mode pacing bounds."""

    def test_pacing_fit_warn(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}]}
        # warm_documentary target range is [4.0, 8.0].
        # Clip is 3s with no reason -> warn.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 3.0, "timeline_in_sec": 0.0},
                {"segment": 1, "source_path": "b.mp4", "duration_sec": 5.0, "timeline_in_sec": 3.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "pacing_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "editor")

    def test_pacing_fit_pass_with_reason(self):
        plan = {"mode": "warm_documentary", "segments": [{"segment": 1}]}
        # Clip is 3s, but has a reason -> pass.
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 3.0, "timeline_in_sec": 0.0, "reason": "fast reaction cut"},
                {"segment": 1, "source_path": "b.mp4", "duration_sec": 5.0, "timeline_in_sec": 3.0},
            ]
        }
        res = audit_visual_fatigue(plan, build)
        findings = [f for f in res["findings"] if f["check"] == "pacing_fit"]
        self.assertEqual(len(findings), 0)

    def test_narration_led_still_hold_uses_attention_budget(self):
        plan = {
            "mode": "rhythmic_mv",
            "segments": [{
                "segment": 1,
                "treatment": "single_hold",
                "execution_plan": {
                    "narration": {"mode": "voiceover"},
                    "music": {"intensity": "low"},
                },
            }],
        }
        build = {"clips": [{
            "segment": 1,
            "source_path": "p.jpg",
            "duration_sec": 6.0,
            "timeline_in_sec": 0.0,
        }]}

        res = audit_visual_fatigue(plan, build)

        self.assertFalse(any(f["check"] == "still_image_fatigue" for f in res["findings"]))
        self.assertFalse(any(f["check"] == "attention_budget_fit" for f in res["findings"]))

    def test_music_led_untreated_still_over_two_seconds_fails_attention_budget(self):
        plan = {
            "mode": "rhythmic_mv",
            "segments": [{
                "segment": 1,
                "treatment": "single_hold",
                "still_motion": "none",
                "execution_plan": {
                    "narration": {"mode": "none"},
                    "music": {"intensity": "medium"},
                },
            }],
        }
        build = {"clips": [{
            "segment": 1,
            "source_path": "p.jpg",
            "duration_sec": 3.0,
            "timeline_in_sec": 0.0,
        }]}

        res = audit_visual_fatigue(plan, build)

        finding = next(f for f in res["findings"] if f["check"] == "attention_budget_fit")
        self.assertEqual(finding["level"], "fail")
        self.assertEqual(finding["route"], "editor/effects-director")


if __name__ == "__main__":
    unittest.main()
