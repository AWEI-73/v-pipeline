import unittest

from video_pipeline_core.material_retrieval import plan_sound_bite, rank_scenes


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


if __name__ == "__main__":
    unittest.main()
