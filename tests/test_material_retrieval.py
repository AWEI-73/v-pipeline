import unittest

from video_pipeline_core.material_retrieval import (
    plan_ranked_windows,
    plan_sound_bite,
    rank_scenes,
)


class MaterialRetrievalTest(unittest.TestCase):
    def test_rank_scenes_prefers_caption_function_and_pace_fit(self):
        segment = {
            "segment": 4,
            "material_fit": {"visual_desc": "students pull electrical cable"},
            "sequence_grammar": {"required_functions": ["action"]},
            "visual_style": {"pace": "fast"},
        }
        maps = [{
            "asset_id": "clip-a",
            "source": "a.mp4",
            "scenes": [
                {"start": 0, "end": 2, "caption": "students pull electrical cable",
                 "functions": ["action"], "motion_peaks": [1]},
                {"start": 2, "end": 8, "caption": "empty classroom",
                 "functions": ["establish"], "motion_peaks": []},
            ],
        }]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["scene_index"], 0)
        self.assertGreater(ranked[0]["score"], 0)
        self.assertEqual(ranked[0]["score_breakdown"]["text"], 2)

    def test_optional_ranker_reranks_but_cannot_admit_zero_evidence_scene(self):
        segment = {"material_fit": {"visual_desc": "cable training"}}
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "caption": "cable training"},
            {"start": 2, "end": 4, "caption": "unrelated sunset"},
        ]}]
        ranked = rank_scenes(segment, maps, ranker=lambda _segment, _scene: 100)
        self.assertEqual([item["scene_index"] for item in ranked], [0])

    def test_need_ref_priority_beats_wrong_need_caption_overlap(self):
        segment = {"segment": 2, "need_ref": "N02", "visual_desc": "night search"}
        maps = [
            {"asset_id": "n05", "source": "wrong.mp4", "need_id": "N05", "scenes": [
                {"start": 0, "end": 5, "caption": "night search team"}
            ]},
            {"asset_id": "n02", "source": "right.mp4", "need_id": "N02", "scenes": [
                {"start": 0, "end": 5, "caption": "boots on trail"}
            ]},
        ]

        ranked = rank_scenes(segment, maps)

        self.assertEqual([item["scene_id"] for item in ranked[:2]], ["n02:0", "n05:0"])
        self.assertEqual(ranked[0]["score_breakdown"]["need"], 4)
        self.assertEqual(ranked[0]["need_id"], "N02")

    def test_material_fit_need_refs_match_scene_satisfies_edges(self):
        segment = {
            "segment": 2,
            "material_fit": {"need_refs": ["N02"], "visual_desc": "night search"},
        }
        maps = [
            {"asset_id": "n05", "source": "wrong.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "night search team",
                 "satisfies": [{"need_id": "N05", "status": "accepted"}]}
            ]},
            {"asset_id": "n02", "source": "right.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "quiet boots on trail",
                 "satisfies": [{"need_id": "N02", "status": "accepted"}]}
            ]},
        ]

        ranked = rank_scenes(segment, maps)

        self.assertEqual([item["scene_id"] for item in ranked[:2]], ["n02:0", "n05:0"])
        self.assertEqual(ranked[0]["score_breakdown"]["need"], 4)
        self.assertEqual(ranked[0]["need_id"], "N02")

    def test_material_fit_need_refs_admits_satisfies_match_without_text_overlap(self):
        segment = {
            "segment": 2,
            "material_fit": {"need_refs": ["N02"], "visual_desc": "endurance run"},
        }
        maps = [{"asset_id": "n02", "source": "right.mp4", "scenes": [
            {"start": 0, "end": 5, "caption": "muddy boots closeup",
             "satisfies": [{"need_id": "N02", "status": "accepted"}]}
        ]}]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["scene_id"], "n02:0")
        self.assertEqual(ranked[0]["score_breakdown"]["need"], 4)
        self.assertEqual(ranked[0]["score_breakdown"]["text"], 0)

    def test_rejected_satisfies_edge_does_not_count_as_need_match(self):
        segment = {
            "segment": 2,
            "material_fit": {"need_refs": ["N02"], "visual_desc": "night search"},
        }
        maps = [{"asset_id": "n02", "source": "rejected.mp4", "scenes": [
            {"start": 0, "end": 5, "caption": "night search team",
             "satisfies": [{"need_id": "N02", "status": "rejected"}]}
        ]}]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["score_breakdown"]["need"], 0)
        self.assertIsNone(ranked[0]["need_id"])

    def test_need_ref_match_is_admitted_even_without_text_overlap(self):
        segment = {"segment": 2, "need_ref": "N02", "visual_desc": "endurance run"}
        maps = [{"asset_id": "n02", "source": "right.mp4", "need_id": "N02", "scenes": [
            {"start": 0, "end": 5, "caption": "muddy boots closeup"}
        ]}]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["scene_id"], "n02:0")
        self.assertEqual(ranked[0]["score_breakdown"]["text"], 0)

    def test_wrong_need_still_fallbacks_when_no_matching_need_exists(self):
        segment = {"segment": 2, "need_ref": "N02", "visual_desc": "night search"}
        maps = [{"asset_id": "n05", "source": "fallback.mp4", "need_id": "N05", "scenes": [
            {"start": 0, "end": 5, "caption": "night search team"}
        ]}]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["need_id"], "N05")

    def test_plan_ranked_windows_preserves_need_id_on_slot(self):
        segment = {"segment": 2, "need_ref": "N02", "visual_desc": "endurance run"}
        maps = [{"asset_id": "n02", "source": "right.mp4", "need_id": "N02", "scenes": [
            {"start": 0, "end": 5, "caption": "muddy boots closeup"}
        ]}]

        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)

        self.assertEqual(slots[0]["need_id"], "N02")
        self.assertEqual(slots[0]["retrieval_score"], 4)

    def test_bad_window_range_does_not_starve_valid_lower_rank(self):
        segment = {"material_fit": {"visual_desc": "rope rescue climber"}}
        maps = [
            {"asset_id": "bad", "source": "bad.mp4", "asset_type": "video", "scenes": [
                {
                    "start": 0.0,
                    "end": 6.0,
                    "caption": "rope rescue climber",
                    "avoid_ranges": [{"start": 2.0, "end": 4.0, "reason": "black_transition"}],
                }
            ]},
            {"asset_id": "ok", "source": "ok.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 6.0, "caption": "rope rescue"}
            ]},
        ]

        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "ok:0")
        self.assertEqual(slots[0]["window_quality_reason"], "ok")

    def test_bad_window_range_outside_selected_window_does_not_block(self):
        segment = {"material_fit": {"visual_desc": "rope rescue climber"}}
        maps = [{"asset_id": "clip", "source": "clip.mp4", "asset_type": "video", "scenes": [
            {
                "start": 0.0,
                "end": 10.0,
                "caption": "rope rescue climber",
                "avoid_ranges": [{"start": 0.0, "end": 1.0, "reason": "black_head"}],
            }
        ]}]

        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip:0")
        self.assertEqual(slots[0]["extract_start"], 4.0)

    def test_all_bad_windows_fall_back_to_least_bad_with_trace(self):
        segment = {"material_fit": {"visual_desc": "rope rescue climber"}}
        maps = [{"asset_id": "bad", "source": "bad.mp4", "asset_type": "video", "scenes": [
            {
                "start": 0.0,
                "end": 6.0,
                "caption": "rope rescue climber",
                "avoid_ranges": [{"start": 0.0, "end": 6.0, "reason": "black_transition"}],
            }
        ]}]

        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "bad:0")
        self.assertEqual(slots[0]["window_quality_reason"], "black_transition")
        self.assertTrue(slots[0]["window_quality_fallback"])

    def test_photo_ignores_video_avoid_ranges(self):
        segment = {"material_fit": {"visual_desc": "storybook panel"}}
        maps = [{"asset_id": "photo", "source": "panel.png", "asset_type": "photo", "scenes": [
            {
                "start": 0.0,
                "end": 0.0,
                "caption": "storybook panel",
                "avoid_ranges": [{"start": 0.0, "end": 10.0, "reason": "video_black"}],
            }
        ]}]

        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=3.0)

        self.assertEqual(len(slots), 1)
        self.assertTrue(slots[0]["is_photo"])

    def test_soul_ranking_changes_same_tier_selection_when_enabled(self):
        segment = {
            "material_fit": {"visual_desc": "training"},
            "core": {
                "emotional_movement": "fear to courage",
                "conflict_or_turn": "the student chooses courage",
                "intended_viewer_feeling": "brave focus",
            },
            "director_intent": {
                "material_prompt_requirements": ["teacher", "courage"],
            },
        }
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "training wide shot"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "training courage teacher closeup"}
            ]},
        ]

        off = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0, soul_ranking=False)
        on = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0, soul_ranking=True)

        self.assertEqual(off[0]["scene_id"], "clip-a:0")
        self.assertEqual(on[0]["scene_id"], "clip-b:0")
        self.assertGreater(on[0]["score_breakdown"]["soul"], 0)

    def test_soul_ranking_does_not_admit_zero_base_evidence_or_override_need(self):
        soul_segment = {
            "material_fit": {"visual_desc": "night search", "need_refs": ["N02"]},
            "core": {"emotional_movement": "fear to courage"},
        }
        maps = [
            {"asset_id": "need-fit", "source": "need.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "quiet boots",
                 "satisfies": [{"need_id": "N02", "status": "accepted"}]}
            ]},
            {"asset_id": "soul-only", "source": "soul.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "courage ceremony"}
            ]},
            {"asset_id": "zero-base", "source": "zero.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "fear courage"}
            ]},
        ]

        ranked = rank_scenes(soul_segment, maps)

        self.assertEqual(ranked[0]["scene_id"], "need-fit:0")
        self.assertEqual(ranked[0]["score_breakdown"]["need"], 4)
        self.assertNotIn("zero-base:0", [item["scene_id"] for item in ranked])

    def test_source_speech_selects_transcribed_speech_run(self):
        segment = {"segment": 7, "audio": {"role": "source_speech"}}
        maps = [{"asset_id": "speech-a", "source": "speech.mp4", "speech": [
            {"start": 0, "end": 2, "kind": "silence"},
            {"start": 2, "end": 7, "kind": "speech", "text": "We finished together"},
        ]}]
        result = plan_sound_bite(segment, maps)
        self.assertEqual(result["source"], "speech.mp4")
        self.assertEqual(result["extract_start"], 2)
        self.assertEqual(result["extract_dur"], 5)
        self.assertTrue(result["keep_audio"])

    def test_flat_runtime_audio_role_requests_source_speech(self):
        segment = {"segment": 7, "audio_role": "source_speech"}
        maps = [{"source": "speech.mp4", "speech": [
            {"start": 1, "end": 3, "kind": "speech", "text": "Ready"},
        ]}]
        self.assertEqual(plan_sound_bite(segment, maps)["status"], "ok")

    def test_source_speech_without_speech_is_gap(self):
        result = plan_sound_bite({"segment": 7, "audio": {"role": "source_speech"}}, [])
        self.assertEqual(result["status"], "gap")

    def test_vd2_A_high_evidence_score_preferred_to_new_family(self):
        # High score duplicate family must be preferred to low score new family
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue climber", "visual_family": "rope_rescue_action"}  # High score, text=2, total=2
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rescue training", "visual_family": "stretcher_carry"}   # Low score, text=1, total=1
            ]}
        ]
        # We select with limit=1, but first select one so rope_rescue_action is already in history/used
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        history = [{"visual_family": "rope_rescue_action", "angle_scale": "medium"}]
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0, history=history)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip-a:0") # High score wins even though family is already used

    def test_vd2_B_same_score_prefers_different_family(self):
        # Same evidence score, choose different visual_family
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "stretcher_carry"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        history = [{"visual_family": "rope_rescue_action", "angle_scale": "medium"}]
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0, history=history)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip-b:0") # b has unused family, should be preferred

    def test_vd2_C_same_family_prefers_different_scale(self):
        # Same family, prefer different angle_scale
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "close"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        history = [{"visual_family": "rope_rescue_action", "angle_scale": "medium"}]
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0, history=history)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip-b:0") # b has different scale than history, preferred

    def test_vd2_D_same_family_scale_prefers_video_over_photo(self):
        # Same family/scale, video preferred over photo
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "photo", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip-b:0") # b is video, preferred

    def test_vd2_E_missing_labels_keeps_legacy_order(self):
        # Missing VD0 labels, results match legacy deterministic sorting (by scene_id ascending)
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-b", "source": "b.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue"}
            ]},
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=2, clip_dur=2.0)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["scene_id"], "clip-a:0")
        self.assertEqual(slots[1]["scene_id"], "clip-b:0")

    def test_vd2_F_allow_reuse_and_no_gap(self):
        # Insufficient candidates, allow reuse (i.e. select same family/scale), no empty slots/GAPs
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=2, clip_dur=2.0)
        # We only have 1 renderable candidate in maps, so we only get 1 slot.
        # But it should not crash, raise errors, or return GAP when we requested limit=2.
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "clip-a:0")

    def test_vd2_G_integrity_preserved(self):
        # Diversity selection does not mutate candidate fields
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["source"], "a.mp4")
        self.assertEqual(slots[0]["scene_id"], "clip-a:0")
        self.assertEqual(slots[0]["extract_start"], 1.5) # centered in [0, 5] for clip_dur=2
        self.assertEqual(slots[0]["extract_dur"], 2.0)
        self.assertEqual(slots[0]["retrieval_score"], 2)

    def test_vd2_H_determinism(self):
        # Deterministic output
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "rope_rescue_action", "angle_scale": "medium"}
            ]},
            {"asset_id": "clip-b", "source": "b.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "rope rescue", "visual_family": "stretcher_carry", "angle_scale": "close"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots1 = plan_ranked_windows(segment, maps, limit=2, clip_dur=2.0)
        slots2 = plan_ranked_windows(segment, maps, limit=2, clip_dur=2.0)
        self.assertEqual(slots1, slots2)

    def test_vd2_I_no_distractor_selected(self):
        # Zero-fit scene not selected due to diversity
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "clip-a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 5, "caption": "unrelated sunset", "visual_family": "forest_landscape"} # text=0, zero-fit
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(slots, [])


    def test_vd2_A_adjacent_segment_score_tie(self):
        # Two adjacent segments asking for same desc. Under tie, segment 1 chooses family-A,
        # segment 2 should choose family-B because family-A was added to history.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        # SRP2 may prepend an auto opening; this test is about story selection.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(len(plan), 2)
        # Segment 1 gets clip-a (smaller scene_id, first choice)
        self.assertEqual(plan[0]["scene_id"], "clip-a:0")
        # Segment 2 gets clip-b (since family-A is now in history)
        self.assertEqual(plan[1]["scene_id"], "clip-b:0")

    def test_vd2_B_correctness_score_tier_priority(self):
        # Even if family-A is in history, if it has a higher correctness score, it must still be preferred.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue climber", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue climber", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        # SRP2 may prepend an auto opening; this test is about story selection.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(len(plan), 2)
        # Segment 1 gets clip-a:0 (score 2 vs 1)
        self.assertEqual(plan[0]["scene_id"], "clip-a:0")
        # Segment 2 gets clip-a:0 too, because its correctness score tier is higher (score 2 vs 1) despite family-A being in history
        self.assertEqual(plan[1]["scene_id"], "clip-a:0")

    def test_vd2_C_no_pollution_from_fallback_or_gap(self):
        # matched/live/GAP/stock do not write to shared history.
        # Segment 1 goes to fallback and yields family-A.
        # Segment 2 has tie candidates: clip-a (family-A) and clip-b (family-B).
        # Deterministic tie-breaker selects clip-a alphabetically.
        # Since fallback didn't pollute history, segment 2 selects clip-a:0.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "unrelated sky", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._plan_live_segment", lambda *a, **k: ([{"source": "live.mp4", "extract_start": 0, "extract_dur": 2, "visual_family": "family-A"}], {"segment": 1}, [])):
            res = mv_cut.run_mv(script, "/materials", "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        plan = res["plan"]
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["source"], "live.mp4")
        # If history was polluted with family-A, segment 2 would choose clip-b:0.
        # Since it's clean, it chooses clip-a:0.
        self.assertEqual(plan[1]["scene_id"], "clip-a:0")

    def test_vd2_D_determinism_across_calls(self):
        # Two consecutive runs do not inherit history.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])):
            res1 = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                 material_maps=maps, skip_render=True, verbose=False)
            res2 = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                 material_maps=maps, skip_render=True, verbose=False)

        self.assertEqual(res1["plan"], res2["plan"])


    def test_vd2_beat_recipe_no_beat_recipe(self):
        # A: No beat_recipe -> map-ranked slots are written to history.
        # Segment 1 gets clip-a:0. Since it has no beat_recipe, it writes family-A to history.
        # Segment 2 gets clip-b:0 because family-A is in history.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        # SRP2 may prepend an auto opening; this test is about story selection.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(plan[0]["scene_id"], "clip-a:0")
        self.assertEqual(plan[1]["scene_id"], "clip-b:0")

    def test_vd2_beat_recipe_effective_replacement(self):
        # B: beat_recipe compiles successfully and replaces slots.
        # The old map-ranked slots (clip-a) are discarded and NOT written to history.
        # Segment 2 has no family-A in history, so segment 2 still prefers clip-a:0 (alphabetically).
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music", "beat_recipe": {"shots": []}},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        # Mock compile_beat_sequence to return a dummy replaced clip
        dummy_beat_seq = {
            "clips": [{"source": "replaced.mp4", "extract_start": 0.0, "extract_dur": 2.0}],
            "cues": [], "beats_used": 1, "dropped": 0
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.beat_sequence.compile_beat_sequence", lambda *a, **k: dummy_beat_seq):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        plan = res["plan"]
        self.assertEqual(plan[0]["source"], "replaced.mp4")
        # Since family-A was not written to history, segment 2 chooses clip-a:0
        self.assertEqual(plan[1]["scene_id"], "clip-a:0")

    def test_vd2_beat_recipe_empty_clips(self):
        # C: beat_recipe compiles to empty list clips=[].
        # Original map-ranked slots (clip-a) remain in plan and MUST be written to history.
        # Segment 2 therefore avoids family-A and selects clip-b:0.
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music", "beat_recipe": {"shots": []}},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "clip-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "clip-b", "source": "b.mp4", "asset_type": "video", "scenes": [
                    {"start": 0.0, "end": 5.0, "caption": "rope rescue climber", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        # Mock compile_beat_sequence to return empty clips list
        empty_beat_seq = {
            "clips": [], "cues": [], "beats_used": 0, "dropped": 1
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.beat_sequence.compile_beat_sequence", lambda *a, **k: empty_beat_seq):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        # SRP2 may prepend an auto opening; this test is about story selection.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(plan[0]["scene_id"], "clip-a:0") # Original stays
        # Since original stayed, family-A was written to history, so segment 2 selects clip-b:0
        self.assertEqual(plan[1]["scene_id"], "clip-b:0")

    def test_vd2_photo_A_selectable_with_zero_bounds(self):
        # A. photo start=0/end=0: selectable, extract_start=0, extract_dur=clip_dur
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=3.5)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "photo-a:0")
        self.assertEqual(slots[0]["extract_start"], 0.0)
        self.assertEqual(slots[0]["extract_dur"], 3.5)
        self.assertTrue(slots[0]["is_photo"])
        self.assertTrue(slots[0]["kenburns"])

    def test_vd2_photo_B_video_preferred_to_photo(self):
        # B. 同分 video 與 photo: video 優先
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]},
            {"asset_id": "video-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 5.0, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "video-a:0")

    def test_vd2_photo_C_correctness_priority_over_media_type(self):
        # C. 高 correctness photo 與低 correctness video: 高分 photo 優先
        segment = {"material_fit": {"visual_desc": "rope rescue climber"}} # exact match for caption
        maps = [
            {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue climber"} # score=2
            ]},
            {"asset_id": "video-a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0.0, "end": 5.0, "caption": "rope training"} # score=1
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "photo-a:0")

    def test_vd2_photo_D_only_photo_no_gap(self):
        # D. 只有 photo 素材: 不得 GAP，產生 timeline slot
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["scene_id"], "photo-a:0")

    def test_vd2_photo_E_source_missing_or_empty_dropped(self):
        # E. photo source 缺失/空白: 不得進 timeline
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "photo-a", "source": "", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]},
            {"asset_id": "photo-b", "source": None, "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=2.0)
        self.assertEqual(slots, [])

    def test_vd2_photo_F_invalid_clip_dur_fails(self):
        # F. 非法 clip_dur: 0、負數、NaN、Infinity 必須 fail/drop
        segment = {"material_fit": {"visual_desc": "rope rescue"}}
        maps = [
            {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                {"start": 0.0, "end": 0.0, "caption": "rope rescue"}
            ]}
        ]
        from video_pipeline_core.material_retrieval import plan_ranked_windows
        for bad_dur in [0, -1.5, float("nan"), float("inf"), float("-inf")]:
            slots = plan_ranked_windows(segment, maps, limit=1, clip_dur=bad_dur)
            self.assertEqual(slots, [], f"Failed to drop invalid clip_dur: {bad_dur}")

    def test_vd2_photo_G_cross_segment_photo_diversity(self):
        # G. 跨段 photo diversity:
        # 第一段選 family-A photo
        # 第二段同分時選 family-B photo
        # shared_history 正常生效
        from unittest.mock import patch
        from video_pipeline_core import mv_cut

        script = {
            "segments": [
                {"segment": 1, "visual_desc": "rope rescue", "audio_role": "music"},
                {"segment": 2, "visual_desc": "rope rescue", "audio_role": "music"}
            ]
        }
        maps = {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "photo-a", "source": "a.jpg", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "rope rescue", "visual_family": "family-A", "angle_scale": "medium"}
                ]},
                {"asset_id": "photo-b", "source": "b.jpg", "asset_type": "photo", "scenes": [
                    {"start": 0.0, "end": 0.0, "caption": "rope rescue", "visual_family": "family-B", "angle_scale": "medium"}
                ]}
            ]
        }

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])):
            res = mv_cut.run_mv(script, None, "/out.mp4", music_path="/music.wav",
                                material_maps=maps, skip_render=True, verbose=False)

        # SRP2 may prepend an auto opening; this test is about story selection.
        plan = [c for c in res["plan"] if not c.get("opening_role")]
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["scene_id"], "photo-a:0")
        self.assertEqual(plan[1]["scene_id"], "photo-b:0")


if __name__ == "__main__":
    unittest.main()
