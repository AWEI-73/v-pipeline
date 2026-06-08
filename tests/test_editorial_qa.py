"""Tests for video_pipeline_core.editorial_qa.

Covers:
  - review_editorial (mode inconsistency warning)
  - review_editorial (successful mock case)
  - review_editorial (treatment audit failure propagation)
  - review_editorial (visual fatigue audit warning/failure propagation)
  - review_editorial (blueprint coverage check failure)
  - review_editorial (technical verification failure propagation)
"""
import unittest

from video_pipeline_core.editorial_qa import review_editorial


class TestEditorialQa(unittest.TestCase):
    """Test editorial QA cross-artifact validator."""

    def test_review_editorial_pass_clean(self):
        artifacts = {
            "brief": {"mode": "warm_documentary"},
            "assembly_plan": {"mode": "warm_documentary"},
            "timeline_build": {"mode": "warm_documentary"},
            "treatment_audit": {"pass": True, "findings": []},
            "visual_fatigue_audit": {"pass": True, "findings": []},
            "blueprint_coverage": {"pass": True},
            "verify_result": {"pass": True, "score": 95},
        }
        res = review_editorial(artifacts)
        self.assertTrue(res["pass"])
        self.assertEqual(res["score"], 100)
        self.assertEqual(len(res["findings"]), 0)
        for val in res["dimensions"].values():
            self.assertEqual(val, 100)

    def test_review_editorial_mode_inconsistency(self):
        artifacts = {
            "brief": {"mode": "warm_documentary"},
            "assembly_plan": {"mode": "rhythmic_mv"},
            "timeline_build": {"mode": "warm_documentary"},
        }
        res = review_editorial(artifacts)
        self.assertTrue(res["pass"])  # Warnings only
        self.assertLess(res["score"], 100)
        findings = [f for f in res["findings"] if f["dimension"] == "artifact_consistency"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")

    def test_review_editorial_treatment_audit_propagation(self):
        artifacts = {
            "treatment_audit": {
                "pass": False,
                "findings": [
                    {
                        "check": "treatment_fit",
                        "level": "fail",
                        "message": "stack collapsed",
                        "route": "editor",
                    }
                ],
            }
        }
        res = review_editorial(artifacts)
        self.assertFalse(res["pass"])
        self.assertLess(res["score"], 100)
        findings = [f for f in res["findings"] if f["dimension"] == "visual_variety_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")
        self.assertEqual(findings[0]["route"], "editor")

    def test_review_editorial_visual_fatigue_propagation(self):
        artifacts = {
            "visual_fatigue_audit": {
                "pass": False,
                "findings": [
                    {
                        "check": "still_image_fatigue",
                        "level": "fail",
                        "message": "still image hold time exceeds limit",
                        "route": "editor/effects-director",
                    },
                    {
                        "check": "pacing_fit",
                        "level": "warn",
                        "message": "pacing range mismatch",
                        "route": "editor",
                    },
                ],
            }
        }
        res = review_editorial(artifacts)
        self.assertFalse(res["pass"])
        self.assertLess(res["score"], 100)
        self.assertEqual(res["dimensions"]["effects_fit"], 90)  # deducted 10
        self.assertEqual(res["dimensions"]["pacing_fit"], 97)   # deducted 3

    def test_review_editorial_blueprint_coverage_failure(self):
        artifacts = {
            "blueprint_coverage": {"pass": False},
        }
        res = review_editorial(artifacts)
        self.assertTrue(res["pass"])  # only warning
        self.assertEqual(res["dimensions"]["narrative_coherence"], 85)

    def test_review_editorial_technical_verify_failure(self):
        artifacts = {
            "verify_result": {"pass": False, "score": 45.0},
        }
        res = review_editorial(artifacts)
        self.assertFalse(res["pass"])
        self.assertEqual(res["dimensions"]["artifact_consistency"], 80)


if __name__ == "__main__":
    unittest.main()
