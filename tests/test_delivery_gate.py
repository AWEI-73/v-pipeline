import unittest

from video_pipeline_core.delivery_gate import evaluate_delivery_gate


class DeliveryGateTest(unittest.TestCase):
    def test_failed_existing_audit_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "broll_audit": {"pass": False, "next_action": "curator"},
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["next_action"], "curator")
        self.assertEqual(result["blocking"][0]["rule"], "failed_audit")

    def test_failed_new_visual_information_audit_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "new_visual_information_audit": {"pass": False, "next_action": "curator"},
        })
        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["artifact"], "new_visual_information_audit")

    def test_unresolved_material_gap_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "material_coverage": {
                "gaps": [{"segment": 7, "must_include": False, "reason": "no live-line footage"}]
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["next_action"], "await_material")
        self.assertEqual(result["blocking"][0]["rule"], "unresolved_gap")

    def test_all_present_gates_pass(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "broll_audit": {"pass": True},
            "editorial_qa": {"pass": True},
            "material_coverage": {"gaps": []},
        })

        self.assertTrue(result["pass"])
        self.assertIsNone(result["next_action"])

    def test_quality_evidence_does_not_block_delivery(self):
        quality_roles = (
            "visual_audit",
            "presentation_feel_audit",
            "treatment_audit",
            "visual_fatigue_audit",
            "semantic_novelty_audit",
            "action_progression_audit",
            "editorial_qa",
        )
        result = evaluate_delivery_gate({
            role: {"pass": False, "next_action": "dashboard_review"}
            for role in quality_roles
        })
        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])
