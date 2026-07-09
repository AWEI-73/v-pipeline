import unittest

from video_pipeline_core.reviewer_registry import (
    detect_review_signature,
    sign_review,
    validate_review_artifact,
)
from video_pipeline_core.effect_director_review import evaluate_effect_director_review
from video_pipeline_core.montage_design_review import evaluate_montage_design_review


class ReviewSignatureTest(unittest.TestCase):
    def test_sign_review_pass_validates(self):
        sig = sign_review("effect_director", passed=True, findings=[])
        self.assertEqual(sig["artifact_role"], "artifact_review")
        self.assertEqual(sig["reviewer_role"], "effect_director")
        self.assertEqual(sig["decision"], "pass")
        self.assertEqual(sig["gate_strength"], "hard_gate")
        self.assertTrue(validate_review_artifact(sig)["ok"])

    def test_sign_review_fail_hard_gate_blocks(self):
        sig = sign_review("effect_director", passed=False, findings=[{"rule": "x"}])
        self.assertEqual(sig["decision"], "block")
        self.assertTrue(validate_review_artifact(sig)["ok"])

    def test_sign_review_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            sign_review("not_a_role", passed=True)

    def test_detect_review_signature_roundtrip(self):
        sig = sign_review("montage_design_reviewer", passed=True)
        self.assertIsNotNone(detect_review_signature({"review_signature": sig}))
        self.assertIsNotNone(detect_review_signature(sig))
        self.assertIsNone(detect_review_signature({"artifact_role": "montage_design_review"}))
        self.assertIsNone(detect_review_signature(None))

    def test_effect_director_review_carries_valid_signature(self):
        report = evaluate_effect_director_review({"review_basis": "metadata_only"})
        sig = detect_review_signature(report)
        self.assertIsNotNone(sig)
        self.assertEqual(sig["reviewer_role"], "effect_director")
        # metadata_only cannot pass -> signed as a hard block
        self.assertFalse(report["pass"])
        self.assertEqual(sig["decision"], "block")

    def test_montage_design_review_carries_valid_signature(self):
        report = evaluate_montage_design_review({"montages": []})
        sig = detect_review_signature(report)
        self.assertIsNotNone(sig)
        self.assertEqual(sig["reviewer_role"], "montage_design_reviewer")
        self.assertFalse(report["pass"])


if __name__ == "__main__":
    unittest.main()
