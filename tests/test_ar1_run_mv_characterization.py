"""AR1 — run_mv runtime-planning characterization tests.

These lock the END-TO-END behavior of `run_mv` (story timeline, VD2 shared
history, SRP1 auto sequence, manual beat recipe, SRP2 auto opening + target_sec
budget, manual opening, ending, compiler fallbacks, immutability, determinism,
and a real render) so the AR1 planning extraction can be proven to be a
ZERO-behavior-change refactor. They must pass identically before and after the
extraction.
"""
from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import mv_cut
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _music(d, dur=6):
    music = d / "music.wav"
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d={dur}:s=44100",
                    str(music)], capture_output=True, check=True)
    return music


def _photo_map(*specs):
    assets = []
    for asset_id, source, caption, family in specs:
        assets.append({
            "asset_id": asset_id, "source": source, "asset_type": "photo",
            "scenes": [{"start": 0.0, "end": 0.0, "caption": caption,
                        "visual_family": family, "angle_scale": "medium"}],
        })
    return {"artifact_role": "project_material_map", "version": 1, "assets": assets}


def _gen_photo(d, name, color):
    p = str(d / f"{name}.png")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"color=c={color}:s=320x240:d=1", "-vframes", "1", p],
                   capture_output=True, check=True)
    return p


def _maps4():
    return _photo_map(
        ("photo-a", "dummy1.png", "gear", "family-A"),
        ("photo-b", "dummy2.png", "gear", "family-B"),
        ("photo-c", "dummy3.png", "tool", "family-C"),
        ("photo-d", "dummy4.png", "tool", "family-D"),
    )


def _two_seg(extra=None):
    script = {"segments": [
        {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast",
         "pacing": {"preferred_shot_sec": 1.0}},
        {"segment": 2, "visual_desc": "tool", "audio_role": "music", "pace": "fast",
         "pacing": {"preferred_shot_sec": 1.0}},
    ]}
    if extra:
        script.update(extra)
    return script


def _run(d, script, maps, **kw):
    kw.setdefault("skip_render", True)
    kw.setdefault("verbose", False)
    kw.setdefault("max_clips_per_seg", 2)
    music = _music(d, dur=kw.pop("music_dur", 6))
    return mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                         material_maps=maps, **kw)


class StoryTimelineTest(unittest.TestCase):
    """A — normal map-ranked story plan/per_seg shape is stable."""

    def test_A_map_ranked_story(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _two_seg(), _maps4())
        plan = res["plan"]
        story = [c for c in plan if not c.get("opening_role")]
        # contiguous slot_index across the WHOLE plan
        self.assertEqual([c["slot_index"] for c in plan], list(range(len(plan))))
        # every story slot carries map-ranked scene_id evidence
        self.assertTrue(story)
        self.assertTrue(all(c.get("scene_id") for c in story))
        # per-segment entries: one per segment, both map_ranked
        self.assertEqual(len(res["segments"]), 2)
        self.assertTrue(all(e.get("retrieval_path") == "map_ranked"
                            for e in res["segments"]))


class VD2HistoryTest(unittest.TestCase):
    """B — VD2 cross-segment scene_id selection + order are stable."""

    def test_B_cross_segment_diversity(self):
        d = Path(tempfile.mkdtemp())
        maps = _photo_map(
            ("clip-a", "a.jpg", "rope rescue", "family-A"),
            ("clip-b", "b.jpg", "rope rescue", "family-B"),
        )
        script = {"segments": [
            {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music"},
            {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"},
        ]}
        res = _run(d, script, maps)
        story = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual([c["scene_id"] for c in story], ["clip-a:0", "clip-b:0"])


class SRP1Test(unittest.TestCase):
    """C, D — SRP1 auto sequence + manual beat recipe (incl. exception)."""

    def test_C_auto_sequence_traces_and_history(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _two_seg(), _maps4())
        story = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(story[0]["beat_role"], "context")
        self.assertEqual(story[1]["beat_role"], "payoff")
        self.assertEqual(story[0]["sequence_recipe_source"], "auto")
        self.assertIn("scene_id", story[0])
        # history diversity carried to segment 2 (tool: family-C then family-D)
        self.assertEqual(res["plan"][-1]["scene_id"], "photo-d:0")

    def test_D_manual_beat_recipe_exception_propagates(self):
        d = Path(tempfile.mkdtemp())
        script = _two_seg()
        script["segments"][0]["beat_recipe"] = {
            "beats": ["context", "payoff"],
            "shots": [{"source": "dummy1.png", "start": 0.0, "dur": 2.0},
                      {"source": "dummy2.png", "start": 0.0, "dur": 2.0}]}
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence",
                   side_effect=ValueError("loud manual")):
            with self.assertRaises(ValueError) as ctx:
                _run(d, script, _maps4())
            self.assertEqual(str(ctx.exception), "loud manual")


class SRP2OpeningTest(unittest.TestCase):
    """E, F, G, I — SRP2 auto opening, budget, manual opening, fallbacks."""

    def test_E_auto_opening_prepended(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _two_seg({"opening_title": "OPENING"}), _maps4())
        plan = res["plan"]
        opening = [c for c in plan if c.get("opening_role")]
        story = [c for c in plan if not c.get("opening_role")]
        self.assertEqual(res["opening_plan"]["status"], "planned")
        self.assertEqual(res["opening_plan"]["execution"]["status"], "prepended")
        self.assertTrue(opening)
        self.assertEqual(plan[:len(opening)], opening)               # opening first
        self.assertEqual([c["slot_index"] for c in plan], list(range(len(plan))))
        for c in opening:
            self.assertEqual(c["opening_recipe_source"], "auto")
            self.assertIn(c["scene_id"], [s["scene_id"] for s in story])

    def test_F_target_sec_budget(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _two_seg({"opening_title": "OPENING"}), _maps4(),
                   target_sec=1.0, music_dur=4)
        execu = res["opening_plan"]["execution"]
        self.assertEqual(execu["status"], "budget_fallback")
        self.assertEqual(execu["applied_opening_duration"], 0.0)
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))

    def test_G_manual_opening(self):
        d = Path(tempfile.mkdtemp())
        res = _run(d, _two_seg({"opening_recipe": {"title_text": "M", "context_count": 1}}),
                   _maps4())
        self.assertIsNone(res["opening_plan"])         # auto planner not invoked
        self.assertIsNotNone(res["opening"])
        self.assertTrue(any(c.get("opening_role") for c in res["plan"]))

    def test_I_auto_opening_value_error_fallback(self):
        d = Path(tempfile.mkdtemp())
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   side_effect=ValueError("boom")):
            res = _run(d, _two_seg({"opening_title": "OPENING"}), _maps4())
        self.assertIsNone(res["opening"])
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))
        self.assertEqual(res["opening_plan"]["execution"]["status"],
                         "compiler_error_fallback")

    def test_I_auto_opening_runtime_error_propagates(self):
        d = Path(tempfile.mkdtemp())
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   side_effect=RuntimeError("loud")):
            with self.assertRaises(RuntimeError):
                _run(d, _two_seg({"opening_title": "OPENING"}), _maps4())


class EndingTest(unittest.TestCase):
    """H — ending recipe clips / cues / slot_index are stable."""

    def test_H_ending_appended(self):
        d = Path(tempfile.mkdtemp())
        script = _two_seg({"ending_recipe": {
            "beats": ["payoff"], "punctuate_payoff": True,
            "shots": [{"source": "dummy3.png", "start": 0.0, "dur": 2.0}]}})
        res = _run(d, script, _maps4())
        self.assertIsNotNone(res["ending"])
        self.assertTrue(res["ending"]["clips"])
        plan = res["plan"]
        # ending clips are the tail; slot_index contiguous across whole plan
        self.assertEqual([c["slot_index"] for c in plan], list(range(len(plan))))


class ImmutabilityDeterminismTest(unittest.TestCase):
    """J, K — input script immutability + deterministic re-runs."""

    def test_J_script_immutable(self):
        d = Path(tempfile.mkdtemp())
        script = _two_seg({"opening_title": "OPENING"})
        original = copy.deepcopy(script)
        _run(d, script, _maps4())
        self.assertEqual(script, original)

    def test_K_determinism(self):
        d = Path(tempfile.mkdtemp())
        script = _two_seg({"opening_title": "OPENING"})
        r1 = _run(d, copy.deepcopy(script), _maps4())
        r2 = _run(d, copy.deepcopy(script), _maps4())
        self.assertEqual(r1["plan"], r2["plan"])
        self.assertEqual(r1["segments"], r2["segments"])
        self.assertEqual(r1["opening"], r2["opening"])
        self.assertEqual(r1["opening_plan"], r2["opening_plan"])
        self.assertEqual(r1["ending"], r2["ending"])


class RealRenderTest(unittest.TestCase):
    """L — real ffmpeg render of the full story+opening timeline."""

    def test_L_real_render(self):
        d = Path(tempfile.mkdtemp())
        srcs = {n: _gen_photo(d, f"photo-{n}", c) for n, c in
                (("a", "red"), ("b", "blue"), ("c", "green"), ("d", "yellow"))}
        maps = _photo_map(
            ("photo-a", srcs["a"], "gear up", "family-A"),
            ("photo-b", srcs["b"], "gear up", "family-B"),
            ("photo-c", srcs["c"], "tool work", "family-C"),
            ("photo-d", srcs["d"], "tool work", "family-D"),
        )
        out = d / "final.mp4"
        music = _music(d, dur=8)
        res = mv_cut.run_mv(_two_seg({"opening_title": "OPENING"}), None, str(out),
                            music_path=str(music), material_maps=maps,
                            skip_render=False, verbose=False, max_clips_per_seg=2,
                            burn_text=True)
        self.assertTrue(out.exists() and out.stat().st_size > 0)
        plan = res["plan"]
        opening = [c for c in plan if c.get("opening_role")]
        self.assertTrue(opening)
        self.assertEqual(plan[:len(opening)], opening)
        dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertGreater(dur, 0.0)


if __name__ == "__main__":
    unittest.main()
