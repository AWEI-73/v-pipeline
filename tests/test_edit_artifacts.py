"""edit_artifacts — Node 9 assembly_plan and Node 10 timeline_build."""
import unittest

from video_pipeline_core import edit_artifacts as ea


class EditArtifactsTest(unittest.TestCase):
    def test_build_assembly_plan_separates_intent_from_timestamps(self):
        script = {
            "_contract_hash": "sha256:abc",
            "segments": [{
                "segment": 1,
                "_from_contract": 1,
                "visual_desc": "校園晨景",
                "material_hint": "空拍",
                "must_include": "校門",
                "audio_role": "music",
                "label": "開場",
                "pace": "hold",
                "needs_review": True,
            }]
        }
        plan = ea.build_assembly_plan(script, music_structure={"sections": [{"name": "Intro"}]})
        seg = plan["segments"][0]
        self.assertEqual(plan["assembly_plan_version"], 1)
        self.assertEqual(plan["contract_hash"], "sha256:abc")
        self.assertEqual(seg["segment"], 1)
        self.assertEqual(seg["story_purpose"], "校園晨景")
        self.assertEqual(seg["candidate_policy"]["must_include"], "校門")
        self.assertEqual(seg["shot_plan"]["shots"][0]["source_hint"], "空拍")
        self.assertNotIn("start_sec", seg["shot_plan"]["shots"][0])

    def test_build_assembly_plan_scopes_beat_grid_to_rendered_timeline(self):
        script = {"segments": [
            {"segment": 1, "weight": 1.0},
            {"segment": 2, "weight": 1.0},
        ]}

        plan = ea.build_assembly_plan(
            script,
            music_structure={"beats": [5.0, 10.0, 15.0, 50.0]},
            timeline_duration_sec=20.0,
        )

        self.assertEqual(plan["segments"][0]["beat_grid"], [5.0, 10.0])
        self.assertEqual(plan["segments"][1]["beat_grid"], [10.0, 15.0])

    def test_build_timeline_build_has_exact_clip_timing_and_trace(self):
        render_plan = [{
            "segment": 1,
            "source": "materials/a.mp4",
            "extract_start": 10.0,
            "extract_dur": 2.5,
            "slot_index": 0,
            "slot_dur": 3.0,
            "keep_audio": True,
            "text": {"label": "開場"},
        }]
        timeline = ea.build_timeline_build(render_plan, contract_hash="sha256:abc")
        clip = timeline["clips"][0]
        self.assertEqual(timeline["timeline_build_version"], 1)
        self.assertEqual(clip["source_path"], "materials/a.mp4")
        self.assertEqual(clip["start_sec"], 10.0)
        self.assertEqual(clip["end_sec"], 12.5)
        self.assertEqual(clip["target_duration_sec"], 3.0)
        self.assertEqual(clip["audio_policy"], "duck")
        self.assertEqual(clip["trace"]["segment_contract_segment"], 1)

    def test_creative_exception_survives_assembly_and_timeline_artifacts(self):
        exception = {
            "rule_bent": "hold_discipline",
            "reason": "Hold for the reveal.",
            "risk": "The shot may feel slow.",
            "requires_review": True,
        }
        plan = ea.build_assembly_plan({
            "segments": [{"segment": 1, "creative_exception": exception}]
        })
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "materials/a.mp4",
            "extract_dur": 3.0,
            "creative_exception": exception,
        }])

        self.assertEqual(plan["segments"][0]["creative_exception"], exception)
        self.assertEqual(timeline["clips"][0]["creative_exception"], exception)

    def test_build_timeline_snaps_start_to_scene_cut(self):
        render_plan = [{
            "segment": 1,
            "source": "materials/a.mp4",
            "extract_start": 10.0,
            "extract_dur": 3.0,
            "slot_index": 0,
            "slot_dur": 3.0,
        }]
        timeline = ea.build_timeline_build(
            render_plan,
            contract_hash="sha256:abc",
            scene_cuts_by_source={"materials/a.mp4": [11.0]},
            scene_cut_tolerance_sec=0.5,
        )
        clip = timeline["clips"][0]
        self.assertEqual(clip["start_sec"], 11.0)
        self.assertEqual(clip["end_sec"], 14.0)
        self.assertTrue(clip["adjusted"])
        self.assertEqual(clip["adjustment_reason"], "snapped_to_scene_cut")

    def test_motion_energy_local_maxima_filters_weak_and_adjacent_peaks(self):
        samples = [
            (0.0, 1.0),
            (0.25, 9.0),
            (0.5, 2.0),
            (0.75, 8.0),
            (1.0, 1.0),
            (1.25, 3.0),
        ]

        peaks = ea.local_motion_peaks(samples, min_energy=5.0, min_gap_sec=0.75)

        self.assertEqual(peaks, [0.25])

    def test_scene_cut_has_priority_over_motion_peak(self):
        snapped = ea.snap_to_edit_point(
            10.0,
            3.0,
            scene_cuts=[11.0],
            motion_peaks=[10.8],
            tolerance=0.5,
        )

        self.assertEqual(snapped, (11.0, 14.0, True, "snapped_to_scene_cut"))

    def test_render_plan_snaps_to_motion_peak_before_render(self):
        plan = [
            {
                "segment": 1,
                "source": "materials/opening.mp4",
                "extract_start": 0.0,
                "extract_dur": 3.0,
            },
            {
                "segment": 2,
                "source": "materials/a.mp4",
                "extract_start": 10.0,
                "extract_dur": 3.0,
            },
        ]

        snapped = ea.snap_render_plan_to_motion(
            plan,
            motion_peak_detector=lambda _source: [10.25, 11.0],
            source_duration_probe=lambda _source: 20.0,
            tolerance=0.5,
        )

        self.assertNotIn("adjustment_reason", snapped[0])
        self.assertEqual(snapped[1]["original_extract_start"], 10.0)
        self.assertEqual(snapped[1]["extract_start"], 11.0)
        self.assertEqual(snapped[1]["adjustment_reason"], "snapped_to_motion_peak")
        self.assertEqual(plan[1]["extract_start"], 10.0)

    def test_render_plan_does_not_move_keep_audio_or_preplanned_window(self):
        plan = [
            {"source": "talk.mp4", "extract_start": 2.0, "extract_dur": 5.0,
             "keep_audio": True, "adjustment_reason": "speech_boundary"},
            {"source": "action.mp4", "extract_start": 4.0, "extract_dur": 3.0,
             "adjustment_reason": "motion_phase"},
        ]
        snapped = ea.snap_render_plan_to_motion(
            plan,
            motion_peak_detector=lambda _source: [5.0],
            source_duration_probe=lambda _source: 20.0,
        )
        self.assertEqual([item["extract_start"] for item in snapped], [2.0, 4.0])
        self.assertEqual(snapped[0]["adjustment_reason"], "speech_boundary")
        self.assertEqual(snapped[1]["adjustment_reason"], "motion_phase")

    def test_render_plan_rejects_motion_snap_that_would_overflow_source(self):
        plan = [
            {"source": "opening.mp4", "extract_start": 0.0, "extract_dur": 2.0},
            {"source": "short.mp4", "extract_start": 5.0, "extract_dur": 3.0},
        ]

        snapped = ea.snap_render_plan_to_motion(
            plan,
            motion_peak_detector=lambda _source: [6.5],
            source_duration_probe=lambda _source: 8.0,
            tolerance=0.5,
        )

        self.assertEqual(snapped[1]["extract_start"], 5.0)
        self.assertNotIn("adjustment_reason", snapped[1])

    def test_render_plan_rejects_motion_snap_that_would_overlap_another_window(self):
        plan = [
            {"source": "a.mp4", "extract_start": 0.0, "extract_dur": 3.0},
            {"source": "a.mp4", "extract_start": 3.0, "extract_dur": 3.0},
            {"source": "a.mp4", "extract_start": 6.0, "extract_dur": 3.0},
        ]

        snapped = ea.snap_render_plan_to_motion(
            plan,
            motion_peak_detector=lambda _source: [4.8, 6.8],
            source_duration_probe=lambda _source: 12.0,
            tolerance=0.5,
        )

        self.assertEqual([clip["extract_start"] for clip in snapped], [0.0, 3.0, 6.8])
        self.assertLessEqual(
            snapped[1]["extract_start"] + snapped[1]["extract_dur"],
            snapped[2]["extract_start"],
        )

    def test_build_timeline_preserves_pre_render_motion_snap_trace(self):
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "materials/a.mp4",
            "original_extract_start": 10.0,
            "extract_start": 11.0,
            "extract_dur": 3.0,
            "adjustment_reason": "snapped_to_motion_peak",
        }])

        clip = timeline["clips"][0]
        self.assertEqual(clip["original_start_sec"], 10.0)
        self.assertEqual(clip["start_sec"], 11.0)
        self.assertTrue(clip["adjusted"])
        self.assertEqual(clip["adjustment_reason"], "snapped_to_motion_peak")

    def test_build_timeline_preserves_m3_verify_evidence(self):
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "materials/action.mp4",
            "extract_dur": 2.0,
            "scene_id": "action:0",
            "beat_alignment": "action",
            "keep_audio": False,
            "motion_phase": {"rise": 1.0, "peak": 2.0, "settle": 3.0},
            "adjustment_reason": "motion_phase",
        }])
        clip = timeline["clips"][0]
        self.assertEqual(clip["scene_id"], "action:0")
        self.assertEqual(clip["beat_alignment"], "action")
        self.assertEqual(clip["motion_phase"]["peak"], 2.0)
        self.assertFalse(clip["keep_audio"])

    def test_build_timeline_carries_hold_reason(self):
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "materials/group-photo.mp4",
            "extract_start": 0.0,
            "extract_dur": 9.0,
            "hold_reason": "group_photo",
        }])

        self.assertEqual(timeline["clips"][0]["hold_reason"], "group_photo")

    def test_build_timeline_carries_crop_center(self):
        render_plan = [{
            "segment": 1,
            "source": "materials/a.mp4",
            "extract_start": 0.0,
            "extract_dur": 2.0,
            "slot_index": 0,
            "crop_center": {"x": 512, "y": 300, "source": "vlm_subject"},
        }]
        timeline = ea.build_timeline_build(render_plan)
        self.assertEqual(timeline["clips"][0]["crop"]["center_x"], 512)
        self.assertEqual(timeline["clips"][0]["crop"]["center_y"], 300)
        self.assertEqual(timeline["clips"][0]["crop"]["source"], "vlm_subject")

    def test_build_timeline_carries_photo_variant_trace(self):
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "photo.jpg",
            "extract_start": 0,
            "extract_dur": 2,
            "slot_index": 2,
            "is_photo": True,
            "photo_variant": 3,
            "still_treatment": {"mode": "detail_push", "reason": "photo_multi_shot"},
        }])
        clip = timeline["clips"][0]
        self.assertEqual(clip["photo_variant"], 3)
        self.assertEqual(clip["still_treatment"]["mode"], "detail_push")

    def test_build_timeline_carries_attention_budget_trace(self):
        budget = {"owner": "music", "shot_sec": [1.5, 4.0], "reason": "music-led"}
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "a.mp4",
            "extract_start": 0,
            "extract_dur": 2.5,
            "slot_index": 0,
            "attention_budget": budget,
        }])

        self.assertEqual(timeline["clips"][0]["attention_budget"], budget)

    def test_build_timeline_carries_presentation_feel_trace(self):
        timeline = ea.build_timeline_build([{
            "segment": 1,
            "source": "a.mp4",
            "extract_start": 0,
            "extract_dur": 2.5,
            "slot_index": 0,
            "composition_layers": 3,
            "text_area_ratio": 0.18,
            "effect_overlays": ["grain", "light_leak"],
        }])

        clip = timeline["clips"][0]
        self.assertEqual(clip["composition_layers"], 3)
        self.assertEqual(clip["text_area_ratio"], 0.18)
        self.assertEqual(clip["effect_overlays"], ["grain", "light_leak"])

    def test_build_timeline_models_explicit_xfade_as_overlap(self):
        timeline = ea.build_timeline_build([
            {"segment": 1, "source": "a.mp4", "extract_start": 0, "extract_dur": 2, "slot_index": 0},
            {"segment": 2, "source": "b.mp4", "extract_start": 0, "extract_dur": 2, "slot_index": 1,
             "transition": "xfade", "transition_duration": 0.5},
        ])

        self.assertEqual(timeline["clips"][1]["timeline_in_sec"], 1.5)
        self.assertEqual(timeline["clips"][1]["timeline_out_sec"], 3.5)
        self.assertEqual(timeline["clips"][1]["transition_duration_sec"], 0.5)


    def test_build_assembly_plan_compiles_execution_and_transition_plans(self):
        script = {
            "_contract_hash": "sha256:abc",
            "segments": [{
                "segment": 1,
                "_from_contract": 1,
                "visual_desc": "校園晨景",
                "audio_role": "music",
                "label": "開場",
                "pace": "hold",
                "subtitle": "Hello world",
                "raw_audio": {
                    "mode": "voiceover",
                    "source": "tts",
                    "duck_music": True,
                    "mood": "happy"
                },
                "raw_visual_style": {
                    "effects_intensity": "expressive",
                    "allowed_effects_roles": ["emphasis"]
                },
                "raw_text_layer": {
                    "mode": "full_subtitle",
                    "placement": "lower_third",
                    "avoid": ["logo"]
                }
            }]
        }
        plan = ea.build_assembly_plan(script, music_structure={"sections": [{"name": "Intro"}]})
        self.assertIn("execution_plan", plan)
        ep = plan["execution_plan"]
        self.assertEqual(len(ep["narration_tasks"]), 1)
        self.assertEqual(ep["narration_tasks"][0]["text"], "Hello world")
        self.assertEqual(len(ep["subtitle_tasks"]), 1)
        self.assertEqual(ep["subtitle_tasks"][0]["placement"], "lower_third")
        
        seg = plan["segments"][0]
        self.assertIn("execution_plan", seg)
        self.assertEqual(seg["execution_plan"]["narration"]["mode"], "voiceover")
        self.assertEqual(seg["execution_plan"]["subtitles"]["placement"], "lower_third")
        self.assertEqual(seg["execution_plan"]["effects"]["intensity"], "expressive")
        self.assertEqual(seg["attention_budget"]["owner"], "narration")
        self.assertEqual(seg["attention_budget"]["shot_sec"], [3.0, 8.0])

    def test_audio_role_music_is_not_misclassified_as_narration(self):
        script = {"segments": [{
            "segment": 1,
            "visual_desc": "music-led montage",
            "raw_audio": {"role": "music"},
        }]}

        plan = ea.build_assembly_plan(script)

        seg = plan["segments"][0]
        self.assertEqual(seg["execution_plan"]["narration"]["mode"], "none")
        self.assertEqual(seg["attention_budget"]["owner"], "music")
        self.assertEqual(seg["attention_budget"]["shot_sec"], [1.5, 4.0])

    def test_long_photo_narrative_gets_anti_presentation_plan(self):
        script = {"segments": [{
            "segment": 2,
            "visual_desc": "long still explanation",
            "media": "photo",
            "narrative": "A concise explanation",
            "raw_text_layer": {"placement": "center"},
        }]}

        plan = ea.build_assembly_plan(
            script,
            music_structure={"beats": [0.0, 18.0]},
            editing_policy={
                "default_mode": "warm_documentary",
                "max_still_hold_sec_by_mode": {"warm_documentary": 7.0},
            },
        )

        anti = plan["segments"][0]["anti_presentation_plan"]
        self.assertEqual(anti["min_shots"], 3)
        self.assertEqual(
            anti["still_treatment_modes"],
            ["detail_push", "pan_left", "slow_push"],
        )
        self.assertEqual(anti["text_placement"], "lower_third")


if __name__ == "__main__":
    unittest.main()
