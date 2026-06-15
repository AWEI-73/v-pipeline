"""SRP3 — runtime integration tests (L–R + runtime A/H/J/K).

Drive run_mv end-to-end to prove the story-arc hints actually change BUILD
allocation (climax > setup) while preserving the duration contract, manual
intent, SRP1/VD2/SRP2 behavior, immutability, determinism, and a real render.
"""
from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import mv_cut
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _music(d, dur=8):
    m = d / "music.wav"
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d={dur}:s=44100",
                    str(m)], capture_output=True, check=True)
    return m


_CAPTIONS = ["alpha gear", "beta climb", "gamma haul", "delta rescue", "epsilon cheer"]


def _arc_map(d=None, gen=False):
    """5 captions x 2 distinct-family assets each (10 photo assets)."""
    assets = []
    for i, cap in enumerate(_CAPTIONS):
        for j, fam in enumerate(("A", "B")):
            aid = f"a{i}-{fam}"
            src = f"{aid}.png"
            if gen and d is not None:
                src = str(d / f"{aid}.png")
                color = ["red", "blue", "green", "yellow", "purple"][i]
                subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                                f"color=c={color}:s=320x240:d=1", "-vframes", "1", src],
                               capture_output=True, check=True)
            assets.append({"asset_id": aid, "source": src, "asset_type": "photo",
                           "scenes": [{"start": 0.0, "end": 0.0, "caption": cap,
                                       "visual_family": f"fam-{i}-{fam}",
                                       "angle_scale": "medium"}]})
    return {"artifact_role": "project_material_map", "version": 1, "assets": assets}


def _five_seg(overrides=None, extra_script=None):
    segs = [{"segment": i + 1, "visual_desc": _CAPTIONS[i], "audio_role": "music"}
            for i in range(5)]
    for idx, fields in (overrides or {}).items():
        segs[idx].update(fields)
    script = {"segments": segs}
    if extra_script:
        script.update(extra_script)
    return script


def _run(d, script, **kw):
    kw.setdefault("skip_render", True)
    kw.setdefault("verbose", False)
    kw.setdefault("max_clips_per_seg", 2)
    music = _music(d, dur=kw.pop("music_dur", 8))
    maps = kw.pop("maps", None) or _arc_map()
    return mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                         material_maps=maps, **kw)


def _seg_dur(plan, seg_id):
    return sum(float(c.get("extract_dur") or 0.0)
               for c in plan if c.get("segment") == seg_id)


def _story_total(plan):
    return sum(float(c.get("extract_dur") or 0.0)
               for c in plan if isinstance(c.get("segment"), int) and c["segment"] >= 1)


class RuntimeApplicabilityTest(unittest.TestCase):
    def test_A_two_segments_not_applicable(self):
        d = Path(tempfile.mkdtemp())
        script = {"segments": [
            {"segment": 1, "visual_desc": "alpha gear", "audio_role": "music"},
            {"segment": 2, "visual_desc": "beta climb", "audio_role": "music"}]}
        res = _run(d, script)
        self.assertEqual(res["story_arc_plan"]["status"], "not_applicable")
        self.assertFalse(any(c.get("story_arc_source") for c in res["plan"]))

    def test_H_disable_flag_unchanged(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _five_seg(extra_script={"story_arc": False}))
        self.assertEqual(res["story_arc_plan"]["status"], "not_applicable")
        self.assertFalse(any(c.get("story_arc_source") for c in res["plan"]))
        self.assertFalse(any(c.get("arc_role") for c in res["plan"]))


class BuildImpactTest(unittest.TestCase):
    def test_L_climax_outweighs_setup(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _five_seg())
        self.assertEqual(res["story_arc_plan"]["status"], "planned")
        setup_dur = _seg_dur(res["plan"], 1)        # role setup
        climax_dur = _seg_dur(res["plan"], 4)       # role climax
        self.assertGreater(climax_dur, setup_dur)
        # arc trace present on story slots
        seg4 = [c for c in res["plan"] if c.get("segment") == 4]
        self.assertTrue(all(c.get("arc_role") == "climax" for c in seg4))
        self.assertTrue(all(c.get("story_arc_source") == "auto" for c in seg4))

    def test_M_total_duration_preserved(self):
        d1, d2 = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        off = _run(d1, _five_seg(extra_script={"story_arc": False}))
        on = _run(d2, _five_seg())
        self.assertAlmostEqual(_story_total(off["plan"]), _story_total(on["plan"]),
                               delta=0.25)

    def test_M_target_sec_not_breached(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _five_seg(extra_script={"opening_title": "T"}),
                   target_sec=6.0, music_dur=8)
        plan_dur = sum(float(c.get("extract_dur") or 0.0) for c in res["plan"])
        self.assertLessEqual(plan_dur, 6.0 + 1e-2)

    def test_N_manual_requested_duration_preserved(self):
        d = Path(tempfile.mkdtemp())
        # seg2 (challenge) pins its duration; SRP3 must not override it
        res = _run(d, _five_seg(overrides={1: {"requested_duration_sec": 3.0}}),
                   music_dur=12)
        self.assertAlmostEqual(_seg_dur(res["plan"], 2), 3.0, delta=0.2)

    def test_O_source_speech_no_weight_multiplier(self):
        d = Path(tempfile.mkdtemp())
        # seg1 (setup) declared source_speech: duration-protected, no auto weight
        res = _run(d, _five_seg(overrides={0: {"audio_role": "source_speech"}}))
        applied = res["story_arc_plan"]["execution"]["applied"]
        seg0_trace = next((t for t in applied if t["segment_index"] == 0), {})
        self.assertNotIn("weight", seg0_trace)

    def test_AB_protected_at_climax_no_weight_or_pace(self):
        d = Path(tempfile.mkdtemp())
        # seg4 (index 3) is the climax (fast role) but is a hold segment → must get
        # neither auto weight nor auto pace, even at the climax position.
        res = _run(d, _five_seg(overrides={3: {"hold": True}}))
        applied = res["story_arc_plan"]["execution"]["applied"]
        climax_trace = next(t for t in applied if t["segment_index"] == 3)
        self.assertEqual(climax_trace["arc_role"], "climax")
        self.assertNotIn("weight", climax_trace["applied_fields"])
        self.assertNotIn("pace", climax_trace["applied_fields"])


class SRP1SRP2InteropTest(unittest.TestCase):
    def test_P_srp1_vd2_preserved(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _five_seg())
        story = [c for c in res["plan"] if isinstance(c.get("segment"), int)
                 and c["segment"] >= 1]
        self.assertTrue(all(c.get("scene_id") for c in story))   # VD2 evidence intact
        # a multi-slot (fast) segment still forms an SRP1 beat sequence
        seg4 = [c for c in res["plan"] if c.get("segment") == 4]
        if len(seg4) >= 2:
            self.assertTrue(all(c.get("beat_role") for c in seg4))

    def test_Q_opening_after_story_no_arc_pollution(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _five_seg(extra_script={"opening_title": "OPENING"}))
        opening = [c for c in res["plan"] if c.get("opening_role")]
        self.assertTrue(opening)
        self.assertEqual(res["opening_plan"]["status"], "planned")
        for c in opening:                       # opening evidence not arc-tagged
            self.assertNotIn("arc_role", c)
            self.assertNotIn("story_arc_source", c)


class ImmutabilityDeterminismTest(unittest.TestCase):
    def test_J_script_immutable(self):
        d = Path(tempfile.mkdtemp())
        script = _five_seg(extra_script={"opening_title": "T"})
        original = copy.deepcopy(script)
        _run(d, script)
        self.assertEqual(script, original)

    def test_K_determinism(self):
        d = Path(tempfile.mkdtemp())
        s = _five_seg()
        r1 = _run(d, copy.deepcopy(s))
        r2 = _run(d, copy.deepcopy(s))
        self.assertEqual(r1["story_arc_plan"], r2["story_arc_plan"])
        self.assertEqual(r1["plan"], r2["plan"])


class RealRenderTest(unittest.TestCase):
    def test_R_real_render_arc_influences_build(self):
        d = Path(tempfile.mkdtemp())
        maps = _arc_map(d, gen=True)
        script = _five_seg(extra_script={"opening_title": "OPENING"})
        out = d / "final.mp4"
        music = _music(d, dur=10)
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=maps, skip_render=False, verbose=False,
                            max_clips_per_seg=2, target_sec=10.0, burn_text=True)
        self.assertTrue(out.exists() and out.stat().st_size > 0)
        plan = res["plan"]
        # arc trace on story slots
        self.assertEqual(res["story_arc_plan"]["status"], "planned")
        self.assertTrue(any(c.get("story_arc_source") == "auto" for c in plan))
        # climax story duration exceeds setup
        self.assertGreater(_seg_dur(plan, 4), _seg_dur(plan, 1))
        # whole plan within target (render tolerance)
        plan_dur = sum(float(c.get("extract_dur") or 0.0) for c in plan)
        self.assertLessEqual(plan_dur, 10.0 + 1e-2)
        out_dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertLessEqual(out_dur, 10.0 + 0.75)


if __name__ == "__main__":
    unittest.main()
