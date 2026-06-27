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
        self.assertEqual(job["props"]["template_id"], "training_opening_title")
        prompt_parameters = job["props"]["prompt_parameters"]
        technique_plan = prompt_parameters["visual_technique_plan"]
        self.assertEqual(technique_plan["style_family"], "japanese_sakura")
        self.assertIn("drift", prompt_parameters["motion_grammar"])
        self.assertIn("fall", prompt_parameters["motion_grammar"])
        self.assertIn("parallax", prompt_parameters["motion_grammar"])


if __name__ == "__main__":
    unittest.main()
