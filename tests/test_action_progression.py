import unittest

from video_pipeline_core import action_progression as ap
from video_pipeline_core.delivery_gate import evaluate_delivery_gate


class ClassifyFunctionTest(unittest.TestCase):
    def test_caption_keywords_classify_bilingually(self):
        self.assertEqual(ap.classify_function("空拍校門全景"), "establish")
        self.assertEqual(ap.classify_function("學員攀爬電桿施工"), "action")
        self.assertEqual(ap.classify_function("工具與手部特寫"), "detail")
        self.assertEqual(ap.classify_function("頒發證書 完成訓練"), "result")
        self.assertEqual(ap.classify_function("wide aerial overview of the venue"), "establish")

    def test_motion_fallback_when_no_caption(self):
        self.assertEqual(ap.classify_function("", motion_peaks=[1.0, 2.0, 3.0]), "action")
        self.assertEqual(ap.classify_function(None, motion_peaks=[], duration_sec=5.0), "establish")
        self.assertIsNone(ap.classify_function("", motion_peaks=[], duration_sec=1.0))


class AuditTest(unittest.TestCase):
    def _segment(self, sid, required, clip_funcs):
        return {
            "segment": sid,
            "sequence_grammar": {"required_functions": required},
            "clips": [{"function": fn} for fn in clip_funcs],
        }

    def test_full_spine_coverage_passes(self):
        seg = self._segment(1, ["establish", "action", "result"],
                            ["establish", "action", "detail", "result"])
        result = ap.audit_action_progression([seg])
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["action_phase_coverage"], 1.0)

    def test_missing_spine_phase_fails(self):
        seg = self._segment(3, ["establish", "action", "result"],
                            ["action", "action", "action"])
        result = ap.audit_action_progression([seg])
        self.assertFalse(result["pass"])
        self.assertIn("establish", result["findings"][0]["missing_spine"])
        self.assertIn("result", result["findings"][0]["missing_spine"])

    def test_segments_without_required_functions_are_ignored(self):
        result = ap.audit_action_progression([{"segment": 1, "clips": [{"function": "action"}]}])
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["segments_reviewed"], 0)

    def test_classifies_from_caption_when_function_absent(self):
        seg = {
            "segment": 2,
            "sequence_grammar": {"required_functions": ["establish", "action"]},
            "clips": [{"caption": "空拍全景"}, {"caption": "學員施工操作"}],
        }
        result = ap.audit_action_progression([seg])
        self.assertTrue(result["pass"])


class DeliveryGateIntegrationTest(unittest.TestCase):
    def test_failed_action_progression_blocks_delivery(self):
        gate = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "action_progression_audit": {"pass": False, "next_action": "fix_timeline_or_assembly"},
        })
        self.assertFalse(gate["pass"])
        self.assertTrue(any(b["artifact"] == "action_progression_audit" for b in gate["blocking"]))


if __name__ == "__main__":
    unittest.main()
