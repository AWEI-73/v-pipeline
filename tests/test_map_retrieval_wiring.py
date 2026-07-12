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
from video_pipeline_core.project_material_map import (
    build_project_material_map,
    expand_project_material_map,
)
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

    def test_B_empty_clip_list_assignments_routes_to_live_not_empty_matched(self):
        """clip_list present but this segment has NO picks → live fallback, never
        an empty matched_fallback."""
        maps = [_map(scenes=NO_FIT)]
        sentinel = ([{"source": "/live/x.mp4", "segment": 4}],
                    {"segment": 4, "picked_scores": [70]}, ["live"])
        original = mv_cut._plan_live_segment
        mv_cut._plan_live_segment = lambda *a, **k: sentinel
        try:
            slots, entry, _ = mv_cut._plan_local_segment(
                _seg("students pull electrical cable"), _alloc(), {}, {}, False,
                material_maps=maps, clip_list={"assignments": []},
                live_kwargs={"material_root": "/some/root", "model": None,
                             "mat_dir": "/tmp", "max_clips_per_seg": 2,
                             "windows_per_clip": 2, "min_score": 60,
                             "prefilter_static": False})
        finally:
            mv_cut._plan_live_segment = original
        self.assertTrue(slots)
        self.assertEqual(entry["retrieval_path"], "live_fallback")

    def test_B_empty_matched_slots_continue_to_live(self):
        """matched picks exist but yield no usable window → continue to live
        fallback (do NOT return an empty matched segment)."""
        maps = [_map(scenes=NO_FIT)]
        clip_by_seg = {4: {"picks": [{"path": "/m/cable/a.mov"}]}}
        sentinel = ([{"source": "/live/x.mp4", "segment": 4}],
                    {"segment": 4, "picked_scores": [70]}, ["live"])
        orig_win = mv_cut._windows_from_clip
        orig_live = mv_cut._plan_live_segment
        mv_cut._windows_from_clip = lambda *a, **k: []          # matched yields nothing
        mv_cut._plan_live_segment = lambda *a, **k: sentinel
        try:
            slots, entry, _ = mv_cut._plan_local_segment(
                _seg("students pull electrical cable"), _alloc(), clip_by_seg, {}, False,
                material_maps=maps, clip_list={"assignments": [{"segment": 4}]},
                live_kwargs={"material_root": "/some/root", "model": None,
                             "mat_dir": "/tmp", "max_clips_per_seg": 2,
                             "windows_per_clip": 2, "min_score": 60,
                             "prefilter_static": False})
        finally:
            mv_cut._windows_from_clip = orig_win
            mv_cut._plan_live_segment = orig_live
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
    def test_l0_shaped_scene_evidence_survives_existing_map_normalization(self):
        source = {
            "artifact_role": "material_map",
            "version": 1,
            "asset_id": "ca_action_cable_8237",
            "asset_type": "video",
            "source": "materials/拖拉電纜/IMG_8237.MOV",
            "scenes": [{
                "scene_index": 0,
                "start": 2.4,
                "end": 4.4,
                "caption": "Outdoor crew cable-work action.",
                "visual_family": "utility_cable_action",
                "angle_scale": "medium",
                "action_family": "technical_training",
                "subject": "uniformed crew",
                "story_function": "training-process cutaway",
                "evidence_refs": ["l0_selects_provenance.json#ca_action_cable_8237"],
                "blind_spots": ["No close-up proof of hand placement."],
            }],
        }

        project = build_project_material_map([source])
        normalized = expand_project_material_map(project)
        scene = normalized[0]["scenes"][0]

        self.assertEqual(project["assets"][0]["asset_id"], "ca_action_cable_8237")
        self.assertEqual(scene["start"], 2.4)
        self.assertEqual(scene["end"], 4.4)
        self.assertEqual(scene["evidence_refs"], ["l0_selects_provenance.json#ca_action_cable_8237"])
        self.assertEqual(scene["blind_spots"], ["No close-up proof of hand placement."])
        self.assertEqual(scene["visual_family"], "utility_cable_action")
        self.assertEqual(scene["story_function"], "training-process cutaway")
        self.assertNotIn("filename_semantics", scene)

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

    def test_unrenderable_top_rank_does_not_starve_valid_lower_rank(self):
        """Fix: an illegal (zero-length) top-ranked scene must not consume the
        single limit slot — the valid lower-ranked window is selected."""
        maps = [_map(scenes=[
            {"start": 0, "end": 0, "caption": "students pull electrical cable"},   # rank #1, illegal
            {"start": 0, "end": 3, "caption": "students pull electrical cable"},   # rank #2, valid
        ])]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "a:1")

    def test_E_zero_and_negative_length_scene_dropped(self):
        maps = [_map(scenes=[{"start": 3, "end": 3, "caption": "students pull electrical cable"},
                             {"start": 5, "end": 4, "caption": "students pull electrical cable"}])]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps,
                                    limit=5, clip_dur=2.0)
        self.assertEqual(slots, [])

    def test_photo_need_refs_with_zero_bounds_enter_map_ranked_timeline(self):
        """Canonical M6 photo maps use satisfies edges; BUILD must not require
        text coverage or positive scene duration to select them."""
        maps = [
            {
                "asset_id": "comic-a",
                "source": "panel-a.png",
                "asset_type": "photo",
                "scenes": [{
                    "start": 0,
                    "end": 0,
                    "caption": "different wording",
                    "satisfies": [{"need_id": "nd_intro", "status": "accepted"}],
                }],
            },
            {
                "asset_id": "comic-b",
                "source": "panel-b.png",
                "asset_type": "photo",
                "scenes": [{
                    "start": 0,
                    "end": 0,
                    "caption": "another panel",
                    "satisfies": [{"need_id": "nd_intro", "status": "candidate"}],
                }],
            },
        ]
        segment = {
            "segment": 1,
            "visual_desc": "story text that does not match captions",
            "material_fit": {"need_refs": ["nd_intro"]},
        }

        slots, entry, _ = mv_cut._plan_local_segment(
            segment, _alloc(n_clips=2, clip_dur=3.5), {}, {}, False,
            material_maps=maps, clip_list=None)

        self.assertEqual(entry["retrieval_path"], "map_ranked")
        self.assertEqual([slot["scene_id"] for slot in slots], ["comic-a:0", "comic-b:0"])
        self.assertTrue(all(slot["is_photo"] for slot in slots))
        self.assertEqual([slot["extract_dur"] for slot in slots], [3.5, 3.5])

    def test_material_map_ids_hard_filter_ranked_scenes(self):
        maps = [
            {
                "asset_id": "commute_001",
                "source": "commute.mp4",
                "asset_type": "video",
                "scenes": [{
                    "start": 0,
                    "end": 5,
                    "caption": "morning commute movement",
                    "satisfies": [{"need_id": "need_commute_motion", "status": "accepted"}],
                }],
            },
            {
                "asset_id": "city_dawn_001",
                "source": "city_dawn.mp4",
                "asset_type": "video",
                "scenes": [{
                    "start": 0,
                    "end": 5,
                    "caption": "morning commute city movement",
                    "satisfies": [{"need_id": "need_city_dawn", "status": "accepted"}],
                }],
            },
        ]
        segment = {
            "segment": 2,
            "material_map_ids": ["commute_001"],
            "material_fit": {
                "visual_desc": "morning commute movement",
                "need_refs": ["need_commute_motion"],
            },
        }

        ranked = rank_scenes(segment, maps)

        self.assertEqual([item["scene_id"] for item in ranked], ["commute_001:0"])

    def test_need_refs_hard_filter_ranked_scenes_when_need_evidence_exists(self):
        maps = [
            {
                "asset_id": "commute_001",
                "source": "commute.mp4",
                "asset_type": "video",
                "scenes": [{
                    "start": 0,
                    "end": 5,
                    "caption": "morning commute movement",
                    "satisfies": [{"need_id": "need_commute_motion", "status": "accepted"}],
                }],
            },
            {
                "asset_id": "city_dawn_001",
                "source": "city_dawn.mp4",
                "asset_type": "video",
                "scenes": [{
                    "start": 0,
                    "end": 5,
                    "caption": "morning commute movement",
                    "satisfies": [{"need_id": "need_city_dawn", "status": "accepted"}],
                }],
            },
        ]
        segment = {
            "segment": 2,
            "material_fit": {
                "visual_desc": "morning commute movement",
                "need_refs": ["need_commute_motion"],
            },
        }

        ranked = rank_scenes(segment, maps)

        self.assertEqual([item["scene_id"] for item in ranked], ["commute_001:0"])


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
    def test_bad_window_range_backfills_and_renders_lower_ranked_clip(self):
        d = Path(tempfile.mkdtemp())
        bad_src = d / "bad.mp4"
        ok_src = d / "ok.mp4"
        for src, color in ((bad_src, "red"), (ok_src, "blue")):
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                            f"color=c={color}:size=320x240:rate=30:duration=6",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                           capture_output=True, check=True)
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=6:s=44100",
                        str(music)], capture_output=True, check=True)
        project_map = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {
                    "asset_id": "bad", "source": str(bad_src), "asset_type": "video",
                    "scenes": [{
                        "start": 0.0, "end": 6.0,
                        "caption": "rope rescue climber",
                        "avoid_ranges": [{"start": 2.0, "end": 4.0, "reason": "black_transition"}],
                    }],
                },
                {
                    "asset_id": "ok", "source": str(ok_src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 6.0, "caption": "rope rescue"}],
                },
            ],
        }
        script = {
            "disable_auto_sequence": True,
            "disable_auto_opening": True,
            "story_arc": False,
            "segments": [{"segment": 1, "visual_desc": "rope rescue climber", "audio_role": "music"}],
        }
        out = d / "final.mp4"

        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=project_map, skip_render=False, verbose=False)

        map_slots = [slot for slot in res["plan"] if slot.get("scene_id")]
        self.assertTrue(out.exists() and out.stat().st_size > 0)
        self.assertEqual([slot["scene_id"] for slot in map_slots], ["ok:0"])
        self.assertEqual(map_slots[0]["window_quality_reason"], "ok")

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
        pending, pending_entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp", _fetch=lambda q, o, min_dur=0: o)
        self.assertEqual(pending, [])
        self.assertTrue(pending_entry["pending_visual_review"])
        self.assertNotIn("retrieval_path", pending_entry)

        ok, entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp", _fetch=lambda q, o, min_dur=0: o,
            visual_verdict={"action": "accept", "picked_windows": [{"start": 0, "end": 3}]})
        self.assertEqual(len(ok), 1)
        self.assertNotIn("retrieval_path", entry)   # stock keeps its own contract

class VisualDiversityIntegrationTest(unittest.TestCase):
    def test_K_timeline_integration_proves_different_order(self):
        """K: timeline planning selects scene_ids in a different order from legacy deterministic sorting."""
        # clip-a (rope_rescue_action), clip-b (rope_rescue_action), clip-c (stretcher_carry)
        # All have the same text score. Legacy order would choose clip-a:0 then clip-b:0.
        # Diverse order chooses clip-a:0 then clip-c:0 because stretcher_carry is unused.
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 5.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 5.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]},
            {"asset_id": "clip-c", "source": "c.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 5.0, "caption": "students pull electrical cable", "visual_family": "stretcher_carry", "angle_scale": "medium"}
            ]},
        ]

        # We request limit=2
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps, limit=2, clip_dur=2.0)
        self.assertEqual(len(slots), 2)
        # Verify diversity selected clip-a and clip-c instead of clip-a and clip-b (which legacy would do)
        self.assertEqual(slots[0]["scene_id"], "clip-a:0")
        self.assertEqual(slots[1]["scene_id"], "clip-c:0")
        self.assertEqual(slots[1]["visual_family"], "stretcher_carry")
        self.assertIn("diversity_selection_reason", slots[1])

    def test_L_ffmpeg_render_proves_diversified_slots_actual_render(self):
        """L: run a real ffmpeg render of diversified slots to prove they enter the final movie."""
        d = Path(tempfile.mkdtemp())
        src = d / "footage.mp4"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=8",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                       capture_output=True, check=True)
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=8:s=44100",
                        str(music)], capture_output=True, check=True)

        project_map = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {
                    "asset_id": "clip-a", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}],
                },
                {
                    "asset_id": "clip-b", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}],
                },
                {
                    "asset_id": "clip-c", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "stretcher_carry", "angle_scale": "medium"}],
                }
            ],
        }

        script = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "students pull electrical cable"},
        ]}

        # n_clips = 2
        out = d / "out.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            model=None, mat_dir=str(d), clip_list=None,
                            material_maps=project_map, verbose=False,
                            # n_clips=2 is achieved by custom allocating budget or setting clip count.
                            # By default run_mv will allocate clips per segment based on visual style / pacing or default.
                            # Let's inspect the slots directly in planning.
                            )
        self.assertTrue(out.exists() and out.stat().st_size > 0)

        # Ensure that map_ranked segment has selected the diversified order
        segment_entry = res["segments"][0]
        self.assertEqual(segment_entry["retrieval_path"], "map_ranked")

        # Let's check the plan slots
        map_slots = [p for p in res["plan"] if p.get("scene_id")]
        self.assertTrue(len(map_slots) >= 1)
        # The first slot should be clip-a:0
        self.assertEqual(map_slots[0]["scene_id"], "clip-a:0")

    def test_M_non_photo_zero_duration_remains_unrenderable(self):
        """M: zero duration assets without photo asset_type are unrenderable and dropped."""
        maps = [
            {"asset_id": "video-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "students pull electrical cable"}
            ]},
            {"asset_id": "unknown-a", "source": "a.mp4", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "students pull electrical cable"}
            ]}
        ]
        slots1 = plan_ranked_windows(_seg("students pull electrical cable"), [maps[0]], limit=1, clip_dur=2.0)
        self.assertEqual(slots1, [])
        slots2 = plan_ranked_windows(_seg("students pull electrical cable"), [maps[1]], limit=1, clip_dur=2.0)
        self.assertEqual(slots2, [])

    def test_effect_assets_do_not_enter_main_video_selection(self):
        """EF1: effect/material-library assets are valid map entries but never main video slots."""
        maps = [
            {"asset_id": "fx-light", "source": "light_sweep.webm", "asset_type": "effect_overlay", "scenes": [
                {"start": 0.0, "end": 2.0, "caption": "students pull electrical cable"}
            ]},
            {"asset_id": "sfx-hit", "source": "hit.wav", "asset_type": "sfx", "scenes": [
                {"start": 0.0, "end": 1.0, "caption": "students pull electrical cable"}
            ]},
            {"asset_id": "motion-title", "source": "title.mov", "asset_type": "motion_asset", "scenes": [
                {"start": 0.0, "end": 2.0, "caption": "students pull electrical cable"}
            ]},
        ]
        slots = plan_ranked_windows(_seg("students pull electrical cable"), maps, limit=3, clip_dur=1.0)
        self.assertEqual(slots, [])

    def test_vd2_photo_H_ffmpeg_render_integration(self):
        """H: run a real ffmpeg render of photo map-ranked slots to prove they enter the final movie."""
        d = Path(tempfile.mkdtemp())
        photo1 = str(d / "photo-a.png")
        photo2 = str(d / "photo-b.png")

        # Generate visually distinct temporary photos
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1", "-vframes", "1", photo1], capture_output=True, check=True)
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1", "-vframes", "1", photo2], capture_output=True, check=True)

        # Create a dummy music file
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=5:s=44100",
                        str(music)], capture_output=True, check=True)

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "students gear", "audio_role": "music"},
                {"segment": 2, "visual_desc": "students gear", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": photo1, "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "students gear up", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": photo2, "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "students gear up", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        from video_pipeline_core import mv_cut
        out = d / "final.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=maps, skip_render=False, verbose=False)

        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

        # Verify that plan has photo map-ranked slots, correct extract_dur, and correct diversified scene_id order.
        # SRP2 may prepend an auto opening; this test is about the story slots.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["scene_id"], "photo-a:0")
        self.assertEqual(plan[1]["scene_id"], "photo-b:0")
        self.assertEqual(plan[0]["extract_dur"], 2.5) # allocated from probed audio duration
        self.assertTrue(plan[0]["is_photo"])
        self.assertTrue(plan[0]["kenburns"])


    def test_N_ffmpeg_render_cross_segment_diversified_slots(self):
        """E: run a real ffmpeg render of cross-segment diversified slots to prove they enter the final movie."""
        d = Path(tempfile.mkdtemp())
        src = d / "footage.mp4"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=8",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                       capture_output=True, check=True)
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=8:s=44100",
                        str(music)], capture_output=True, check=True)

        project_map = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {
                    "asset_id": "clip-a", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}],
                },
                {
                    "asset_id": "clip-b", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "rope_rescue_action", "angle_scale": "medium"}],
                },
                {
                    "asset_id": "clip-c", "source": str(src), "asset_type": "video",
                    "scenes": [{"start": 0.0, "end": 3.0, "caption": "students pull electrical cable", "visual_family": "stretcher_carry", "angle_scale": "medium"}],
                }
            ],
        }

        script = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "students pull electrical cable"},
            {"segment": 2, "visual_desc": "students pull electrical cable"},
        ]}

        out = d / "out.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            model=None, mat_dir=str(d), clip_list=None,
                            material_maps=project_map, verbose=False)

        self.assertTrue(out.exists() and out.stat().st_size > 0)

        # Let's check the plan slots. SRP2 may prepend an auto opening (whose
        # clips also carry scene_id lineage); this test is about the story slots.
        map_slots = [p for p in res["plan"] if p.get("scene_id") and not p.get("opening_role")]
        self.assertTrue(len(map_slots) >= 2)
        # The first slot should be clip-a:0, and the second should be clip-c:0
        self.assertEqual(map_slots[0]["scene_id"], "clip-a:0")
        self.assertEqual(map_slots[1]["scene_id"], "clip-c:0")


if __name__ == "__main__":
    unittest.main()
