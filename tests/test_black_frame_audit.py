import unittest

from video_pipeline_core import black_frame_audit as bfa
from video_pipeline_core.delivery_gate import evaluate_delivery_gate


def _bright(t):
    return {"t": t, "luma_avg": 120.0, "luma_range": 180.0}


def _black(t):
    return {"t": t, "luma_avg": 4.0, "luma_range": 6.0}


def _blank(t):
    return {"t": t, "luma_avg": 246.0, "luma_range": 4.0}


class FindDefectRunsTest(unittest.TestCase):
    def test_sustained_black_run_is_flagged(self):
        samples = [_bright(0.0), _black(0.5), _black(1.0), _black(1.5), _bright(2.0)]
        runs = bfa.find_defect_runs(samples, interval_sec=0.5, min_run_sec=0.4)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["kind"], "black")
        self.assertEqual(runs[0]["start_sec"], 0.5)
        self.assertEqual(runs[0]["duration_sec"], 1.5)

    def test_blank_white_card_is_flagged(self):
        samples = [_bright(0.0), _blank(0.5), _blank(1.0), _bright(1.5)]
        runs = bfa.find_defect_runs(samples, interval_sec=0.5, min_run_sec=0.4)
        self.assertEqual([r["kind"] for r in runs], ["blank"])

    def test_clean_footage_has_no_runs(self):
        samples = [_bright(t / 2) for t in range(8)]
        self.assertEqual(bfa.find_defect_runs(samples, interval_sec=0.5), [])

    def test_single_frame_blip_below_min_run_is_ignored(self):
        # one black sample = 0.25s of footage at fps=4, below the 0.4s floor
        samples = [_bright(0.0), _black(0.25), _bright(0.5)]
        runs = bfa.find_defect_runs(samples, interval_sec=0.25, min_run_sec=0.4)
        self.assertEqual(runs, [])

    def test_bright_but_textured_frame_is_not_blank(self):
        # high luma with wide spread (e.g. bright sky with detail) is legit
        samples = [{"t": 0.0, "luma_avg": 240.0, "luma_range": 90.0},
                   {"t": 0.5, "luma_avg": 240.0, "luma_range": 90.0}]
        self.assertEqual(bfa.find_defect_runs(samples, interval_sec=0.5), [])


class AuditTest(unittest.TestCase):
    def test_audit_uses_injected_sampler_and_reports_findings(self):
        samples = [_bright(0.0), _black(0.5), _black(1.0), _black(1.5)]
        result = bfa.audit_black_frames(
            "fake.mp4", sampler=lambda _p: samples, fps=2.0, min_run_sec=0.4,
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["findings"][0]["check"], "black_frame_run")
        self.assertEqual(result["next_action"], "fix_timeline_or_assembly")

    def test_clean_video_passes(self):
        result = bfa.audit_black_frames(
            "fake.mp4", sampler=lambda _p: [_bright(t / 2) for t in range(6)],
        )
        self.assertTrue(result["pass"])
        self.assertIsNone(result["next_action"])

    def test_unavailable_samples_fail_closed(self):
        result = bfa.audit_black_frames("missing.mp4", sampler=lambda _p: [])
        self.assertFalse(result["pass"])
        self.assertEqual(result["reason"], "sample_unavailable")
        self.assertEqual(result["next_action"], "verify_failed")


class DeliveryGateIntegrationTest(unittest.TestCase):
    def test_failed_black_frame_audit_blocks_delivery(self):
        gate = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "black_frame_audit": {"pass": False, "next_action": "fix_timeline_or_assembly"},
        })
        self.assertFalse(gate["pass"])
        self.assertEqual(gate["next_action"], "fix_timeline_or_assembly")
        self.assertTrue(any(b["artifact"] == "black_frame_audit" for b in gate["blocking"]))


if __name__ == "__main__":
    unittest.main()
