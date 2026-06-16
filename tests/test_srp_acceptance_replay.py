"""Unit tests for the SRP acceptance-replay harness.

Mostly ffmpeg/Gemini-free (material-map building, asset-resolution blocking, report
attribution, content/slot analysis). One slot-level reverse proof builds a tiny
[red card + gradient] video with ffmpeg using ONLY generated content (no Gemini).
"""
from __future__ import annotations

import subprocess
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
        self.assertEqual(asset["need_id"], "N01")
        scene = asset["scenes"][0]
        self.assertEqual(scene["need_id"], "N01")
        self.assertEqual((scene["start"], scene["end"]), (0.0, 0.0))
        self.assertEqual(scene["visual_family"], "assembly_view")
        self.assertIn(R.NEED_THEME["N01"], scene["caption"])

    def test_declared_missing_image_fails_closed(self):
        # a declared manifest image that is missing -> resolve reports it ->
        # assert_declared_present BLOCKS (no successful run on a degraded set).
        d = self._root_with({"n01_a.png": b"x"})
        manifest = [_entry("n01_a.png", "N01"), _entry("n02_missing.png", "N02")]
        assets, problems = R.resolve_assets(manifest, d)
        self.assertTrue(problems)
        with self.assertRaises(R.Blocked):
            R.assert_declared_present(problems)

    def test_unreadable_declared_image_is_a_problem(self):
        d = self._root_with({"good.png": b"x"})
        # a directory at a declared path is not a readable file
        (d / "n02_dir.png").mkdir()
        manifest = [_entry("good.png", "N01"), _entry("n02_dir.png", "N02")]
        _assets, problems = R.resolve_assets(manifest, d)
        self.assertTrue(any(p["filename"] == "n02_dir.png" for p in problems))
        with self.assertRaises(R.Blocked):
            R.assert_declared_present(problems)

    def test_all_present_does_not_block(self):
        R.assert_declared_present([])   # no problems -> no raise

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

    def test_distractor_usage_reported(self):
        assets = [
            {"asset_id": "n01_a", "need_id": "N01", "visual_family": "f1",
             "angle_scale": "wide", "asset_type": "photo", "is_distractor": False,
             "filename": "n01_a.png"},
            {"asset_id": "distractor_bad_group_photo", "need_id": "DISTRACTOR",
             "visual_family": "bad_group", "angle_scale": "wide",
             "asset_type": "photo", "is_distractor": True,
             "filename": "distractor_bad_group_photo.png"},
        ]
        # enhanced selects the bad-group distractor into segment 7
        enh = {"plan": [_slot(1, "n01_a:0", fam="f1"),
                        _slot(7, "distractor_bad_group_photo:0", fam="bad_group")],
               "segments": [{"segment": 1, "picked_scores": [1.0]},
                            {"segment": 7, "picked_scores": [1.0]}],
               "story_arc_plan": {"status": "not_applicable"}}
        base = {"plan": [_slot(1, "n01_a:0", fam="f1")],
                "segments": [{"segment": 1, "picked_scores": [1.0]}],
                "story_arc_plan": {"status": "not_applicable"}}
        rep = R.compute_report(base, enh, assets, isolations={})
        du = rep["distractor_usage"]
        self.assertTrue(du["off_topic_or_distractor_used"])
        self.assertEqual(du["used_distractors_baseline"], [])
        self.assertEqual(len(du["used_distractors_enhanced"]), 1)
        used = du["used_distractors_enhanced"][0]
        self.assertEqual(used["filename"], "distractor_bad_group_photo.png")
        self.assertEqual(used["segment"], 7)
        self.assertEqual(used["visual_family"], "bad_group")
        self.assertIn("distractor", R.report_md(rep))

    def test_report_md_renders(self):
        base = {"plan": [_slot(1, "a:0", fam="f1")],
                "segments": [{"segment": 1, "picked_scores": [1.0]}],
                "story_arc_plan": {"status": "not_applicable"}}
        rep = R.compute_report(base, base, self._assets(), isolations={})
        md = R.report_md(rep)
        self.assertIn("Comparison Report", md)
        self.assertIn("Viewing checklist", md)


class RenderContentTest(unittest.TestCase):
    """Render-content verification (anti fake-render). Pure: PIL only, no ffmpeg."""

    def _png(self, d, name, pixels_fn, size=32):
        from PIL import Image
        im = Image.new("RGB", (size, size))
        im.putdata([pixels_fn(i % size, i // size) for i in range(size * size)])
        p = Path(d) / name
        im.save(p)
        return str(p)

    def test_frame_descriptor_flat_card_is_monochrome(self):
        d = tempfile.mkdtemp()
        for name, color in (("red.png", (255, 0, 0)), ("black.png", (0, 0, 0)),
                            ("white.png", (255, 255, 255))):
            p = self._png(d, name, lambda x, y, c=color: c)
            desc = R.frame_descriptor(p)
            self.assertLess(desc["stdev"], R.MONO_STDEV, f"{name} should be flat")

    def test_frame_descriptor_varied_image_not_monochrome(self):
        d = tempfile.mkdtemp()
        p = self._png(d, "grad.png", lambda x, y: (x * 8 % 256, y * 8 % 256,
                                                   (x + y) * 4 % 256))
        self.assertGreaterEqual(R.frame_descriptor(p)["stdev"], R.MONO_STDEV)

    def test_pearson(self):
        self.assertAlmostEqual(R.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0, places=6)
        self.assertAlmostEqual(R.pearson([1, 2, 3, 4], [4, 3, 2, 1]), -1.0, places=6)
        self.assertEqual(R.pearson([1, 1, 1], [1, 2, 3]), 0.0)   # zero variance

    def test_evaluate_content_blocks_monochrome(self):
        flat = [{"stdev": 0.0, "gray": [10] * 16, "mean_rgb": (255, 0, 0)}] * 3
        src = [{"gray": list(range(16)), "name": "s.png"}]
        res = R.evaluate_content(flat, src)
        self.assertFalse(res["ok"])
        self.assertIn("monochrome", res["reason"])

    def test_evaluate_content_blocks_uncorrelated(self):
        frames = [{"stdev": 50.0, "gray": [i % 4 for i in range(16)],
                   "mean_rgb": (100, 100, 100)}]
        src = [{"gray": [(i * 7) % 5 for i in range(16)], "name": "s.png"}]
        res = R.evaluate_content(frames, src, min_corr=0.95)
        self.assertFalse(res["ok"])
        self.assertIn("correlate", res["reason"])

    def test_evaluate_content_ok_when_frame_matches_source(self):
        g = [float(i) for i in range(16)]
        frames = [{"stdev": 50.0, "gray": g, "mean_rgb": (100, 100, 100)}]
        src = [{"gray": [v * 1.0 + 3 for v in g], "name": "match.png"}]  # corr 1.0
        res = R.evaluate_content(frames, src)
        self.assertTrue(res["ok"])
        self.assertEqual(res["best_match_source"], "match.png")
        self.assertGreaterEqual(res["best_source_correlation"], 0.99)

    def test_assert_render_content_raises_on_fail(self):
        with self.assertRaises(R.Blocked):
            R.assert_render_content({"ok": False, "reason": "flat"}, "enhanced")
        R.assert_render_content({"ok": True, "reason": "ok"}, "enhanced")  # no raise

    def test_no_frames_extracted_is_not_ok(self):
        self.assertFalse(R.evaluate_content([], [{"gray": [1] * 16}])["ok"])


class SlotLevelTest(unittest.TestCase):
    """Slot-level render verification (catches a per-slot fake render that
    whole-video sampling can skip — e.g. a red opening card)."""

    def _png(self, d, name, fn, size=64):
        from PIL import Image
        im = Image.new("RGB", (size, size))
        im.putdata([fn(i % size, i // size) for i in range(size * size)])
        p = Path(d) / name
        im.save(p)
        return str(p)

    def test_slot_windows_cumulative(self):
        plan = [{"slot_index": 0, "extract_dur": 2.0},
                {"slot_index": 1, "extract_dur": 1.0},
                {"slot_index": 2, "extract_dur": 3.0}]
        w = R.slot_windows(plan)
        self.assertEqual([(s, e, m) for _, s, e, m in w],
                         [(0.0, 2.0, 1.0), (2.0, 3.0, 2.5), (3.0, 6.0, 4.5)])

    def test_evaluate_slot_monochrome_card_fails(self):
        flat = {"stdev": 0.0, "gray": [40.0] * 16}     # solid red/blue/black card
        src = {"gray": list(range(16))}
        res = R.evaluate_slot(flat, src)
        self.assertFalse(res["ok"])
        self.assertIn("monochrome", res["reason"])

    def test_evaluate_slot_uncorrelated_fails(self):
        frame = {"stdev": 50.0, "gray": [i % 3 for i in range(16)]}
        src = {"gray": [(i * 5) % 7 for i in range(16)]}
        res = R.evaluate_slot(frame, src, min_corr=0.95)
        self.assertFalse(res["ok"])
        self.assertIn("uncorrelated", res["reason"])

    def test_evaluate_slot_ok_when_matches_source(self):
        g = [float(i) for i in range(16)]
        res = R.evaluate_slot({"stdev": 50.0, "gray": g}, {"gray": [v + 2 for v in g]})
        self.assertTrue(res["ok"])

    def test_summarize_front_color_cards_fail(self):
        # "only the second half has real images; the front is color cards"
        records = [
            {"slot_index": 0, "ok": False}, {"slot_index": 1, "ok": False},
            {"slot_index": 2, "ok": True}, {"slot_index": 3, "ok": True}]
        s = R.summarize_slot_records(records)
        self.assertFalse(s["ok"])
        self.assertEqual(s["failed_slots"], [0, 1])
        with self.assertRaises(R.Blocked):
            R.assert_slots(s, "enhanced")

    def test_verify_slots_blocks_red_opening_clip(self):
        # END-TO-END (ffmpeg, no external assets): a video whose FIRST slot is a
        # solid-red card must fail at the slot level, even though a later slot is
        # real content (the whole-video gate could miss this).
        from video_pipeline_core.vt_core import FFMPEG, FFPROBE
        orig = (R.FFMPEG, R.FFPROBE)
        R.FFMPEG, R.FFPROBE = FFMPEG, FFPROBE
        try:
            d = Path(tempfile.mkdtemp())
            grad = self._png(d, "grad.png",
                             lambda x, y: (x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256))
            red, gr, out = d / "red.mp4", d / "gr.mp4", d / "v.mp4"
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1",
                            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", str(red)],
                           capture_output=True, check=True)
            subprocess.run([FFMPEG, "-y", "-loop", "1", "-i", grad, "-t", "1",
                            "-vf", "scale=320:240,setsar=1,fps=30,format=yuv420p",
                            "-c:v", "libx264", str(gr)], capture_output=True, check=True)
            listf = d / "l.txt"
            listf.write_text(f"file '{red.as_posix()}'\nfile '{gr.as_posix()}'\n")
            subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
                            "-c", "copy", str(out)], capture_output=True, check=True)
            plan = [
                {"slot_index": 0, "segment": 1, "source": grad, "extract_dur": 1.0,
                 "opening_role": "hook", "scene_id": "grad:0"},
                {"slot_index": 1, "segment": 1, "source": grad, "extract_dur": 1.0,
                 "beat_role": "payoff", "scene_id": "grad:1"}]
            chk = R.verify_slots(str(out), plan)
            self.assertIn(0, chk["failed_slots"])     # red opening slot fails
            self.assertNotIn(1, chk["failed_slots"])  # real gradient slot passes
            self.assertFalse(chk["ok"])
            with self.assertRaises(R.Blocked):
                R.assert_slots(chk, "enhanced")
        finally:
            R.FFMPEG, R.FFPROBE = orig


if __name__ == "__main__":
    unittest.main()
