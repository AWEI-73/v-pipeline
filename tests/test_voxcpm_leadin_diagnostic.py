import unittest

from video_pipeline_core.voxcpm_leadin_diagnostic import (
    classify_provider_leadin,
    plan_diagnostic_matrix,
)


class VoxCPMLeadInDiagnosticTest(unittest.TestCase):
    def test_matrix_contains_required_variants(self):
        matrix = plan_diagnostic_matrix()
        labels = {item["label"] for item in matrix}
        self.assertIn("starts_zhe_yi_tian_calm_ascii_path", labels)
        self.assertIn("starts_basic_training_blank_style", labels)
        self.assertIn("starts_basic_training_repeat_1", labels)
        self.assertIn("starts_basic_training_repeat_2", labels)

    def test_classifies_blocked_without_safe_trim(self):
        result = classify_provider_leadin(
            [
                {"lead_in_qa_pass": False, "detected_extra_leadin": "抗"},
                {"lead_in_qa_pass": False, "detected_extra_leadin": "康"},
            ],
            {"safe_trim_available": False},
        )

        self.assertEqual(result["classification"], "provider_blocked_no_safe_fix")
        self.assertFalse(result["safe_for_production"])


if __name__ == "__main__":
    unittest.main()
