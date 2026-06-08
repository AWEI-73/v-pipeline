"""Integration: contract -> adapter -> Node 9 assembly -> Node 11 treatment audit.

Locks the wiring that makes material treatment live in the build chain:
the adapter passes content_pattern/material_treatment through, build_assembly_plan
resolves a treatment + n_required (opt-in), and audit_treatment catches a
collapsed enumeration.
"""
import json
import unittest
from pathlib import Path

from video_pipeline_core import contract_adapter, edit_artifacts, treatment_audit

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "examples" / "genre_tests" / "treatment_demo" / "segment_contract.json"


def _seg(plan, sid):
    return next(s for s in plan["segments"] if s["segment"] == sid)


class TreatmentIntegrationTests(unittest.TestCase):
    def setUp(self):
        contract = json.loads(DEMO.read_text(encoding="utf-8"))
        self.script = contract_adapter.contract_to_mv_script(contract)
        self.plan = edit_artifacts.build_assembly_plan(self.script)

    def test_adapter_passthrough(self):
        s2 = next(s for s in self.script["segments"] if s["segment"] == 2)
        self.assertEqual((s2.get("editing_intent") or {}).get("content_pattern"), "enumeration")
        self.assertEqual((s2.get("material_treatment") or {}).get("items"),
                         ["Ethiopia", "Colombia", "Guatemala"])

    def test_node9_resolves_enumeration(self):
        s2 = _seg(self.plan, 2)
        self.assertEqual(s2["treatment"], "photo_stack_beat")
        self.assertEqual(s2["n_required"], 3)
        self.assertTrue(s2["label_per_item"])
        self.assertEqual(s2["lane_plan"]["subtitle"], "per_item_label")

    def test_emotional_segments_opt_into_single_hold(self):
        # seg1/seg3 declare content_pattern=emotional -> single_hold, n_required 1
        for sid in (1, 3):
            s = _seg(self.plan, sid)
            self.assertEqual(s["treatment"], "single_hold")
            self.assertEqual(s["n_required"], 1)

    def test_audit_fails_on_collapsed_enumeration(self):
        collapsed = [
            {"segment": 1, "source": "open.mp4", "duration_sec": 4, "timeline_in": 0},
            {"segment": 2, "source": "beans.mp4", "duration_sec": 3, "timeline_in": 4},
            {"segment": 3, "source": "done.mp4", "duration_sec": 4, "timeline_in": 7},
        ]
        tl = edit_artifacts.build_timeline_build(collapsed)
        audit = treatment_audit.audit_treatment(self.plan, tl)
        self.assertFalse(audit["pass"])
        checks = {f["check"] for f in audit["findings"] if f["level"] == "fail"}
        self.assertIn("treatment_fit", checks)

    def test_audit_passes_on_proper_stack(self):
        proper = [
            {"segment": 1, "source": "open.mp4", "duration_sec": 4, "timeline_in": 0},
            {"segment": 2, "source": "b1.jpg", "duration_sec": 0.7, "timeline_in": 4.0, "text": "Ethiopia"},
            {"segment": 2, "source": "b2.jpg", "duration_sec": 0.7, "timeline_in": 4.7, "text": "Colombia"},
            {"segment": 2, "source": "b3.jpg", "duration_sec": 0.7, "timeline_in": 5.4, "text": "Guatemala"},
            {"segment": 3, "source": "done.mp4", "duration_sec": 4, "timeline_in": 6.1},
        ]
        tl = edit_artifacts.build_timeline_build(proper)
        audit = treatment_audit.audit_treatment(self.plan, tl)
        self.assertTrue(audit["pass"])

    def test_write_edit_artifacts_emits_treatment_audit(self):
        import tempfile
        render_plan = [
            {"segment": 1, "source": "open.mp4", "duration_sec": 4, "timeline_in": 0},
            {"segment": 2, "source": "beans.mp4", "duration_sec": 3, "timeline_in": 4},
            {"segment": 3, "source": "done.mp4", "duration_sec": 4, "timeline_in": 7},
        ]
        with tempfile.TemporaryDirectory() as d:
            res = edit_artifacts.write_edit_artifacts(self.script, out_dir=d, render_plan=render_plan)
            self.assertIn("treatment_audit", res)
            self.assertTrue(Path(res["treatment_audit"]).exists())


if __name__ == "__main__":
    unittest.main()
