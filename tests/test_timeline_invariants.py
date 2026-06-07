"""timeline_invariants — Node 11 deterministic timeline audit (P1-A)."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import timeline_invariants as ti


def _clip(segment, source, start, dur, timeline_in, **kw):
    clip = {
        "segment": segment,
        "source_path": source,
        "start_sec": start,
        "end_sec": start + dur,
        "duration_sec": dur,
        "timeline_in_sec": timeline_in,
        "timeline_out_sec": timeline_in + dur,
        "trace": {"segment_contract_segment": segment},
    }
    clip.update(kw)
    return clip


def _checks_by_name(result):
    return {c["name"]: c for c in result["checks"]}


class TimelineInvariantsTest(unittest.TestCase):
    def test_clean_timeline_passes(self):
        timeline = {"clips": [
            _clip(1, "a.mp4", 0, 3, 0),
            _clip(2, "b.mp4", 10, 2, 3),
        ]}
        result = ti.audit_timeline(timeline)
        self.assertTrue(result["pass"])
        self.assertEqual(result["artifact_role"], "timeline_invariants")
        self.assertEqual(result["version"], 1)
        self.assertIsNone(result["next_action"])
        checks = _checks_by_name(result)
        self.assertEqual(checks["clip_trace_present"]["status"], "pass")
        self.assertEqual(checks["non_negative_duration"]["status"], "pass")
        self.assertEqual(checks["track_overlap_free"]["status"], "pass")

    def test_missing_trace_fails(self):
        clip = _clip(2, "b.mp4", 0, 2, 3)
        clip.pop("trace")
        clip.pop("source_path")
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0), clip]}
        result = ti.audit_timeline(timeline)
        self.assertFalse(result["pass"])
        checks = _checks_by_name(result)
        self.assertEqual(checks["clip_trace_present"]["status"], "fail")
        self.assertIn(2, checks["clip_trace_present"]["affected_segments"])
        self.assertIsNotNone(result["next_action"])

    def test_negative_duration_fails(self):
        bad = _clip(2, "b.mp4", 5, 2, 3)
        bad["duration_sec"] = -1.0
        bad["end_sec"] = 4.0  # end < start
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0), bad]}
        result = ti.audit_timeline(timeline)
        checks = _checks_by_name(result)
        self.assertEqual(checks["non_negative_duration"]["status"], "fail")
        self.assertFalse(result["pass"])

    def test_track_overlap_reported(self):
        # second clip starts on the timeline before the first one ends
        timeline = {"clips": [
            _clip(1, "a.mp4", 0, 3, 0),       # timeline 0 -> 3
            _clip(2, "b.mp4", 0, 2, 2),       # timeline 2 -> 4 overlaps
        ]}
        result = ti.audit_timeline(timeline)
        checks = _checks_by_name(result)
        self.assertEqual(checks["track_overlap_free"]["status"], "fail")
        self.assertFalse(result["pass"])

    def test_must_include_missing_fails(self):
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0)]}
        result = ti.audit_timeline(timeline, must_include_segments=[1, 5])
        checks = _checks_by_name(result)
        self.assertEqual(checks["must_include_present"]["status"], "fail")
        self.assertIn(5, checks["must_include_present"]["affected_segments"])
        self.assertFalse(result["pass"])

    def test_must_include_present_passes(self):
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0), _clip(5, "b.mp4", 0, 2, 3)]}
        result = ti.audit_timeline(timeline, must_include_segments=[1, 5])
        checks = _checks_by_name(result)
        self.assertEqual(checks["must_include_present"]["status"], "pass")
        self.assertTrue(result["pass"])

    def test_duration_incompatible_warns(self):
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0), _clip(2, "b.mp4", 0, 2, 3)]}
        # actual total = 5s, expected 30s -> incompatible
        result = ti.audit_timeline(timeline, expected_duration_sec=30.0,
                                   duration_tolerance_sec=1.0)
        checks = _checks_by_name(result)
        self.assertEqual(checks["duration_compatible"]["status"], "warn")
        # warn does not fail the audit
        self.assertTrue(result["pass"])

    def test_duration_compatible_passes(self):
        timeline = {"clips": [_clip(1, "a.mp4", 0, 3, 0), _clip(2, "b.mp4", 0, 2, 3)]}
        result = ti.audit_timeline(timeline, expected_duration_sec=5.0,
                                   duration_tolerance_sec=1.0)
        checks = _checks_by_name(result)
        self.assertEqual(checks["duration_compatible"]["status"], "pass")

    def test_writer_outputs_stable_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "timeline_invariants.json"
            result = ti.write_timeline_invariants({"clips": []}, p)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(result["timeline_invariants"], str(p))
            self.assertEqual(saved["artifact_role"], "timeline_invariants")
            self.assertEqual(saved["version"], 1)
            self.assertTrue(saved["pass"])


if __name__ == "__main__":
    unittest.main()
