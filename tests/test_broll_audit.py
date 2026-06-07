"""broll_audit — Node 11 B-roll ratio / repeated-source audit (P1-A)."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import broll_audit as ba


def _clip(segment, src_path, dur, **kw):
    clip = {"segment": segment, "source_path": src_path, "duration_sec": dur}
    clip.update(kw)
    return clip


def _findings_by_check(result):
    return {f["check"] for f in result["findings"]}


class BrollAuditTest(unittest.TestCase):
    def test_metrics_computed(self):
        timeline = {"clips": [
            _clip(1, "local1.mp4", 4, source="local"),
            _clip(2, "stock1.mp4", 2, source="stock"),
            _clip(3, "stock2.mp4", 2, source="stock"),
        ]}
        result = ba.audit_broll(timeline)
        self.assertEqual(result["artifact_role"], "broll_audit")
        self.assertEqual(result["version"], 1)
        m = result["metrics"]
        # b-roll duration = 4 of 8 total
        self.assertAlmostEqual(m["broll_ratio"], 0.5)
        # 3 unique sources over 3 clips
        self.assertAlmostEqual(m["unique_source_ratio"], 1.0)
        self.assertEqual(m["max_source_repeats"], 1)

    def test_no_policy_passes_with_no_findings(self):
        timeline = {"clips": [
            _clip(1, "a.mp4", 3, source="stock"),
            _clip(2, "a.mp4", 3, source="stock"),
            _clip(3, "a.mp4", 3, source="stock"),
        ]}
        result = ba.audit_broll(timeline)
        self.assertTrue(result["pass"])
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["next_action"])

    def test_max_repeats_exceeded_fails_with_material_route(self):
        timeline = {"clips": [
            _clip(1, "a.mp4", 3, source="stock"),
            _clip(2, "a.mp4", 3, source="stock"),
            _clip(3, "a.mp4", 3, source="stock"),
        ]}
        result = ba.audit_broll(timeline, max_source_repeats=2)
        self.assertFalse(result["pass"])
        self.assertIn("max_source_repeats", _findings_by_check(result))
        repeat_finding = next(f for f in result["findings"]
                              if f["check"] == "max_source_repeats")
        self.assertEqual(repeat_finding["fix_class"], "material")
        self.assertIsNotNone(result["next_action"])

    def test_broll_ratio_exceeds_target_warns(self):
        timeline = {"clips": [
            _clip(1, "s1.mp4", 8, source="stock"),
            _clip(2, "l1.mp4", 2, source="local"),
        ]}
        result = ba.audit_broll(timeline, target_ratio=0.5)
        # warn does not block
        self.assertTrue(result["pass"])
        self.assertIn("broll_ratio", _findings_by_check(result))
        finding = next(f for f in result["findings"] if f["check"] == "broll_ratio")
        self.assertEqual(finding["level"], "warn")

    def test_parameterized_broll_sources_no_hardcoded_keywords(self):
        # caller defines what counts as b-roll; module ships no creator keyword map
        timeline = {"clips": [
            _clip(1, "g1.mp4", 5, source="generated"),
            _clip(2, "l1.mp4", 5, source="local"),
        ]}
        # treat only "generated" as b-roll
        result = ba.audit_broll(timeline, broll_sources=["generated"])
        self.assertAlmostEqual(result["metrics"]["broll_ratio"], 0.5)
        # confirm module exposes no built-in keyword/preference map
        self.assertFalse(hasattr(ba, "CREATOR_KEYWORDS"))
        self.assertFalse(hasattr(ba, "DEFAULT_BROLL_RATIO"))

    def test_explicit_is_broll_flag_respected(self):
        timeline = {"clips": [
            _clip(1, "x.mp4", 5, is_broll=True),
            _clip(2, "y.mp4", 5, is_broll=False),
        ]}
        result = ba.audit_broll(timeline)
        self.assertAlmostEqual(result["metrics"]["broll_ratio"], 0.5)

    def test_writer_outputs_stable_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "broll_audit.json"
            result = ba.write_broll_audit({"clips": []}, p)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(result["broll_audit"], str(p))
            self.assertEqual(saved["artifact_role"], "broll_audit")
            self.assertTrue(saved["pass"])


if __name__ == "__main__":
    unittest.main()
