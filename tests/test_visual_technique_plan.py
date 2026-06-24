import unittest

from video_pipeline_core.effect_revision import ADAPTER_ROUTE
from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
from video_pipeline_core.visual_technique_plan import plan_visual_technique, technique_to_effect


class VisualTechniquePlanTest(unittest.TestCase):
    def test_japanese_sakura_opening_maps_semantics_to_particle_techniques(self):
        plan = plan_visual_technique(
            {
                "request": "日式櫻花飄逸開場",
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
                "request": "熱血 energetic MV 開場 with big impact cuts",
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

    def test_technique_plan_converts_to_effect_intent_and_prompt_pack_controls(self):
        plan = plan_visual_technique(
            {
                "request": "日式櫻花飄逸開場",
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
