import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace


class EffectDesignConceptTest(unittest.TestCase):
    def test_fuzzy_training_recap_request_builds_reviewable_design_chain(self):
        from video_pipeline_core.effect_design_concept import build_effect_design_concept_chain

        chain = build_effect_design_concept_chain(
            request="做一段有溫度的訓練回顧開場，像回憶慢慢湧上來，不要太像簡報，也不要太花，讓人想繼續看。",
            effect_role="opening_title",
            duration_sec=4.0,
        )

        self.assertEqual(chain["design_brief"]["artifact_role"], "effect_design_brief")
        self.assertIn("warmth", chain["design_brief"]["emotional_core"])
        self.assertIn("avoid_presentation_deck", chain["design_brief"]["negative_direction"])
        self.assertEqual(chain["concept_options"]["artifact_role"], "effect_concept_options")
        self.assertGreaterEqual(len(chain["concept_options"]["concepts"]), 3)
        concept_ids = {item["concept_id"] for item in chain["concept_options"]["concepts"]}
        self.assertIn("quiet_memory_wall", concept_ids)
        self.assertIn("film_table_recall", concept_ids)
        self.assertIn("warm_archive_opening", concept_ids)
        self.assertEqual(chain["concept_selection"]["artifact_role"], "effect_concept_selection")
        self.assertEqual(chain["concept_selection"]["selected_concept_id"], "quiet_memory_wall")
        self.assertEqual(chain["concept_selection"]["decision"], "selected")
        self.assertGreaterEqual(chain["concept_selection"]["score"], 8)

    def test_technology_logo_fly_in_does_not_fall_back_to_memory_wall(self):
        from video_pipeline_core.effect_design_concept import build_effect_design_concept_chain

        chain = build_effect_design_concept_chain(
            request="做一個科技感很強、logo 飛進來的開場，但不要太廉價",
            effect_role="opening_title",
            duration_sec=15.0,
        )

        self.assertIn("technology", chain["design_brief"]["semantic_tokens"])
        self.assertIn("logo_focus", chain["design_brief"]["semantic_tokens"])
        self.assertIn("fast_logo_motion", chain["design_brief"]["semantic_tokens"])
        concept_ids = {item["concept_id"] for item in chain["concept_options"]["concepts"]}
        self.assertIn("tech_logo_fly_in", concept_ids)
        self.assertEqual(chain["concept_selection"]["selected_concept_id"], "tech_logo_fly_in")
        self.assertIn("technology", chain["concept_selection"]["reason"])
        self.assertIn("memory/photo-wall metaphors are intentionally avoided", chain["concept_selection"]["reason"])
        selected = chain["concept_selection"]["selected_concept"]
        self.assertEqual(
            selected["prompt_parameters"]["effect_build_spec"]["component"],
            "GenericRemotionEffect",
        )
        layer_types = {
            layer["type"]
            for layer in selected["prompt_parameters"]["effect_build_spec"]["layers"]
        }
        self.assertIn("logo_3d_motion", layer_types)
        self.assertNotEqual(chain["concept_selection"]["selected_concept_id"], "quiet_memory_wall")

    def test_non_memory_effect_families_do_not_default_to_memory_wall(self):
        from video_pipeline_core.effect_design_concept import build_effect_design_concept_chain

        cases = [
            ("日式櫻花飄落的童話段落轉場，柔和夢幻", "transition", "symbolic_motion_effect"),
            ("閃電劈下來的震撼開場，但不要廉價", "opening_title", "symbolic_motion_effect"),
            ("母親節活動開場，溫暖愛心布景", "opening_title", "symbolic_motion_effect"),
            ("講者下標，乾淨、中文清楚、不要花", "lower_third", "clean_information_overlay"),
            ("故事切到熱血 MV，速度感很強的轉場", "transition", "kinetic_mv_transition"),
            ("產品發表開場，高級黑金質感，物件慢慢亮出來", "opening_title", "premium_product_reveal"),
        ]

        for request, role, expected in cases:
            with self.subTest(request=request):
                chain = build_effect_design_concept_chain(
                    request=request,
                    effect_role=role,
                    duration_sec=8.0,
                )
                self.assertEqual(chain["concept_selection"]["selected_concept_id"], expected)
                self.assertNotEqual(chain["concept_selection"]["selected_concept_id"], "quiet_memory_wall")

    def test_selection_enriches_effect_with_design_params_that_reach_prompt_pack(self):
        from video_pipeline_core.effect_design_concept import (
            build_effect_design_concept_chain,
            apply_effect_concept_to_effect,
        )
        from video_pipeline_core.effect_factory_boundary import (
            build_effect_revision_request,
            build_timeline,
        )
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        chain = build_effect_design_concept_chain(
            request="有溫度的訓練回顧開場，不要像簡報",
            effect_role="opening_title",
            duration_sec=4.0,
        )
        effect = {
            "effect_id": "fx_design_01",
            "role": "title_card",
            "intent": "training recap opening",
            "intensity": "medium",
            "target": {"beat_id": "beat_opening", "segment_id": "seg_opening"},
            "visual_language": ["memory photo wall"],
            "required_for_story": True,
            "must_preserve_proof": True,
            "allowed_backends": ["remotion_preview", "remotion_render"],
            "fallback": "ask for supported visual technique",
            "duration_sec": 4.0,
            "display_text": "Training recap",
            "subtitle_text": "",
            "template_id": "memory_photo_wall",
            "prompt_parameters": {
                "effect_build_spec": {
                    "component": "MemoryPhotoWall",
                    "duration_sec": 4.0,
                    "material_refs": [],
                }
            },
        }

        enriched = apply_effect_concept_to_effect(effect, chain["concept_selection"])
        params = enriched["prompt_parameters"]
        self.assertEqual(params["design_concept"]["concept_id"], "quiet_memory_wall")
        self.assertIn("avoid_presentation_deck", params["negative_rules"])
        self.assertEqual(
            params["effect_build_spec"]["camera_motion"],
            "slow_push_in",
        )
        self.assertEqual(enriched["presentation"]["text_position"], "bottom_left")
        self.assertIn("quiet_memory_wall", enriched["visual_language"])

        plan = {"artifact_role": "effect_intent_plan", "version": 1, "effects": [enriched]}
        pack = build_remotion_prompt_pack(
            build_effect_revision_request(plan),
            plan,
            timeline=build_timeline(plan),
            output_dir="remotion_effects",
        )
        job_params = pack["jobs"][0]["props"]["prompt_parameters"]
        self.assertEqual(job_params["design_concept"]["concept_id"], "quiet_memory_wall")
        self.assertEqual(
            job_params["effect_build_spec"]["reveal_mode"],
            "one_by_one",
        )
        self.assertEqual(
            pack["jobs"][0]["props"]["presentation"]["background_style"],
            "memory_photo_wall",
        )

    def test_design_review_flags_default_copy_and_presentation_padding(self):
        from video_pipeline_core.effect_design_concept import build_effect_design_review

        selection = {
            "artifact_role": "effect_concept_selection",
            "version": 1,
            "selected_concept_id": "quiet_memory_wall",
            "selected_concept": {
                "title_direction": {
                    "avoid_copy": ["Reviewed material memory wall"],
                },
                "review_rubric": [
                    "emotional_fit",
                    "presentation_avoidance",
                    "copy_specificity",
                    "material_presence",
                    "pacing_fit",
                ],
            },
        }
        render_report = {
            "artifact_role": "effect_render_probe",
            "version": 1,
            "playable_preview": True,
            "duration_sec": 5.0,
            "requested_duration_sec": 4.0,
            "display_text": "Training recap",
            "subtitle_text": "Reviewed material memory wall",
            "uses_real_material_refs": True,
            "contact_sheet": "frames/contact_sheet.jpg",
        }

        review = build_effect_design_review(selection, render_report)

        self.assertEqual(review["artifact_role"], "effect_design_review")
        self.assertEqual(review["status"], "revise")
        issue_ids = {item["issue_id"] for item in review["blocking_issues"]}
        self.assertIn("default_or_internal_copy", issue_ids)
        self.assertIn("duration_padding_or_drift", issue_ids)
        self.assertEqual(review["next_action"], "revise_contract_or_render")

    def test_cli_writes_design_concept_chain(self):
        import video_tools

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with redirect_stdout(StringIO()):
                video_tools.cmd_effect_design_concept(SimpleNamespace(
                    request="有溫度的訓練回顧開場，不要像簡報",
                    effect_role="opening_title",
                    duration_sec=4.0,
                    out_dir=str(root),
                ))

            for name in [
                "effect_design_brief.json",
                "effect_concept_options.json",
                "effect_concept_selection.json",
            ]:
                self.assertTrue((root / name).is_file(), name)
            selection = json.loads((root / "effect_concept_selection.json").read_text(encoding="utf-8"))
            self.assertEqual(selection["selected_concept_id"], "quiet_memory_wall")

    def test_cli_accepts_utf8_request_file_for_chinese_text(self):
        import video_tools

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_file = root / "request.txt"
            request_file.write_text("做一個科技感很強、logo 飛進來的開場，但不要太廉價", encoding="utf-8")
            out_dir = root / "out"
            with redirect_stdout(StringIO()):
                video_tools.cmd_effect_design_concept(SimpleNamespace(
                    request="",
                    request_file=str(request_file),
                    effect_role="opening_title",
                    duration_sec=15.0,
                    material_context="reviewed_or_local_material_refs",
                    preferred_concept_id="",
                    out_dir=str(out_dir),
                ))

            brief = json.loads((out_dir / "effect_design_brief.json").read_text(encoding="utf-8"))
            selection = json.loads((out_dir / "effect_concept_selection.json").read_text(encoding="utf-8"))
            self.assertIn("technology", brief["semantic_tokens"])
            self.assertEqual(selection["selected_concept_id"], "tech_logo_fly_in")


if __name__ == "__main__":
    unittest.main()
