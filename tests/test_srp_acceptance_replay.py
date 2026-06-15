"""Unit tests for the SRP acceptance-replay harness pure functions.

No ffmpeg / no Gemini dependency: covers material-map building, asset resolution
blocking, and the comparison-report attribution logic with hand-built results.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import srp_acceptance_replay as R


def _entry(fn, need, fam="fam", scale="medium", subject="s", similar=None,
           must=True):
    return {"filename": fn, "need_id": need, "visual_family": fam,
            "angle_scale": scale, "subject": subject,
            "intentionally_similar_to": similar, "must_have": must}


class MaterialBuildTest(unittest.TestCase):
    def _root_with(self, files):
        d = Path(tempfile.mkdtemp())
        for fn, content in files.items():
            (d / fn).write_bytes(content)
        return d

    def test_resolve_assets_ok(self):
        d = self._root_with({"n01_a.png": b"x", "n02_b.png": b"y"})
        manifest = [_entry("n01_a.png", "N01"), _entry("n02_b.png", "N02")]
        assets, problems = R.resolve_assets(manifest, d)
        self.assertEqual(len(assets), 2)
        self.assertEqual(problems, [])
        self.assertTrue(all(Path(a["source"]).is_absolute() for a in assets))

    def test_resolve_assets_reports_missing_and_empty(self):
        d = self._root_with({"good.png": b"x", "empty.png": b""})
        manifest = [_entry("good.png", "N01"), _entry("empty.png", "N02"),
                    _entry("gone.png", "N03")]
        assets, problems = R.resolve_assets(manifest, d)
        self.assertEqual([a["filename"] for a in assets], ["good.png"])
        reasons = {p["filename"]: p["reason"] for p in problems}
        self.assertEqual(reasons["empty.png"], "empty file")
        self.assertEqual(reasons["gone.png"], "file not found")

    def test_distractor_theme_follows_similar(self):
        e = _entry("distractor_dup.png", "DISTRACTOR", similar="n01_assembly.png")
        self.assertEqual(R.asset_theme(e), R.NEED_THEME["N01"])
        off = _entry("distractor_forest.png", "DISTRACTOR")
        self.assertIsNone(R.asset_theme(off))
        self.assertNotIn(R.NEED_THEME["N01"], R.build_caption(off))

    def test_build_material_map_is_canonical_photo_shape(self):
        d = self._root_with({"n01_a.png": b"x"})
        assets, _ = R.resolve_assets([_entry("n01_a.png", "N01", fam="assembly_view",
                                              scale="wide")], d)
        mm = R.build_material_map(assets)
        self.assertEqual(mm["artifact_role"], "project_material_map")
        asset = mm["assets"][0]
        self.assertEqual(asset["asset_type"], "photo")
        scene = asset["scenes"][0]
        self.assertEqual((scene["start"], scene["end"]), (0.0, 0.0))
        self.assertEqual(scene["visual_family"], "assembly_view")
        self.assertIn(R.NEED_THEME["N01"], scene["caption"])

    def test_variant_flags(self):
        script = R.build_script(["N01", "N02", "N03"])
        self.assertTrue(all(s["pace"] == "fast" for s in script["segments"]))
        base = R.baseline_script(script)
        self.assertTrue(base["disable_visual_diversity"])
        self.assertTrue(base["disable_auto_sequence"])
        self.assertTrue(base["disable_auto_opening"])
        self.assertIs(base["story_arc"], False)
        enh = R.enhanced_script(script)
        self.assertFalse(enh["disable_visual_diversity"])
        self.assertNotIn("story_arc", enh)


def _slot(seg, sid, dur=2.0, fam=None, beat=None, is_photo=True, arc=None,
          seq=None, opening=None):
    s = {"segment": seg, "scene_id": sid, "extract_dur": dur, "visual_family": fam,
         "is_photo": is_photo}
    if beat:
        s["beat_role"] = beat
    if arc:
        s["arc_role"] = arc
    if seq:
        s["sequence_recipe_source"] = seq
    if opening:
        s["opening_role"] = opening
    return s


class ReportTest(unittest.TestCase):
    def _assets(self):
        return [{"asset_id": "a", "need_id": "N01", "visual_family": "f1",
                 "angle_scale": "wide", "asset_type": "photo", "is_distractor": False,
                 "filename": "a.png"}]

    def test_attribution_from_isolations(self):
        # baseline: 2 plain story slots; no structure
        base = {"plan": [_slot(1, "a:0", fam="f1"), _slot(1, "b:0", fam="f1")],
                "segments": [{"segment": 1, "picked_scores": [1.0], "clips_found": 2}],
                "story_arc_plan": {"status": "not_applicable"}}
        # enhanced: opening + beat roles + arc + different selection
        enh = {"plan": [_slot(0, "a:0", opening="hook"),
                        _slot(1, "a:0", fam="f1", beat="context", arc="setup", seq="auto"),
                        _slot(1, "c:0", fam="f2", beat="payoff", arc="setup", seq="auto")],
               "segments": [{"segment": 1, "picked_scores": [1.0], "clips_found": 2}],
               "story_arc_plan": {"status": "planned", "execution": {"status": "applied"},
                                  "segment_hints": [{"segment_ref": 1, "arc_role": "setup"}]}}
        # isolations: each single toggle changes the timeline signature vs baseline
        iso = {
            "VD2": {"plan": [_slot(1, "a:0", fam="f1"), _slot(1, "c:0", fam="f2")],
                    "segments": base["segments"]},
            "SRP1": {"plan": [_slot(1, "a:0", fam="f1", beat="context", seq="auto"),
                              _slot(1, "b:0", fam="f1", beat="payoff", seq="auto")],
                     "segments": base["segments"]},
            "SRP2": {"plan": [_slot(0, "a:0", opening="hook"),
                              _slot(1, "a:0", fam="f1"), _slot(1, "b:0", fam="f1")],
                     "segments": base["segments"]},
            "SRP3": {"plan": [_slot(1, "a:0", dur=3.0, fam="f1"),
                              _slot(1, "b:0", dur=1.0, fam="f1")],
                     "segments": base["segments"]},
        }
        rep = R.compute_report(base, enh, self._assets(), isolations=iso)
        caps = rep["capabilities_that_changed_build"]
        for name in caps:
            self.assertTrue(caps[name]["active"], f"{name} should be active")
        self.assertTrue(rep["timelines_differ"])
        self.assertEqual(rep["opening_inserted"]["enhanced"], True)
        self.assertEqual(rep["opening_inserted"]["baseline"], False)
        self.assertEqual(rep["auto_sequence_count"]["enhanced"], 1)

    def test_inactive_capability_when_isolation_matches_baseline(self):
        base = {"plan": [_slot(1, "a:0", fam="f1")],
                "segments": [{"segment": 1, "picked_scores": [1.0]}],
                "story_arc_plan": {"status": "not_applicable"}}
        enh = base
        # VD2 isolation identical to baseline -> not active, honest reason
        iso = {"VD2": {"plan": [_slot(1, "a:0", fam="f1")], "segments": base["segments"]}}
        rep = R.compute_report(base, enh, self._assets(), isolations=iso)
        self.assertFalse(rep["capabilities_that_changed_build"]["VD2_visual_diversity"]["active"])
        self.assertIn("did not change", rep["capabilities_that_changed_build"]
                      ["VD2_visual_diversity"]["evidence"])

    def test_consecutive_family_repeats(self):
        plan = [_slot(1, "a:0", fam="X"), _slot(1, "b:0", fam="X"),
                _slot(2, "c:0", fam="Y")]
        self.assertEqual(R.consecutive_family_repeats(plan), 1)

    def test_report_md_renders(self):
        base = {"plan": [_slot(1, "a:0", fam="f1")],
                "segments": [{"segment": 1, "picked_scores": [1.0]}],
                "story_arc_plan": {"status": "not_applicable"}}
        rep = R.compute_report(base, base, self._assets(), isolations={})
        md = R.report_md(rep)
        self.assertIn("Comparison Report", md)
        self.assertIn("Viewing checklist", md)


if __name__ == "__main__":
    unittest.main()
