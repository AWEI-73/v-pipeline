"""Unit tests for the 67th real-footage SRP sanity harness.

These tests stay ffmpeg/footage-free. The real harness run is manual/integration:
`python tools/srp_real67_sanity.py --footage-root ...`.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import srp_real67_sanity as R


def _slot(seg, sid, dur=2.0, **extra):
    s = {
        "segment": seg,
        "scene_id": sid,
        "source": f"{sid}.MOV",
        "extract_start": 1.0,
        "extract_dur": dur,
    }
    s.update(extra)
    return s


class Real67SanityPureTest(unittest.TestCase):
    def test_variant_flags_disable_only_auto_capabilities(self):
        script = {"segments": [{"segment": 1}, {"segment": 2}, {"segment": 3}]}
        base = R.baseline_script(script)
        self.assertTrue(base["disable_visual_diversity"])
        self.assertTrue(base["disable_auto_sequence"])
        self.assertTrue(base["disable_auto_opening"])
        self.assertIs(base["story_arc"], False)
        enhanced = R.enhanced_script(script)
        self.assertFalse(enhanced["disable_visual_diversity"])
        self.assertFalse(enhanced["disable_auto_sequence"])
        self.assertFalse(enhanced["disable_auto_opening"])
        self.assertNotIn("story_arc", enhanced)
        self.assertNotIn("disable_visual_diversity", script)

    def test_find_music_prefers_declared_music_argument(self):
        d = Path(tempfile.mkdtemp())
        p = d / "music.mp4"
        p.write_bytes(b"x")
        self.assertEqual(R.find_music(d, declared=p), p)

    def test_find_music_searches_footage_tree(self):
        root = Path(tempfile.mkdtemp())
        music_dir = root / "66期學長音樂檔"
        music_dir.mkdir()
        expected = music_dir / "7感性收尾.mp4"
        expected.write_bytes(b"x")
        self.assertEqual(R.find_music(root), expected)

    def test_find_music_blocks_when_missing(self):
        with self.assertRaises(R.Blocked):
            R.find_music(Path(tempfile.mkdtemp()))

    def test_comparison_report_discloses_subset_and_effects(self):
        base = {
            "plan": [_slot(1, "director:0"), _slot(2, "birthday:0")],
            "segments": [{"segment": 1}, {"segment": 2}],
            "opening_plan": {"status": "disabled"},
            "story_arc_plan": {"status": "not_applicable"},
        }
        enhanced = {
            "plan": [
                _slot(0, "director:0", opening_role="hook"),
                _slot(1, "director:0", beat_role="context", sequence_recipe_source="auto"),
                _slot(2, "birthday:0", arc_role="climax"),
            ],
            "segments": [{"segment": 1}, {"segment": 2}],
            "opening_plan": {"status": "planned"},
            "story_arc_plan": {"status": "planned", "execution": {"status": "applied"}},
        }
        report = R.compute_real67_report(base, enhanced, subset_scene_count=3,
                                         baseline_render_sec=6.9,
                                         enhanced_render_sec=10.5,
                                         slot_checks={"baseline": {"ok": True},
                                                      "enhanced": {"ok": True}})
        self.assertTrue(report["timelines_differ"])
        self.assertTrue(report["limitations"]["m6e_covered_subset_only"])
        self.assertEqual(report["limitations"]["covered_scene_count"], 3)
        self.assertEqual(report["opening"]["enhanced_status"], "planned")
        self.assertEqual(report["auto_sequence"]["enhanced_count"], 1)

    def test_report_md_contains_honesty_boundary(self):
        report = {
            "timelines_differ": True,
            "durations": {"baseline_render_sec": 1.0, "enhanced_render_sec": 2.0},
            "opening": {"enhanced_status": "planned"},
            "story_arc": {"enhanced_status": "planned"},
            "auto_sequence": {"enhanced_count": 1, "enhanced_segments": [1]},
            "slot_render_checks": {"baseline": {"ok": True}, "enhanced": {"ok": True}},
            "limitations": {"m6e_covered_subset_only": True, "covered_scene_count": 3,
                            "full_ingest": False},
        }
        md = R.report_md(report)
        self.assertIn("67th Real-Footage SRP Sanity", md)
        self.assertIn("covered subset", md)
        self.assertIn("not a full 304-file ingest", md)

    def test_real67_slot_verdict_allows_low_variance_source_match(self):
        frame = {"stdev": 8.0, "gray": [1, 2, 3, 4]}
        source = {"gray": [1, 2, 3, 4]}
        verdict = R.real67_slot_verdict(frame, source)
        self.assertTrue(verdict["ok"])
        self.assertIn("source-matched", verdict["reason"])

    def test_real67_slot_verdict_still_blocks_low_variance_unrelated_frame(self):
        frame = {"stdev": 8.0, "gray": [1, 2, 3, 4]}
        source = {"gray": [4, 3, 2, 1]}
        verdict = R.real67_slot_verdict(frame, source)
        self.assertFalse(verdict["ok"])

    def test_actual_slot_windows_use_rendered_segment_durations(self):
        plan = [_slot(1, "a", dur=1.0, slot_index=0),
                _slot(2, "b", dur=1.0, slot_index=1)]
        windows = R.actual_slot_windows(plan, {0: 1.25, 1: 1.75})
        self.assertEqual(windows[0][1:], (0.0, 1.25, 0.625))
        self.assertEqual(windows[1][1:], (1.25, 3.0, 2.125))

    def test_verdict_uses_best_source_candidate(self):
        frame = {"stdev": 40.0, "gray": [1, 2, 3, 4]}
        sources = [{"gray": [4, 3, 2, 1]}, {"gray": [1, 2, 3, 4]}]
        verdict = R.real67_slot_verdict(frame, sources)
        self.assertTrue(verdict["ok"])
        self.assertAlmostEqual(verdict["best_correlation"], 1.0)


if __name__ == "__main__":
    unittest.main()
