"""MR1 — map-based window retrieval promoted from partial to active.

Falsification tests for the wiring contract: when a valid material map exists,
local segments default to map-based scene/window retrieval (no longer gated on
clip_list matched picks), with honest matched/live fallback and a measurable
`retrieval_path` trace. Existing stock/source_speech/photo_stack behavior and
the no-map compatibility path must not regress.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import mv_cut
from video_pipeline_core.material_retrieval import plan_ranked_windows, rank_scenes
from video_pipeline_core.project_material_map import expand_project_material_map
from video_pipeline_core.vt_core import FFMPEG


def _seg(desc, n=4):
    return {"segment": n, "visual_desc": desc,
            "material_fit": {"visual_desc": desc}}


def _alloc(n_clips=1, clip_dur=2.0):
    return {"n_clips": n_clips, "clip_dur": clip_dur, "budget": clip_dur}


def _map(asset_id="a", source="a.mp4", scenes=None):
    return {"asset_id": asset_id, "source": source, "scenes": scenes or []}


FIT = [{"start": 0, "end": 5, "caption": "students pull electrical cable"}]
NO_FIT = [{"start": 0, "end": 5, "caption": "unrelated empty sky"}]


class MapDefaultPathTest(unittest.TestCase):
    def test_A_map_ranked_enters_plan_without_clip_list_picks(self):
        """A: project map present, NO clip_list picks → map-ranked scene still
        becomes a concrete slot (the partial→active promotion)."""
        maps = [_map(scenes=FIT)]
        slots, entry, _ = mv_cut._plan_local_segment(
            _seg("students pull electrical cable"), _alloc(), {}, {}, False,
            material_maps=maps, clip_list=None)
        self.assertTrue(slots)
        self.assertEqual(entry["retrieval_path"], "map_ranked")
        self.assertEqual(slots[0]["scene_id"], "a:0")
        self.assertIn("retrieval_score", slots[0])

    def test_B_no_fit_falls_back_to_matched_not_empty(self):
        """B: map present but no evidence-fit scene → matched fallback (never an
        empty/GAP segment when picks exist)."""
        maps = [_map(scenes=NO_FIT)]
        clip_by_seg = {4: {"picks": [{"path": "/m/cable/a.mov"}]}}
        original = mv_cut._windows_from_clip
        mv_cut._windows_from_clip = lambda path, n, dur, ka, text=None, segment=None: (
            [{"source": path, "segment": segment}] if n > 0 else [])
        try:
            slots, entry, _ = mv_cut._plan_local_segment(
                _seg("students pull electrical cable"), _alloc(), clip_by_seg, {}, False,
                material_maps=maps, clip_list={"assignments": []})
        finally:
            mv_cut._windows_from_clip = original
        self.assertTrue(slots)                       # NOT empty
        self.assertEqual(entry["retrieval_path"], "matched_fallback")

    def test_B_no_fit_falls_back_to_live_when_no_picks(self):
        """B: no fit and no matched picks but material_root present → live fallback."""
        maps = [_map(scenes=NO_FIT)]
        sentinel = ([{"source": "/live/x.mp4", "segment": 4}],
                    {"segment": 4, "picked_scores": [70]}, ["live"])
        original = mv_cut._plan_live_segment
        mv_cut._plan_live_segment = lambda *a, **k: sentinel
        try:
            slots, entry, _ = mv_cut._plan_local_segment(
                _seg("students pull electrical cable"), _alloc(), {}, {}, False,
                material_maps=maps, clip_list=None,
                live_kwargs={"material_root": "/some/root", "model": None,
                             "mat_dir": "/tmp", "max_clips_per_seg": 2,
                             "windows_per_clip": 2, "min_score": 60,
                             "prefilter_static": False})
        finally:
            mv_cut._plan_live_segment = original
        self.assertTrue(slots)
        self.assertEqual(entry["retrieval_path"], "live_fallback")

    def test_C_no_map_keeps_legacy_matched_behavior(self):
        """C: no map → unchanged matched routing/labelling."""
        clip_by_seg = {4: {"picks": [{"path": "/m/x.mov"}]}}
        original = mv_cut._windows_from_clip
        mv_cut._windows_from_clip = lambda path, n, dur, ka, text=None, segment=None: (
            [{"source": path, "segment": segment}] if n > 0 else [])
        try:
            slots, entry, _ = mv_cut._plan_local_segment(
                _seg("anything"), _alloc(), clip_by_seg, {}, False,
                material_maps=None, clip_list={"assignments": []})
        finally:
            mv_cut._windows_from_clip = original
        self.assertTrue(slots)
        self.assertEqual(entry["retrieval_path"], "matched")

    def test_no_fallback_material_is_honest_gap_not_crash(self):
        maps = [_map(scenes=NO_FIT)]
        slots, entry, _ = mv_cut._plan_local_segment(
            _seg("students pull electrical cable"), _alloc(), {}, {}, False,
            material_maps=maps, clip_list=None, live_kwargs={"material_root": None})
        self.assertEqual(slots, [])
        self.assertEqual(entry["picked_scores"], [mv_cut.GAP])


class ExpandProjectMapTest(unittest.TestCase):
    def test_D_project_map_expands_to_per_asset_maps_for_retrieval(self):
        project_map = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [{"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video",
                        "scenes": FIT}],
        }
        maps = expand_project_material_map(project_map)
        self.assertEqual(maps[0]["asset_id"], "clip-a")
        self.assertEqual(maps[0]["source"], "a.mp4")
        ranked = rank_scenes(_seg("students pull electrical cable"), maps)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["scene_id"], "clip-a:0")

    def test_list_and_single_map_pass_through(self):
        self.assertEqual(len(expand_project_material_map([_map(), _map("b")])), 2)
        self.assertEqual(len(expand_project_material_map(_map())), 1)
        self.assertIsNone(expand_project_material_map(None))

    def test_E_unknown_artifact_role_fails(self):
        with self.assertRaises(ValueError):
            expand_project_material_map({"artifact_role": "bogus", "assets": []})

    def test_E_project_asset_without_source_fails(self):
        with self.assertRaises(ValueError):
            expand_project_material_map({
                "artifact_role": "project_material_map",
                "assets": [{"asset_id": "a", "scenes": []}]})

    def test_E_non_numeric_scene_bound_fails(self):
        with self.assertRaises(ValueError):
            expand_project_material_map({
                "artifact_role": "project_material_map",
                "assets": [{"asset_id": "a", "source": "a.mp4",
                            "scenes": [{"start": "soon", "end": 5}]}]})

    def test_E_sourceless_scene_never_enters_timeline(self):
        # a per-asset map with no source: scenes can be ranked but must not
        # produce a renderable window (it would point at a missing input).
        maps = [{"asset_id": "a", "scenes": FIT}]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=2, clip_dur=2.0)
        self.assertEqual(slots, [])

    def test_E_zero_and_negative_length_scene_dropped(self):
        maps = [_map(scenes=[{"start": 3, "end": 3, "caption": "students pull electrical cable"},
                             {"start": 5, "end": 4, "caption": "students pull electrical cable"}])]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=5, clip_dur=2.0)
        self.assertEqual(slots, [])


class WindowEvidenceTest(unittest.TestCase):
    def test_F_window_stays_within_scene_bounds(self):
        maps = [_map(scenes=[{"start": 2.0, "end": 5.0,
                              "caption": "students pull electrical cable"}])]
        # clip_dur larger than the scene must clamp to the scene length, in bounds
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=1, clip_dur=10.0)
        self.assertEqual(len(slots), 1)
        start, dur = slots[0]["extract_start"], slots[0]["extract_dur"]
        self.assertGreaterEqual(start, 2.0)
        self.assertLessEqual(round(start + dur, 3), 5.0)

    def test_F_centered_window_smaller_than_scene_in_bounds(self):
        maps = [_map(scenes=[{"start": 0.0, "end": 10.0,
                              "caption": "students pull electrical cable"}])]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=1, clip_dur=2.0)
        start, dur = slots[0]["extract_start"], slots[0]["extract_dur"]
        self.assertGreaterEqual(start, 0.0)
        self.assertLessEqual(round(start + dur, 3), 10.0)


class RealMapRankedRenderTest(unittest.TestCase):
    def test_G_map_ranked_window_renders_with_ffmpeg(self):
        """G: a map-ranked window actually renders (proves the plan change reaches
        real output, not just the plan dict). Drives run_mv with a project map and
        NO clip_list."""
        d = Path(tempfile.mkdtemp())
        src = d / "footage.mp4"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=8",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                       capture_output=True, check=True)
        music = d / "music.wav"
        # a 120-BPM click train so librosa.detect_beats yields a real cut grid
        # (a pure sine has no onsets → zero beats → nothing to allocate).
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=8:s=44100",
                        str(music)], capture_output=True, check=True)
        project_map = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [{
                "asset_id": "footage", "source": str(src), "asset_type": "video",
                "scenes": [
                    {"start": 0.0, "end": 3.0, "caption": "students pull electrical cable"},
                    {"start": 3.0, "end": 7.0, "caption": "team carry equipment together"},
                ],
            }],
        }
        script = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "students pull electrical cable"},
            {"segment": 2, "visual_desc": "team carry equipment together"},
        ]}
        out = d / "out.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            model=None, mat_dir=str(d), clip_list=None,
                            material_maps=project_map, verbose=False)
        self.assertTrue(out.exists() and out.stat().st_size > 0)
        map_slots = [p for p in res["plan"] if p.get("scene_id")]
        self.assertTrue(map_slots, "at least one map-ranked window must be in the plan")
        bounds = {"footage:0": (0.0, 3.0), "footage:1": (3.0, 7.0)}
        for slot in map_slots:
            lo, hi = bounds[slot["scene_id"]]
            self.assertGreaterEqual(slot["extract_start"], lo)
            self.assertLessEqual(round(slot["extract_start"] + slot["extract_dur"], 3), hi)
        paths = [e["retrieval_path"] for e in res["segments"] if "retrieval_path" in e]
        self.assertIn("map_ranked", paths)


class NoRegressionTest(unittest.TestCase):
    def test_H_source_speech_still_planned_from_map(self):
        from video_pipeline_core.material_retrieval import plan_sound_bite
        maps = expand_project_material_map([{
            "asset_id": "sp", "source": "speech.mp4",
            "speech": [{"start": 2, "end": 7, "kind": "speech", "text": "we finished"}]}])
        seg = {"segment": 7, "audio_role": "source_speech"}
        self.assertEqual(plan_sound_bite(seg, maps)["status"], "ok")

    def test_H_stock_segment_unaffected_by_local_dispatcher(self):
        # a stock segment never routes through _plan_local_segment
        a = _alloc(n_clips=1, clip_dur=3.0)
        s = {"segment": 2, "visual_desc": "aerial", "search_query": "aerial", "source": "stock"}
        ok, entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp", _fetch=lambda q, o, min_dur=0: o)
        self.assertEqual(len(ok), 1)
        self.assertNotIn("retrieval_path", entry)   # stock keeps its own contract


if __name__ == "__main__":
    unittest.main()
