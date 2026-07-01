import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from video_pipeline_core.effect_revision import ADAPTER_ROUTE
from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
from video_pipeline_core.visual_technique_plan import (
    apply_visual_technique_review,
    plan_visual_technique,
    technique_to_effect,
)


SAKURA_OPENING = "\u65e5\u5f0f\u6afb\u82b1\u98c4\u9038\u958b\u5834"
ENERGETIC_MV = "\u71b1\u8840 energetic MV \u958b\u5834 with big impact cuts"
WARM_LEGACY_CLOSING = (
    "\u7d50\u5c3e\u8981\u542b\u84c4\u611f\u4eba\uff0c"
    "\u628a\u9019\u6bb5\u65e5\u5b50\u7684\u7cbe\u795e\u50b3\u905e\u5230"
    "\u4e0b\u4e00\u500b\u968e\u6bb5\uff0c\u7528\u5408\u7167\u7576\u80cc\u666f"
    "\u548c\u6eab\u6696\u706b\u5149\u9918\u6eab"
)
NEXT_STAGE = "\u8d70\u5411\u4e0b\u4e00\u500b\u968e\u6bb5"
CARRY_SPIRIT = "\u628a\u9019\u6bb5\u65e5\u5b50\u7684\u7cbe\u795e\uff0c\u5e36\u5230\u66f4\u9060\u7684\u5730\u65b9"


class VisualTechniquePlanTest(unittest.TestCase):
    def test_japanese_sakura_opening_maps_semantics_to_particle_techniques(self):
        plan = plan_visual_technique(
            {
                "request": SAKURA_OPENING,
                "effect_role": "opening_title",
                "duration_sec": 6,
                "material_state": "generated_background_ok",
            }
        )

        self.assertEqual(plan["artifact_role"], "visual_technique_plan")
        self.assertEqual(plan["version"], 1)
        self.assertEqual(plan["style_family"], "japanese_sakura")
        self.assertEqual(plan["effect_role"], "opening_title")
        self.assertIn("remotion_canvas_particles", plan["render_strategy"])
        self.assertIn("remotion_three_particles", plan["render_strategy"])
        self.assertIn("sakura", plan["visual_primitives"])
        self.assertIn("petals", plan["visual_primitives"])
        self.assertIn("drift", plan["motion_primitives"])
        self.assertIn("fall", plan["motion_primitives"])
        self.assertIn("parallax", plan["motion_primitives"])
        self.assertEqual(plan["controls"]["duration_sec"], 6.0)
        for control in ("petal_count", "wind_strength", "fall_speed", "depth_layers", "color_mood"):
            self.assertIn(control, plan["controls"])
        self.assertEqual(plan["followup_questions"], [])
        self.assertEqual(plan["handoff_to"], "remotion_prompt_parameters")

    def test_energetic_mv_maps_to_kinetic_typography_not_sakura(self):
        plan = plan_visual_technique(
            {
                "request": ENERGETIC_MV,
                "effect_role": "opening_title",
                "duration_sec": 4,
            }
        )

        self.assertEqual(plan["style_family"], "energetic_mv")
        self.assertIn("remotion_text_layers", plan["render_strategy"])
        self.assertIn("kinetic_typography", plan["visual_primitives"])
        self.assertIn("flash_bars", plan["visual_primitives"])
        self.assertIn("impact_cuts", plan["motion_primitives"])
        self.assertIn("beat_pulse", plan["motion_primitives"])
        self.assertNotIn("sakura", plan["visual_primitives"])
        self.assertNotIn("petals", plan["visual_primitives"])
        self.assertIn("cut_intensity", plan["controls"])
        self.assertIn("flash_frequency", plan["controls"])
        self.assertEqual(plan["followup_questions"], [])

    def test_chinese_lightning_opening_maps_to_reviewable_electric_family(self):
        plan = plan_visual_technique(
            {
                "request": "\u52d5\u611f\u9583\u96fb\u958b\u5834\uff0c\u8981\u6709\u885d\u64ca\u611f\u4f46\u4e0d\u8981\u50cf\u6050\u6016\u7247",
                "effect_role": "opening_title",
                "duration_sec": 5,
            }
        )

        self.assertEqual(plan["style_family"], "electric_lightning_energy")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("branching_lightning_arcs", plan["visual_primitives"])
        self.assertIn("arc_strike", plan["motion_primitives"])
        self.assertIn("strike_count", plan["controls"])
        self.assertIn("no horror tone", plan["negative_rules"])

    def test_chinese_earthquake_crack_opening_maps_to_impact_family(self):
        plan = plan_visual_technique(
            {
                "request": "\u5730\u9707\u88c2\u52d5\u958b\u5834\uff0c\u50cf\u6311\u6230\u958b\u59cb\u7684\u885d\u64ca\u756b\u9762",
                "effect_role": "opening_title",
                "duration_sec": 4,
            }
        )

        self.assertEqual(plan["style_family"], "earthquake_crack_impact")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("surface_crack_lines", plan["visual_primitives"])
        self.assertIn("impact_shake", plan["motion_primitives"])
        self.assertIn("shake_strength", plan["controls"])
        self.assertIn("no injury implication", plan["negative_rules"])

    def test_chinese_mothers_day_heart_background_maps_to_warm_family(self):
        plan = plan_visual_technique(
            {
                "request": "\u6bcd\u89aa\u7bc0\u611b\u5fc3\u5e03\u666f\uff0c\u6eab\u67d4\u611f\u8b1d\u7684\u958b\u5834",
                "effect_role": "opening_title",
                "duration_sec": 6,
            }
        )

        self.assertEqual(plan["style_family"], "mothers_day_heart_stage")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("soft_heart_bokeh", plan["visual_primitives"])
        self.assertIn("heart_float", plan["motion_primitives"])
        self.assertIn("heart_count", plan["controls"])
        self.assertIn("no harsh red", plan["negative_rules"])

    def test_broad_japanese_cute_style_maps_to_dictionary_not_fixed_sakura_template(self):
        plan = plan_visual_technique(
            {
                "request": "\u65e5\u5f0f\u53ef\u611b\u98a8\u683c\u7684\u6545\u4e8b\u958b\u5834\uff0c\u60f3\u8981\u8f15\u67d4\u3001\u6709\u7d19\u672c\u611f",
                "effect_role": "opening_title",
                "duration_sec": 6,
            }
        )

        self.assertEqual(plan["style_family"], "japanese_soft_storybook")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("storybook_paper_texture", plan["visual_primitives"])
        self.assertIn("soft_character_plate", plan["visual_primitives"])
        self.assertIn("gentle_parallax", plan["motion_primitives"])
        self.assertIn("palette", plan["controls"])
        self.assertNotIn("sakura", plan["visual_primitives"])
        self.assertTrue(plan["requires_human_review"])
        self.assertEqual(plan["semantic_slots"]["tone"], "gentle_cute_storybook")
        self.assertIn("remotion_layered_paper", plan["remotion_capability_plan"]["capabilities"])
        self.assertIn("remotion_text_layers", plan["remotion_capability_plan"]["capabilities"])
        self.assertEqual(plan["remotion_capability_plan"]["timing_model"], "useCurrentFrame_interpolate")
        self.assertIn("layers", plan["remotion_capability_plan"])
        self.assertIn("parameter_schema", plan["remotion_capability_plan"])
        self.assertIn("fallback_policy", plan["remotion_capability_plan"])
        self.assertIn("remotion_layered_paper", plan["remotion_capability_plan"]["parameter_schema"])
        self.assertIn("duration_sec", plan["remotion_capability_plan"]["timing_controls"])

    def test_memory_wall_translates_to_supported_build_spec_not_only_style_label(self):
        plan = plan_visual_technique(
            {
                "request": "\u56de\u61b6\u7167\u7247\u7246\uff0c\u7167\u7247\u4e00\u5f35\u4e00\u5f35\u6162\u6162\u51fa\u73fe\uff0c\u6eab\u99a8\u60c5\u7dd2",
                "effect_role": "transition",
                "duration_sec": 8,
            }
        )

        self.assertEqual(plan["style_family"], "memory_photo_wall_warm")
        self.assertEqual(plan["semantic_slots"]["story_function"], "memory_transition_or_emotional_recap")
        self.assertEqual(plan["semantic_slots"]["pacing"], "slow")
        self.assertEqual(plan["semantic_slots"]["reveal_mode"], "one_by_one")
        self.assertIn("remotion_photo_layers", plan["remotion_capability_plan"]["capabilities"])
        self.assertIn("sequence_layers", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("material_refs", plan["remotion_capability_plan"]["parameter_schema"])
        self.assertEqual(plan["remotion_capability_plan"]["layers"][0]["role"], "image_layout")
        self.assertEqual(plan["remotion_capability_plan"]["layers"][0]["source"], "reviewed_material_refs")
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "MemoryPhotoWall")
        self.assertEqual(spec["duration_sec"], 8.0)
        self.assertEqual(spec["reveal_mode"], "one_by_one")
        self.assertEqual(spec["camera_motion"], "slow_push_in")

    def test_story_to_mv_transition_translates_to_supported_build_spec(self):
        plan = plan_visual_technique(
            {
                "request": "\u524d\u534a\u6bb5\u6545\u4e8b\u8f49\u5230\u5f8c\u534a\u6bb5 MV \u8499\u592a\u5947\uff0c\u8981\u52a0\u901f\u6709\u885d\u64ca",
                "effect_role": "transition",
                "duration_sec": 4,
            }
        )

        self.assertEqual(plan["style_family"], "story_to_mv_transition")
        self.assertEqual(plan["semantic_slots"]["story_function"], "story_to_montage_energy_shift")
        self.assertEqual(plan["semantic_slots"]["pacing_shift"], "slow_to_fast")
        self.assertIn("transition_series", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("remotion_timeline_cuts", plan["remotion_capability_plan"]["capabilities"])
        self.assertIn("impact_moment_sec", plan["remotion_capability_plan"]["timing_controls"])
        self.assertTrue(any(layer["role"] == "transition_overlay" for layer in plan["remotion_capability_plan"]["layers"]))
        self.assertIn("TransitionSeries.Transition", plan["remotion_capability_plan"]["remotion_api_refs"])
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "StoryToMVTransition")
        self.assertEqual(spec["section_from"], "story")
        self.assertEqual(spec["section_to"], "montage")
        self.assertIn("thumbnail_acceleration", spec["motion_grammar"])

    def test_terminal_data_reveal_keeps_cyber_semantics_instead_of_lightning_fallback(self):
        plan = plan_visual_technique(
            {
                "request": (
                    "\u9ed1\u5ba2\u8cc7\u6599\u6d41\u63ed\u793a\u958b\u5834\uff0c"
                    "\u50cf\u7d42\u7aef\u6a5f\u8cc7\u6599\u5feb\u901f\u6d41\u52d5\uff0c"
                    "\u6700\u5f8c\u7d44\u6210\u4e3b\u6a19\u984c\uff0c\u79d1\u6280\u7dca\u5f35\u4f46\u6587\u5b57\u6e05\u695a"
                ),
                "effect_role": "opening_title",
                "duration_sec": 5,
            }
        )

        self.assertEqual(plan["style_family"], "terminal_data_reveal")
        self.assertEqual(plan["semantic_slots"]["story_function"], "cyber_information_reveal")
        self.assertEqual(plan["semantic_slots"]["material_relation"], "abstract_generated_overlay")
        self.assertIn("glyph_stream_layer", plan["visual_primitives"])
        self.assertIn("title_assembly", plan["motion_primitives"])
        self.assertIn("scanline_layer", plan["remotion_capability_plan"]["primitives"])
        self.assertTrue(any(layer["role"] == "data_stream_layer" for layer in plan["remotion_capability_plan"]["layers"]))
        self.assertIn("glyph_speed", plan["remotion_capability_plan"]["parameter_schema"])
        self.assertEqual(plan["controls"]["readability_guard"], "title_clear_after_reveal")
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "text" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "glyph_stream" for layer in spec["layers"]))
        self.assertNotEqual(plan["style_family"], "electric_lightning_energy")

    def test_vintage_film_burn_transition_keeps_burn_through_semantics(self):
        plan = plan_visual_technique(
            {
                "request": (
                    "\u5fa9\u53e4\u81a0\u7247\u71d2\u707c\u8f49\u5834\uff0c"
                    "\u50cf\u8001\u96fb\u5f71\u81a0\u5377\u908a\u7de3\u88ab\u5149\u71d2\u958b\uff0c"
                    "\u5f9e\u4e0a\u4e00\u6bb5\u56de\u61b6\u5207\u5230\u4e0b\u4e00\u6bb5\u771f\u76f8\uff0c"
                    "\u61f7\u820a\u3001\u4e0d\u5b89\u4f46\u4e0d\u6050\u6016"
                ),
                "effect_role": "transition",
                "duration_sec": 3,
            }
        )

        self.assertEqual(plan["style_family"], "vintage_film_burn_transition")
        self.assertEqual(plan["semantic_slots"]["story_function"], "memory_to_truth_transition")
        self.assertIn("burn_mask_edge", plan["visual_primitives"])
        self.assertIn("burn_through_wipe", plan["motion_primitives"])
        self.assertIn("mask_wipe_layer", plan["remotion_capability_plan"]["primitives"])
        self.assertTrue(any(layer["role"] == "burn_mask_wipe" for layer in plan["remotion_capability_plan"]["layers"]))
        self.assertIn("burn_edge_width", plan["remotion_capability_plan"]["parameter_schema"])
        self.assertIn("transition_duration_sec", plan["remotion_capability_plan"]["timing_controls"])
        self.assertEqual(plan["controls"]["horror_guard"], "no_horror_no_gore")
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "mask_wipe" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "film_grain" for layer in spec["layers"]))
        self.assertNotEqual(plan["style_family"], "warm_documentary")

    def test_ink_spread_reveal_translates_to_mask_and_fluid_layers(self):
        plan = plan_visual_technique(
            {
                "request": "ink spread reveal opening, black ink blooms across rice paper and reveals the title",
                "effect_role": "opening_title",
                "duration_sec": 5,
            }
        )

        self.assertEqual(plan["style_family"], "ink_spread_reveal")
        self.assertEqual(plan["semantic_slots"]["story_function"], "organic_title_reveal")
        self.assertIn("ink_bloom_mask", plan["visual_primitives"])
        self.assertIn("paper_fiber_texture", plan["visual_primitives"])
        self.assertIn("fluid_spread", plan["motion_primitives"])
        self.assertIn("mask_reveal_layer", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("noise_displacement_layer", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("ink_spread_radius", plan["remotion_capability_plan"]["parameter_schema"])
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "mask_reveal" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "texture_overlay" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "text" for layer in spec["layers"]))
        self.assertFalse(any(layer["type"] == "film_grain" for layer in spec["layers"]))

    def test_prism_glass_refraction_translates_to_refraction_layers(self):
        plan = plan_visual_technique(
            {
                "request": "prism glass refraction transition, crystalline split colors bend the footage into the next chapter",
                "effect_role": "transition",
                "duration_sec": 4,
            }
        )

        self.assertEqual(plan["style_family"], "prism_glass_refraction")
        self.assertEqual(plan["semantic_slots"]["story_function"], "crystalline_transition")
        self.assertIn("glass_prism_planes", plan["visual_primitives"])
        self.assertIn("rgb_spectral_split", plan["visual_primitives"])
        self.assertIn("refraction_sweep", plan["motion_primitives"])
        self.assertIn("refraction_layer", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("clip_path_planes", plan["remotion_capability_plan"]["primitives"])
        self.assertIn("chromatic_aberration_px", plan["remotion_capability_plan"]["parameter_schema"])
        spec = plan["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "refraction" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "chromatic_split" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "mask_wipe" for layer in spec["layers"]))

    def test_supported_build_spec_is_preserved_into_prompt_parameters(self):
        plan = plan_visual_technique(
            {
                "request": "\u56de\u61b6\u7167\u7247\u7246\uff0c\u7167\u7247\u4e00\u5f35\u4e00\u5f35\u6162\u6162\u51fa\u73fe",
                "effect_role": "transition",
                "duration_sec": 8,
                "confirmed_style_family": True,
            }
        )
        effect = technique_to_effect(plan, effect_id="fx_memory_wall_01")

        self.assertEqual(
            effect["prompt_parameters"]["effect_build_spec"]["component"],
            "MemoryPhotoWall",
        )
        self.assertEqual(
            effect["prompt_parameters"]["visual_technique_plan"]["remotion_capability_plan"]["engine"],
            "remotion",
        )

    def test_vague_or_unsupported_request_requires_followup_not_fake_completion(self):
        plan = plan_visual_technique({"request": "make it nice"})

        self.assertEqual(plan["artifact_role"], "visual_technique_plan")
        self.assertEqual(plan["style_family"], "needs_clarification")
        self.assertEqual(plan["handoff_to"], "ask_followup")
        self.assertEqual(plan["render_strategy"], [])
        self.assertEqual(plan["visual_primitives"], [])
        self.assertEqual(plan["motion_primitives"], [])
        self.assertGreaterEqual(len(plan["followup_questions"]), 2)
        self.assertIn("visual style", " ".join(plan["followup_questions"]).lower())
        self.assertIn("effect role", " ".join(plan["followup_questions"]).lower())

    def test_chinese_wedding_photo_wall_maps_to_reviewable_memory_family(self):
        plan = plan_visual_technique(
            {
                "request": "婚禮照片牆溫馨轉場，照片一張一張慢慢出現",
                "effect_role": "transition",
                "duration_sec": 8,
            }
        )

        self.assertEqual(plan["style_family"], "memory_photo_wall_warm")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("photo_grid", plan["visual_primitives"])
        self.assertIn("one_by_one_reveal", plan["motion_primitives"])
        self.assertIn("photo_count", plan["controls"])
        self.assertTrue(any("photo" in q.lower() or "照片" in q for q in plan["followup_questions"]))

    def test_lower_third_maps_to_simple_label_family_not_generic_style_question(self):
        plan = plan_visual_technique(
            {
                "request": "幫主任致詞加一個下標姓名職稱，不要太花",
                "effect_role": "lower_third",
                "duration_sec": 5,
            }
        )

        self.assertEqual(plan["style_family"], "clean_lower_third_label")
        self.assertIn("name_title_plate", plan["visual_primitives"])
        self.assertIn("safe_area", plan["controls"])
        self.assertNotIn("What visual style should drive the technique plan?", plan["followup_questions"])

    def test_extreme_metaphor_creates_candidate_primitives_and_specific_questions(self):
        plan = plan_visual_technique(
            {
                "request": "時間像玻璃裂開然後倒轉，當作段落轉場",
                "effect_role": "transition",
                "duration_sec": 7,
            }
        )

        self.assertEqual(plan["style_family"], "time_fracture_reverse")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertIn("glass_crack", plan["visual_primitives"])
        self.assertIn("reverse_motion", plan["motion_primitives"])
        self.assertIn("crack_timing", plan["controls"])
        self.assertTrue(any("before" in q.lower() or "after" in q.lower() or "前後" in q for q in plan["followup_questions"]))

    def test_lightning_request_proposes_reviewable_options_before_worker_handoff(self):
        plan = plan_visual_technique(
            {
                "request": "electric lightning opening with strong impact",
                "effect_role": "opening_title",
                "duration_sec": 6,
            }
        )

        self.assertEqual(plan["style_family"], "electric_lightning_energy")
        self.assertEqual(plan["parameter_status"], "candidate_parameters")
        self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
        self.assertTrue(plan["requires_human_review"])
        self.assertIn("branching_lightning_arcs", plan["visual_primitives"])
        self.assertIn("arc_strike", plan["motion_primitives"])
        self.assertIn("strike_count", plan["controls"])
        self.assertEqual(
            [item["option_id"] for item in plan["candidate_options"]],
            ["restrained", "balanced", "expressive"],
        )
        with self.assertRaises(ValueError):
            technique_to_effect(plan, effect_id="fx_lightning_opening_01")

    def test_confirmed_lightning_candidate_can_handoff_as_visible_parameters(self):
        plan = plan_visual_technique(
            {
                "request": "electric lightning opening with strong impact",
                "effect_role": "opening_title",
                "duration_sec": 6,
                "confirmed_style_family": True,
            }
        )

        self.assertEqual(plan["style_family"], "electric_lightning_energy")
        self.assertEqual(plan["handoff_to"], "remotion_prompt_parameters")
        self.assertEqual(plan["followup_questions"], [])
        self.assertEqual(plan["parameter_status"], "reviewed_candidate_parameters")
        self.assertEqual(plan["review_decision"]["reviewer"], "cli_confirmed")
        self.assertEqual(plan["selected_candidate_option"]["option_id"], "balanced")
        effect = technique_to_effect(
            plan,
            effect_id="fx_lightning_opening_01",
            display_text="Launch",
        )
        params = effect["prompt_parameters"]
        self.assertEqual(params["parameter_status"], "reviewed_candidate_parameters")
        self.assertTrue(params["requires_human_review"])
        self.assertEqual(params["template_policy"], "templates_are_carriers_not_creative_locks")
        self.assertEqual(
            params["visual_technique_plan"]["candidate_options"][1]["option_id"],
            "balanced",
        )
        spec = params["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "particle_overlay" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "light_overlay" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "camera_motion" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "text" for layer in spec["layers"]))

    def test_confirmed_earthquake_candidate_can_handoff_as_generic_crack_layers(self):
        plan = plan_visual_technique(
            {
                "request": "earthquake crack impact opening, concrete lines expand with dust and shake",
                "effect_role": "opening_title",
                "duration_sec": 4,
                "confirmed_style_family": True,
            }
        )

        self.assertEqual(plan["style_family"], "earthquake_crack_impact")
        self.assertEqual(plan["handoff_to"], "remotion_prompt_parameters")
        effect = technique_to_effect(
            plan,
            effect_id="fx_crack_opening_01",
            display_text="Impact",
        )
        spec = effect["prompt_parameters"]["effect_build_spec"]
        self.assertEqual(spec["component"], "GenericRemotionEffect")
        self.assertTrue(any(layer["type"] == "crack_lines" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "particle_overlay" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "camera_motion" for layer in spec["layers"]))
        self.assertTrue(any(layer["type"] == "text" for layer in spec["layers"]))

    def test_review_apply_promotes_candidate_with_selected_option_and_overrides(self):
        plan = plan_visual_technique(
            {
                "request": "electric lightning opening with strong impact",
                "effect_role": "opening_title",
                "duration_sec": 6,
            }
        )
        reviewed = apply_visual_technique_review(
            plan,
            {
                "artifact_role": "visual_technique_review",
                "decision": "revise",
                "reviewer": "user",
                "selected_option": "restrained",
                "reason": "keep the lightning but avoid aggressive strobe",
                "control_overrides": {
                    "flash_intensity": "medium",
                    "strike_count": 2,
                },
                "remove_motion_primitives": ["micro_jitter"],
                "add_negative_rules": ["avoid nervous camera shake"],
            },
        )

        self.assertEqual(reviewed["handoff_to"], "remotion_prompt_parameters")
        self.assertEqual(reviewed["parameter_status"], "revised_candidate_parameters")
        self.assertEqual(reviewed["selected_candidate_option"]["option_id"], "restrained")
        self.assertEqual(reviewed["controls"]["flash_intensity"], "medium")
        self.assertEqual(reviewed["controls"]["strike_count"], 2)
        self.assertNotIn("micro_jitter", reviewed["motion_primitives"])
        self.assertIn("avoid nervous camera shake", reviewed["negative_rules"])
        effect = technique_to_effect(reviewed, effect_id="fx_lightning_reviewed_01")
        self.assertEqual(effect["prompt_parameters"]["visual_technique_plan"]["review_decision"]["reviewer"], "user")

    def test_cli_writes_review_candidate_by_default_and_confirmed_handoff_when_requested(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "visual_technique_plan.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/visual_technique_plan.py",
                    "--request",
                    "electric lightning opening with strong impact",
                    "--effect-role",
                    "opening_title",
                    "--duration-sec",
                    "6",
                    "--out",
                    str(out),
                    "--json",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            plan = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(plan["handoff_to"], "review_candidate_parameters")
            self.assertEqual(plan["candidate_options"][0]["option_id"], "restrained")

            confirmed = Path(temp) / "visual_technique_plan.confirmed.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/visual_technique_plan.py",
                    "--request",
                    "electric lightning opening with strong impact",
                    "--effect-role",
                    "opening_title",
                    "--duration-sec",
                    "6",
                    "--confirmed",
                    "--out",
                    str(confirmed),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            confirmed_plan = json.loads(confirmed.read_text(encoding="utf-8"))
            self.assertEqual(confirmed_plan["handoff_to"], "remotion_prompt_parameters")
            self.assertEqual(confirmed_plan["followup_questions"], [])
            self.assertEqual(confirmed_plan["parameter_status"], "reviewed_candidate_parameters")
            self.assertEqual(confirmed_plan["review_decision"]["reviewer"], "cli_confirmed")
            self.assertEqual(confirmed_plan["selected_candidate_option"]["option_id"], "balanced")

    def test_video_tools_command_writes_review_candidate_plan(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "visual_technique_plan.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "visual-technique-plan",
                    "--request",
                    "electric lightning opening with strong impact",
                    "--effect-role",
                    "opening_title",
                    "--duration-sec",
                    "6",
                    "--json",
                    "--out",
                    str(out),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["handoff_to"], "review_candidate_parameters")
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["style_family"], "electric_lightning_energy")
            self.assertEqual(saved["candidate_options"][2]["option_id"], "expressive")

    def test_video_tools_review_apply_command_writes_confirmed_plan(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp) / "visual_technique_plan.json"
            review = Path(temp) / "visual_technique_review.json"
            out = Path(temp) / "visual_technique_plan.confirmed.json"
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "visual-technique-plan",
                    "--request",
                    "electric lightning opening with strong impact",
                    "--effect-role",
                    "opening_title",
                    "--duration-sec",
                    "6",
                    "--out",
                    str(plan),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            review.write_text(json.dumps({
                "artifact_role": "visual_technique_review",
                "decision": "accept",
                "reviewer": "user",
                "selected_option": "balanced",
                "reason": "balanced is close enough for preview",
            }), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "visual-technique-review-apply",
                    "--plan",
                    str(plan),
                    "--review",
                    str(review),
                    "--out",
                    str(out),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["handoff_to"], "remotion_prompt_parameters")
            self.assertEqual(saved["parameter_status"], "reviewed_candidate_parameters")
            self.assertEqual(saved["selected_candidate_option"]["option_id"], "balanced")

    def test_warm_legacy_fire_closing_keeps_original_contract_and_adds_worker_controls(self):
        plan = plan_visual_technique(
            {
                "request": WARM_LEGACY_CLOSING,
                "effect_role": "closing_title",
                "duration_sec": 8,
                "material_state": "group_photo_available",
            }
        )

        self.assertEqual(plan["style_family"], "warm_legacy_fire")
        self.assertEqual(plan["story_function"], "closing_emotional_legacy")
        self.assertEqual(plan["placement"], "ending")
        self.assertEqual(plan["tone"], "moving_warm")
        self.assertEqual(plan["display_text"], NEXT_STAGE)
        self.assertEqual(plan["subtitle_text"], CARRY_SPIRIT)
        self.assertIn("soft_ember_particles", plan["visual_primitives"])
        self.assertIn("dimmed_group_photo_background", plan["visual_primitives"])
        self.assertIn("very_slow_push_in", plan["motion_primitives"])
        self.assertEqual(plan["material_use"]["background_source"], "group_photo")
        self.assertEqual(plan["material_use"]["background_treatment"], "soft_dimmed_memory_plate")
        self.assertTrue(plan["material_use"]["preserve_people_visibility"])
        self.assertEqual(plan["controls"]["duration_sec"], 8.0)
        self.assertEqual(plan["controls"]["ember_density"], "low")
        self.assertEqual(plan["controls"]["photo_dim_strength"], "medium")
        self.assertEqual(plan["controls"]["subtitle_readability"], "high")
        self.assertIn("no aggressive flames", plan["negative_rules"])
        self.assertIn("do not obscure faces in group photo", plan["negative_rules"])

    def test_technique_plan_converts_to_effect_intent_and_prompt_pack_controls(self):
        plan = plan_visual_technique(
            {
                "request": SAKURA_OPENING,
                "effect_role": "opening_title",
                "duration_sec": 6,
            }
        )
        effect = technique_to_effect(
            plan,
            effect_id="fx_sakura_opening_01",
            display_text="Spring Memory",
        )
        effect_intent_plan = {
            "artifact_role": "effect_intent_plan",
            "version": 1,
            "effects": [effect],
        }
        request = {
            "artifact_role": "effect_revision_request",
            "version": 1,
            "status": "pending",
            "summary": {"request_count": 1},
            "requests": [
                {
                    "request_id": "fxrev_sakura_opening_01",
                    "effect_id": "fx_sakura_opening_01_adapter",
                    "source_effect_id": "fx_sakura_opening_01",
                    "segment": "fx_sakura_opening_01",
                    "operation": "external_effect",
                    "route": ADAPTER_ROUTE,
                    "reason": "probe semantic technique handoff",
                    "status": "pending",
                }
            ],
        }
        timeline = {
            "segments": [
                {
                    "segment_id": "fx_sakura_opening_01",
                    "start_sec": 0,
                    "duration_sec": 6,
                    "effect_ids": ["fx_sakura_opening_01"],
                }
            ]
        }

        pack = build_remotion_prompt_pack(
            request,
            effect_intent_plan,
            timeline=timeline,
            output_dir="remotion_effects",
        )

        self.assertEqual(pack["artifact_role"], "remotion_prompt_pack")
        self.assertEqual(len(pack["jobs"]), 1)
        job = pack["jobs"][0]
        self.assertEqual(job["route"], ADAPTER_ROUTE)
        self.assertIsNone(job["props"]["template_id"])
        prompt_parameters = job["props"]["prompt_parameters"]
        self.assertEqual(prompt_parameters["effect_build_spec"]["component"], "GenericRemotionEffect")
        technique_plan = prompt_parameters["visual_technique_plan"]
        self.assertEqual(technique_plan["style_family"], "japanese_sakura")
        self.assertIn("drift", prompt_parameters["motion_grammar"])
        self.assertIn("fall", prompt_parameters["motion_grammar"])
        self.assertIn("parallax", prompt_parameters["motion_grammar"])


if __name__ == "__main__":
    unittest.main()
