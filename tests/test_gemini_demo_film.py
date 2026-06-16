"""Unit tests for the enhanced-only Gemini demo-film harness."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import gemini_demo_film as D


class GeminiDemoFilmPureTest(unittest.TestCase):
    def test_build_demo_script_is_enhanced_only_and_story_ordered(self):
        script = D.build_demo_script(["N01", "N02", "N03"], title="Demo")
        self.assertEqual(script["title"], "Demo")
        self.assertEqual([s["segment"] for s in script["segments"]], [1, 2, 3])
        self.assertEqual([s["need_ref"] for s in script["segments"]], ["N01", "N02", "N03"])
        self.assertTrue(all(s["pace"] == "fast" for s in script["segments"]))
        self.assertTrue(all(s["pacing"]["preferred_shot_sec"] == [2.8, 3.4]
                            for s in script["segments"]))
        self.assertNotIn("disable_visual_diversity", script)
        self.assertNotIn("story_arc", script)

    def test_select_needs_requires_at_least_three_present_needs(self):
        assets = [{"need_id": "N01"}, {"need_id": "N02"}]
        with self.assertRaises(D.Blocked):
            D.select_present_needs(assets)

    def test_select_needs_ignores_distractors_and_preserves_canonical_order(self):
        assets = [{"need_id": "DISTRACTOR"}, {"need_id": "N03"}, {"need_id": "N01"}]
        self.assertEqual(D.select_present_needs(assets, min_needs=2), ["N01", "N03"])

    def test_compute_demo_report_discloses_outputs_and_limits(self):
        result = {
            "plan": [
                {"segment": 0, "opening_role": "hook", "extract_dur": 2.0},
                {"segment": 1, "scene_id": "a:0", "extract_dur": 4.0,
                 "sequence_recipe_source": "auto", "arc_role": "setup"},
                {"segment": 2, "scene_id": "b:0", "extract_dur": 5.0,
                 "arc_role": "climax"},
            ],
            "segments": [{"segment": 1}, {"segment": 2}],
            "opening_plan": {"status": "planned"},
            "story_arc_plan": {"status": "planned", "execution": {"status": "applied"}},
            "cuts": 3,
        }
        assets = [{"asset_id": "a", "filename": "a.png", "is_distractor": False},
                  {"asset_id": "b", "filename": "b.png", "is_distractor": True}]
        report = D.compute_demo_report(result, asset_count=36, need_count=7,
                                       requested_target_sec=75.0,
                                       render_sec=74.6,
                                       slot_check={"ok": True, "checked_slots": 3,
                                                   "failed_slots": []},
                                       assets=assets)
        self.assertEqual(report["mode"], "enhanced_only_gemini_demo")
        self.assertEqual(report["assets"]["asset_count"], 36)
        self.assertEqual(report["opening"]["status"], "planned")
        self.assertEqual(report["auto_sequence"]["count"], 1)
        self.assertEqual(report["story_arc"]["status"], "planned")
        self.assertTrue(report["slot_render_check"]["ok"])
        self.assertEqual(report["distractor_usage"]["used"][0]["asset_id"], "b")

    def test_report_md_contains_viewing_boundary(self):
        report = {
            "mode": "enhanced_only_gemini_demo",
            "target": {"requested_sec": 75.0, "render_sec": 74.6},
            "assets": {"asset_count": 36, "need_count": 7},
            "opening": {"status": "planned", "clip_count": 2},
            "auto_sequence": {"count": 7, "segments": [1, 2, 3]},
            "story_arc": {"status": "planned", "execution": "applied",
                          "arc_role_durations": {"setup": 8.0, "climax": 12.0}},
            "slot_render_check": {"ok": True, "checked_slots": 15, "failed_slots": []},
            "distractor_usage": {"used": [{"asset_id": "d", "segment": 1}]},
            "limitations": {"synthetic_gemini_material": True},
        }
        md = D.report_md(report)
        self.assertIn("Gemini Demo Film", md)
        self.assertIn("synthetic Gemini material", md)
        self.assertIn("not a real-footage quality verdict", md)
        self.assertIn("Distractors used", md)

    def test_output_root_is_cleaned_before_run(self):
        root = Path(tempfile.mkdtemp())
        old = root / "old.txt"
        old.write_text("old")
        D.prepare_output_root(root)
        self.assertTrue(root.exists())
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
