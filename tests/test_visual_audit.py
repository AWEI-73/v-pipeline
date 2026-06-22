"""visual_audit — Node 12 keyframe-grid evidence + optional model lineage (P1-B)."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import visual_audit as va
from video_pipeline_core import model_routing


def _grid_meta(n=4):
    return {
        "grid": "keyframe_grid.jpg",
        "grid_path": "/run/keyframe_grid.jpg",
        "columns": 2,
        "rows": 2,
        "sample_count": n,
        "duration_sec": 12.0,
        "samples": [{"timestamp_sec": float(i), "cell": i + 1} for i in range(n)],
    }


class VisualAuditMechanicalTest(unittest.TestCase):
    def test_mechanical_only_without_model(self):
        result = va.audit_visual(_grid_meta(4))
        self.assertEqual(result["artifact_role"], "visual_audit")
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["grid"], "keyframe_grid.jpg")
        self.assertEqual(len(result["samples"]), 4)
        self.assertIsNone(result["model_review"])  # mechanical-only
        self.assertTrue(result["pass"])
        self.assertIsNone(result["next_action"])

    def test_empty_grid_flags_mechanical_finding(self):
        result = va.audit_visual(_grid_meta(0))
        self.assertFalse(result["pass"])
        checks = {f["check"] for f in result["mechanical_findings"]}
        self.assertIn("keyframes_present", checks)
        self.assertIsNotNone(result["next_action"])


class VisualAuditModelTest(unittest.TestCase):
    def test_model_lineage_recorded_from_routes(self):
        routes = model_routing.default_model_routes()
        seen = {}

        def reviewer(grid_meta):
            seen["called"] = True
            return []  # no problems found

        result = va.audit_visual(_grid_meta(4), model_routes=routes, reviewer=reviewer)
        self.assertTrue(seen.get("called"))
        mr = result["model_review"]
        self.assertIsNotNone(mr)
        self.assertEqual(mr["provider"], "agent")
        self.assertEqual(mr["model"], "codex_or_hermes")
        self.assertEqual(mr["findings"], [])
        self.assertTrue(result["pass"])

    def test_model_mismatch_finding_routes(self):
        routes = model_routing.default_model_routes()

        def reviewer(grid_meta):
            return [{"level": "fail", "cell": 2, "timestamp_sec": 1.0,
                     "note": "visual does not match narrative"}]

        result = va.audit_visual(_grid_meta(4), model_routes=routes, reviewer=reviewer)
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["model_review"]["findings"]), 1)
        self.assertIsNotNone(result["next_action"])

    def test_no_hardcoded_ollama_when_disabled(self):
        # Without a reviewer, no provider assumption is made at all.
        result = va.audit_visual(_grid_meta(4), model_routes=None, reviewer=None)
        self.assertIsNone(result["model_review"])


class VisualAuditWriterTest(unittest.TestCase):
    def test_writer_outputs_stable_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "visual_audit.json"
            result = va.write_visual_audit(_grid_meta(2), p)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(result["visual_audit"], str(p))
            self.assertEqual(saved["artifact_role"], "visual_audit")
            self.assertEqual(len(saved["samples"]), 2)


if __name__ == "__main__":
    unittest.main()
