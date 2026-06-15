"""SRP1 — Sequence Recipe Planner Tests.
"""
from __future__ import annotations

import copy
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import mv_cut
from video_pipeline_core.sequence_recipe_planner import plan_segment_sequence, segment_pool_from_plan
from video_pipeline_core.vt_core import FFMPEG


def _seg(desc, segment=1, extra=None):
    s = {"segment": segment, "visual_desc": desc, "material_fit": {"visual_desc": desc}}
    if extra:
        s.update(extra)
    return s


def _alloc(n_clips=2, clip_dur=2.0):
    return {"n_clips": n_clips, "clip_dur": clip_dur, "budget": clip_dur * n_clips}


class SequenceRecipePlannerTest(unittest.TestCase):

    def setUp(self):
        self.dummy_slots_2 = [
            {
                "source": "video1.mp4",
                "extract_start": 1.0,
                "extract_dur": 2.0,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "asset1:0",
                "caption": "test caption 1",
                "function": "action",
                "retrieval_score": 90.0,
                "visual_family": "family-A",
                "angle_scale": "medium"
            },
            {
                "source": "video2.mp4",
                "extract_start": 3.0,
                "extract_dur": 2.5,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "asset2:0",
                "caption": "test caption 2",
                "function": "reaction",
                "retrieval_score": 85.0,
                "visual_family": "family-B",
                "angle_scale": "close"
            }
        ]

        self.dummy_slots_3 = self.dummy_slots_2 + [
            {
                "source": "video3.mp4",
                "extract_start": 0.0,
                "extract_dur": 1.8,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "asset3:0",
                "caption": "test caption 3",
                "function": "detail",
                "retrieval_score": 88.0,
                "visual_family": "family-C",
                "angle_scale": "wide"
            }
        ]

        self.dummy_slots_4 = self.dummy_slots_3 + [
            {
                "source": "video4.mp4",
                "extract_start": 2.0,
                "extract_dur": 2.2,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "asset4:0",
                "caption": "test caption 4",
                "function": "payoff",
                "retrieval_score": 80.0,
                "visual_family": "family-D",
                "angle_scale": "medium"
            }
        ]

    def test_A_two_slots_planning(self):
        """A: 2 approved slots auto-plans context -> payoff and sets beat_role / traces."""
        segment = _seg("2 slots segment")
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_2, entry=entry)

        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"], ["context", "payoff"])
        self.assertEqual(res["recipe"]["durations"]["context"], 2.0)
        self.assertEqual(res["recipe"]["durations"]["payoff"], 2.5)
        self.assertEqual(res["recipe"]["punctuate_payoff"], True)
        self.assertEqual(res["evidence"]["approved_slot_count"], 2)
        self.assertEqual(res["evidence"]["distinct_visual_families"], 2)

    def test_B_three_slots_planning(self):
        """B: 3 approved slots auto-plans context -> primary_action -> payoff."""
        segment = _seg("3 slots segment")
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_3, entry=entry)

        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"], ["context", "primary_action", "payoff"])
        self.assertEqual(res["recipe"]["durations"]["context"], 2.0)
        self.assertEqual(res["recipe"]["durations"]["primary_action"], 2.5)
        self.assertEqual(res["recipe"]["durations"]["payoff"], 1.8)

    def test_C_four_slots_planning(self):
        """C: 4 approved slots auto-plans context -> primary_action -> detail_reaction -> payoff."""
        segment = _seg("4 slots segment")
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_4, entry=entry)

        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"], ["context", "primary_action", "detail_reaction", "payoff"])
        self.assertEqual(res["recipe"]["durations"]["context"], 2.0)
        self.assertEqual(res["recipe"]["durations"]["primary_action"], 2.5)
        self.assertEqual(res["recipe"]["durations"]["detail_reaction"], 1.8)
        self.assertEqual(res["recipe"]["durations"]["payoff"], 2.2)

    def test_D_one_slot_not_applicable(self):
        """D: only 1 slot is not applicable for auto-planning."""
        segment = _seg("1 slot segment")
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_2[:1], entry=entry)

        self.assertEqual(res["status"], "not_applicable")
        self.assertIsNone(res["recipe"])
        self.assertIn("Insufficient approved slots", res["reason"])

    def test_E_manual_beat_recipe_never_overwritten(self):
        """E: segment with existing manual beat_recipe is not overridden."""
        manual_recipe = {"beats": ["custom1", "custom2"], "punctuate_payoff": False}
        segment = _seg("manual recipe", extra={"beat_recipe": manual_recipe})
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_2, entry=entry)

        self.assertEqual(res["status"], "not_applicable")
        self.assertIsNone(res["recipe"])
        self.assertIn("already has a manual beat_recipe", res["reason"])

    def test_F_keep_audio_or_hold_not_applicable(self):
        """F: keep_audio, hold, or source_speech are not eligible."""
        # hold
        res = plan_segment_sequence(_seg("hold", extra={"hold": True}), self.dummy_slots_2, entry={"retrieval_path": "map_ranked"})
        self.assertEqual(res["status"], "not_applicable")

        # keep_audio
        res = plan_segment_sequence(_seg("keep_audio", extra={"keep_audio": True}), self.dummy_slots_2, entry={"retrieval_path": "map_ranked"})
        self.assertEqual(res["status"], "not_applicable")

        # source_speech
        res = plan_segment_sequence(_seg("speech", extra={"audio_role": "source_speech"}), self.dummy_slots_2, entry={"retrieval_path": "map_ranked"})
        self.assertEqual(res["status"], "not_applicable")

    def test_G_gap_or_fallback_not_applicable(self):
        """G: GAP slots or fallback retrieval paths are not eligible."""
        # fallback path
        res = plan_segment_sequence(_seg("fallback"), self.dummy_slots_2, entry={"retrieval_path": "matched_fallback"})
        self.assertEqual(res["status"], "not_applicable")

        # GAP slots
        gap_slots = [self.dummy_slots_2[0], {"source": "GAP", "extract_dur": 2.0}]
        res = plan_segment_sequence(_seg("gap"), gap_slots, entry={"retrieval_path": "map_ranked"})
        self.assertEqual(res["status"], "not_applicable")

    def test_H_window_integrity(self):
        """H: auto-planned recipe keeps exact source, scene_id, extract_start, extract_dur."""
        from video_pipeline_core.beat_sequence import compile_beat_sequence

        segment = _seg("integrity segment")
        entry = {"retrieval_path": "map_ranked"}
        res = plan_segment_sequence(segment, self.dummy_slots_2, entry=entry)
        self.assertEqual(res["status"], "planned")

        beat_pool = segment_pool_from_plan(self.dummy_slots_2)
        beat_seq = compile_beat_sequence(res["recipe"], beat_pool, segment=1)
        clips = beat_seq["clips"]

        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0]["source"], self.dummy_slots_2[0]["source"])
        self.assertEqual(clips[0]["extract_start"], self.dummy_slots_2[0]["extract_start"])
        self.assertEqual(clips[0]["extract_dur"], self.dummy_slots_2[0]["extract_dur"])
        self.assertEqual(clips[0]["beat_role"], "context")

        self.assertEqual(clips[1]["source"], self.dummy_slots_2[1]["source"])
        self.assertEqual(clips[1]["extract_start"], self.dummy_slots_2[1]["extract_start"])
        self.assertEqual(clips[1]["extract_dur"], self.dummy_slots_2[1]["extract_dur"])
        self.assertEqual(clips[1]["beat_role"], "payoff")

    def test_I_photo_video_mix(self):
        """I: photo assets can be planned and their is_photo/kenburns attributes are preserved."""
        slots = [
            {
                "source": "photo.png",
                "extract_start": 0.0,
                "extract_dur": 2.0,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "photo:0",
                "is_photo": True,
                "kenburns": True,
                "visual_family": "family-P"
            },
            {
                "source": "video.mp4",
                "extract_start": 1.0,
                "extract_dur": 3.0,
                "keep_audio": False,
                "segment": 1,
                "scene_id": "video:0",
                "visual_family": "family-V"
            }
        ]
        res = plan_segment_sequence(_seg("mix"), slots, entry={"retrieval_path": "map_ranked"})
        self.assertEqual(res["status"], "planned")

        from video_pipeline_core.beat_sequence import compile_beat_sequence

        beat_pool = segment_pool_from_plan(slots)
        beat_seq = compile_beat_sequence(res["recipe"], beat_pool, segment=1)
        clips = beat_seq["clips"]

        self.assertEqual(len(clips), 2)
        self.assertTrue(clips[0]["is_photo"])
        self.assertTrue(clips[0]["kenburns"])
        self.assertFalse(clips[1]["is_photo"])

    def test_K_determinism(self):
        """K: repeated planning calls on the same slots yield identical results."""
        segment = _seg("deterministic")
        entry = {"retrieval_path": "map_ranked"}
        res1 = plan_segment_sequence(segment, self.dummy_slots_3, entry=entry)
        res2 = plan_segment_sequence(segment, self.dummy_slots_3, entry=entry)
        self.assertEqual(res1, res2)

    def test_L_ffmpeg_render_integration(self):
        """L: run a real integration test where auto-planned sequence alters the timeline and renders final.mp4."""
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
                {"segment": 1, "visual_desc": "students gear", "audio_role": "music", "pace": "fast"}
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

        out = d / "final.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=maps, skip_render=False, verbose=False, max_clips_per_seg=2)

        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

        plan = res["plan"]
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["beat_role"], "context")
        self.assertEqual(plan[1]["beat_role"], "payoff")

        # Traces must exist
        self.assertEqual(plan[0]["sequence_recipe_source"], "auto")
        self.assertIn("Successfully planned sequence recipe with 2 beats", plan[0]["sequence_recipe_reason"])
        self.assertEqual(plan[0]["sequence_recipe_evidence"]["approved_slot_count"], 2)

    # --- HARDENING TESTS ---

    def test_M_lineage_preservation(self):
        """M: verifies that compile_beat_sequence preserves all lineage and evidence fields from approved slots."""
        from video_pipeline_core.beat_sequence import compile_beat_sequence

        segment = _seg("lineage")
        res = plan_segment_sequence(segment, self.dummy_slots_2, entry={"retrieval_path": "map_ranked"})
        beat_pool = segment_pool_from_plan(self.dummy_slots_2)
        beat_seq = compile_beat_sequence(res["recipe"], beat_pool, segment=1)
        clips = beat_seq["clips"]

        for idx, clip in enumerate(clips):
            orig = self.dummy_slots_2[idx]
            self.assertEqual(clip["source"], orig["source"])
            self.assertEqual(clip["scene_id"], orig["scene_id"])
            self.assertEqual(clip["retrieval_score"], orig["retrieval_score"])
            self.assertEqual(clip["visual_family"], orig["visual_family"])
            self.assertEqual(clip["angle_scale"], orig["angle_scale"])
            self.assertEqual(clip["caption"], orig["caption"])
            self.assertEqual(clip["function"], orig["function"])

    def test_N_no_deduplication_by_source(self):
        """N: verifies that same source with different scene/window bounds are NOT de-duplicated."""
        slots = [
            {
                "source": "same.mp4",
                "extract_start": 0.0,
                "extract_dur": 2.0,
                "scene_id": "same:0",
                "visual_family": "family-A"
            },
            {
                "source": "same.mp4",
                "extract_start": 5.0,
                "extract_dur": 2.0,
                "scene_id": "same:1",
                "visual_family": "family-B"
            }
        ]
        beat_pool = segment_pool_from_plan(slots)
        self.assertEqual(len(beat_pool), 2)
        self.assertEqual(beat_pool[0]["scene_id"], "same:0")
        self.assertEqual(beat_pool[1]["scene_id"], "same:1")

        # Compile and check bounds & scene_id preservation (Requirement D)
        from video_pipeline_core.beat_sequence import compile_beat_sequence
        recipe = {
            "beats": ["context", "payoff"],
            "durations": {"context": 2.0, "payoff": 2.0}
        }
        beat_seq = compile_beat_sequence(recipe, beat_pool, segment=1)
        clips = beat_seq["clips"]
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0]["scene_id"], "same:0")
        self.assertEqual(clips[0]["extract_start"], 0.0)
        self.assertEqual(clips[0]["extract_dur"], 2.0)
        self.assertEqual(clips[1]["scene_id"], "same:1")
        self.assertEqual(clips[1]["extract_start"], 5.0)
        self.assertEqual(clips[1]["extract_dur"], 2.0)

    def test_O_vd2_shared_history(self):
        """O: verifies that history is updated properly for auto sequence success, fallback, and not for manual recipe."""
        # Setup dummy music
        d = Path(tempfile.mkdtemp())
        music = d / "music.wav"
        # Pulsating audio so librosa works correctly
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=4:s=44100", str(music)], capture_output=True, check=True)

        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "dummy1.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "dummy2.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-B", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-c", "source": "dummy3.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "tool", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-d", "source": "dummy4.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "tool", "visual_family": "family-C", "angle_scale": "medium"}
                ]}
            ]
        }

        # E. Auto sequence success -> updates history, segment 2 picks family-C (photo-d) instead of family-A (photo-c)
        script_auto = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast",
                 "pacing": {"preferred_shot_sec": 1.0}},
                {"segment": 2, "visual_desc": "tool", "audio_role": "music", "pace": "fast"}
            ]
        }
        res_auto = mv_cut.run_mv(script_auto, None, str(d / "out_auto.mp4"), music_path=str(music),
                                material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
        self.assertEqual(res_auto["plan"][0]["sequence_recipe_source"], "auto")
        self.assertEqual(res_auto["plan"][-1]["scene_id"], "photo-d:0")

        # F. Manual beat recipe -> does NOT update history, segment 2 picks photo-c (family-A)
        script_manual = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast",
                 "pacing": {"preferred_shot_sec": 1.0},
                 "beat_recipe": {"beats": ["context", "payoff"],
                                 "shots": [{"source": "dummy1.png", "start": 0.0, "dur": 2.0},
                                           {"source": "dummy2.png", "start": 0.0, "dur": 2.0}]}},
                {"segment": 2, "visual_desc": "tool", "audio_role": "music", "pace": "fast"}
            ]
        }
        res_manual = mv_cut.run_mv(script_manual, None, str(d / "out_man.mp4"), music_path=str(music),
                                  material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
        self.assertNotIn("sequence_recipe_source", res_manual["plan"][0])
        self.assertEqual(res_manual["plan"][-1]["scene_id"], "photo-c:0")

        # G. Auto compiler empty/error results退回原 slots -> updates history with original slots, segment 2 picks family-C (photo-d)
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence", side_effect=ValueError("compiler error")):
            res_fallback = mv_cut.run_mv(script_auto, None, str(d / "out_fallback.mp4"), music_path=str(music),
                                         material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
            self.assertEqual(res_fallback["segments"][0]["auto_sequence_status"], "fallback")
            self.assertNotIn("sequence_recipe_source", res_fallback["plan"][0])
            self.assertEqual(res_fallback["plan"][-1]["scene_id"], "photo-d:0")

    def test_H_auto_compiler_value_error_fallback(self):
        """H: mock auto compiler raise ValueError: run_mv doesn't crash, original slots are kept, final plan is not empty, has fallback trace."""
        d = Path(tempfile.mkdtemp())
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=4:s=44100", str(music)], capture_output=True, check=True)
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "dummy1.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "dummy2.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }
        script = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast"}
            ]
        }
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence", side_effect=ValueError("mock error")):
            res = mv_cut.run_mv(script, None, str(d / "out1.mp4"), music_path=str(music),
                                material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
            self.assertTrue(res["plan"])
            self.assertNotIn("sequence_recipe_source", res["plan"][0])
            self.assertEqual(res["segments"][0]["auto_sequence_status"], "fallback")
            self.assertEqual(res["segments"][0]["auto_sequence_error"], "mock error")

    def test_I_auto_compiler_clips_empty_fallback(self):
        """I: mock auto compiler returning clips=[]: original slots are kept, has fallback trace."""
        d = Path(tempfile.mkdtemp())
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=4:s=44100", str(music)], capture_output=True, check=True)
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "dummy1.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "dummy2.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }
        script = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast"}
            ]
        }
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence", return_value={"clips": [], "cues": [], "beats_used": [], "dropped": []}):
            res = mv_cut.run_mv(script, None, str(d / "out2.mp4"), music_path=str(music),
                                material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
            self.assertTrue(res["plan"])
            self.assertNotIn("sequence_recipe_source", res["plan"][0])
            self.assertEqual(res["segments"][0]["auto_sequence_status"], "fallback")
            self.assertEqual(res["segments"][0]["auto_sequence_error"], "Compiler returned empty clips")

    def test_J_compiler_manual_recipe_raise(self):
        """J: manual recipe compiler raise propagates exception loudly."""
        d = Path(tempfile.mkdtemp())
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=4:s=44100", str(music)], capture_output=True, check=True)
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "dummy1.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "dummy2.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }
        script_manual = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast",
                 "beat_recipe": {"beats": ["context", "payoff"],
                                 "shots": [{"source": "dummy1.png", "start": 0.0, "dur": 2.0},
                                           {"source": "dummy2.png", "start": 0.0, "dur": 2.0}]}}
            ]
        }
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence", side_effect=ValueError("loud manual error")):
            with self.assertRaises(ValueError) as ctx:
                mv_cut.run_mv(script_manual, None, str(d / "out3.mp4"), music_path=str(music),
                              material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
            self.assertEqual(str(ctx.exception), "loud manual error")

    def test_Q_immutability_and_trace_only_on_success(self):
        """Q: verifies that input script deepcopy is unchanged and fallback slots don't have success trace."""
        d = Path(tempfile.mkdtemp())
        music = d / "music.wav"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d=4:s=44100", str(music)], capture_output=True, check=True)
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "dummy1.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "dummy2.png", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "gear", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast"}
            ]
        }
        script_orig = copy.deepcopy(script)

        # Run success path
        res = mv_cut.run_mv(script, None, str(d / "out_ok.mp4"), music_path=str(music),
                            material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
        self.assertEqual(script, script_orig)  # Immutability check

        # Run fallback path
        with patch("video_pipeline_core.beat_sequence.compile_beat_sequence", side_effect=ValueError("error")):
            res_fail = mv_cut.run_mv(script, None, str(d / "out_fail.mp4"), music_path=str(music),
                                     material_maps=maps, skip_render=True, verbose=False, max_clips_per_seg=2)
            self.assertEqual(script, script_orig)  # Immutability check
            for slot in res_fail["plan"]:
                self.assertNotIn("sequence_recipe_source", slot)  # No success trace on fallback slots
