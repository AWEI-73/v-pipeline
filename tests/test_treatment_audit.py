"""Tests for video_pipeline_core.treatment_audit.

Covers:
  - treatment_fit (collapsed stack, wrong count, bridge collapse, single_hold chopped)
  - label_pairing (missing labels on photo_stack_beat or label_per_item)
  - beat_lock (alignment to beat grid timestamps)
  - audit_treatment orchestrator return shape and status
"""
import unittest

from video_pipeline_core.treatment_audit import audit_treatment


class TestTreatmentFit(unittest.TestCase):
    """Audits the fit/structure between declared treatment and rendered clips."""

    def test_photo_stack_beat_collapsed_to_single_hold(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "n_required": 3,
                }
            ]
        }
        # Rendered as 1 clip -> collapsed stack (fail)
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "label": "Eth"}
            ]
        }
        res = audit_treatment(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")
        self.assertEqual(findings[0]["route"], "editor")

    def test_photo_stack_beat_mismatch_count(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "n_required": 3,
                }
            ]
        }
        # Rendered as 2 clips instead of 3 (fail)
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "label": "Eth"},
                {"segment": 1, "source_path": "b.jpg", "label": "Col"},
            ]
        }
        res = audit_treatment(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")

    def test_photo_stack_beat_correct(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "n_required": 3,
                }
            ]
        }
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "label": "Eth"},
                {"segment": 1, "source_path": "b.jpg", "label": "Col"},
                {"segment": 1, "source_path": "c.jpg", "label": "Gua"},
            ]
        }
        res = audit_treatment(plan, build)
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 0)

    def test_quick_cut_bridge_collapsed(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "quick_cut_bridge",
                    "n_required": 3,
                }
            ]
        }
        # Rendered as 1 clip -> collapsed bridge (fail)
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4"}
            ]
        }
        res = audit_treatment(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")

    def test_quick_cut_bridge_correct(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "quick_cut_bridge",
                    "n_required": 3,
                }
            ]
        }
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.mp4"},
                {"segment": 1, "source_path": "b.mp4"},
            ]
        }
        res = audit_treatment(plan, build)
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 0)

    def test_single_hold_chopped(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "single_hold",
                    "n_required": 1,
                }
            ]
        }
        # Single hold segment split into multiple clips -> warn
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg"},
                {"segment": 1, "source_path": "b.jpg"},
            ]
        }
        res = audit_treatment(plan, build)
        # Note: warn does not fail the audit
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "treatment_fit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "editor")


class TestLabelPairing(unittest.TestCase):
    """Audits that per-item-label/stack treatments carry labels on timeline clips."""

    def test_photo_stack_beat_missing_label(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "n_required": 2,
                }
            ]
        }
        # One clip lacks a label or text_overlay (fail)
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "label": "Eth"},
                {"segment": 1, "source_path": "b.jpg"},
            ]
        }
        res = audit_treatment(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "label_pairing"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "fail")
        self.assertEqual(findings[0]["route"], "writer")

    def test_label_per_item_explicit_missing_label(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "stepped_sequence",
                    "label_per_item": True,
                    "n_required": 1,
                }
            ]
        }
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "text_overlay": "none"},
            ]
        }
        res = audit_treatment(plan, build)
        self.assertFalse(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "label_pairing"]
        self.assertEqual(len(findings), 1)

    def test_label_pairing_via_text_overlay(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "n_required": 1,
                }
            ]
        }
        # Passes if text_overlay is not "none" or absent
        build = {
            "clips": [
                {"segment": 1, "source_path": "a.jpg", "text_overlay": "Beans from Eth"},
            ]
        }
        res = audit_treatment(plan, build)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "label_pairing"]
        self.assertEqual(len(findings), 0)


class TestBeatLock(unittest.TestCase):
    """Audits alignment of stack/bridge cut times to the beat grid."""

    def test_beat_lock_aligned(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "beat_grid": [0.5, 1.0, 1.5],
                }
            ]
        }
        # timeline_in_sec aligned within tolerance (0.15s)
        build = {
            "clips": [
                {"segment": 1, "timeline_in_sec": 0.45, "label": "Eth"},
                {"segment": 1, "timeline_in_sec": 1.05, "label": "Col"},
            ]
        }
        res = audit_treatment(plan, build, beat_tolerance_sec=0.15)
        self.assertTrue(res["pass"])
        findings = [f for f in res["findings"] if f["check"] == "beat_lock"]
        self.assertEqual(len(findings), 0)

    def test_beat_lock_misaligned(self):
        plan = {
            "segments": [
                {
                    "segment": 1,
                    "treatment": "photo_stack_beat",
                    "beat_grid": [0.5, 1.0, 1.5],
                }
            ]
        }
        # One clip is misaligned (0.8s is not close to 0.5, 1.0, 1.5)
        build = {
            "clips": [
                {"segment": 1, "timeline_in_sec": 0.5, "label": "Eth"},
                {"segment": 1, "timeline_in_sec": 0.8, "label": "Col"},
            ]
        }
        res = audit_treatment(plan, build, beat_tolerance_sec=0.15)
        self.assertTrue(res["pass"])  # Warn level does not cause pass=False
        findings = [f for f in res["findings"] if f["check"] == "beat_lock"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["route"], "editor")


class TestGeneralAudit(unittest.TestCase):
    """Checks overall return shape of audit_treatment."""

    def test_return_shape(self):
        plan = {"segments": []}
        build = {"clips": []}
        res = audit_treatment(plan, build)
        self.assertEqual(res["artifact_role"], "treatment_audit")
        self.assertEqual(res["version"], 1)
        self.assertTrue(res["pass"])
        self.assertEqual(res["findings"], [])


if __name__ == "__main__":
    unittest.main()
