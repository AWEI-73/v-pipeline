import unittest


class EffectBuildSpecTest(unittest.TestCase):
    def test_accepts_supported_memory_photo_wall_and_story_transition_specs(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        memory = {
            "component": "MemoryPhotoWall",
            "duration_sec": 8,
            "story_function": "emotional_setup",
            "pacing": "slow",
            "density": "low",
            "reveal_mode": "one_by_one",
            "camera_motion": "slow_push_in",
            "caption_mode": "minimal",
        }
        transition = {
            "component": "StoryToMVTransition",
            "duration_sec": 4,
            "section_from": "story",
            "section_to": "montage",
            "pacing_shift": "slow_to_fast",
            "impact_moment_sec": 2.2,
            "thumbnail_acceleration": "medium",
            "motion_grammar": ["film_rail", "thumbnail_acceleration"],
            "phase_labels": ["STORY", "MONTAGE"],
        }

        self.assertEqual(validate_effect_build_spec(memory)["component"], "MemoryPhotoWall")
        self.assertEqual(validate_effect_build_spec(transition)["component"], "StoryToMVTransition")

    def test_accepts_generic_remotion_effect_layer_graph(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        generic = {
            "component": "GenericRemotionEffect",
            "duration_sec": 5,
            "canvas": {"width": 1920, "height": 1080, "fps": 30},
            "layers": [
                {
                    "id": "data_stream",
                    "type": "glyph_stream",
                    "params": {"glyph_speed": "medium_fast", "glyph_density": "medium"},
                },
                {
                    "id": "title",
                    "type": "text",
                    "params": {"content": "DATA BREACH", "animation": "assemble"},
                },
            ],
            "timing": {"reveal_sec": 3.6, "hold_sec": 1.4},
            "review_required": True,
        }

        normalized = validate_effect_build_spec(generic)

        self.assertEqual(normalized["component"], "GenericRemotionEffect")
        self.assertEqual(normalized["duration_sec"], 5.0)
        self.assertEqual(normalized["canvas"]["fps"], 30)
        self.assertEqual(normalized["layers"][0]["type"], "glyph_stream")

    def test_accepts_generic_brand_hero_with_radial_current_layer(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        spec = {
            "component": "GenericRemotionEffect",
            "duration_sec": 15,
            "canvas": {"width": 1920, "height": 1080, "fps": 30},
            "layers": [
                {
                    "id": "hero",
                    "type": "image_layout",
                    "params": {
                        "layout": "full_bleed_hero",
                        "refs": ["brand_hero.png"],
                        "fade_in_start_sec": 0,
                        "fade_in_end_sec": 2,
                        "fade_out_start_sec": 12,
                        "fade_out_end_sec": 15,
                    },
                },
                {
                    "id": "outer_current",
                    "type": "radial_current",
                    "params": {
                        "flow_style": "smooth_outer_ring",
                        "ring_count": 2,
                        "pulse": "subtle",
                        "fade_in_start_sec": 2,
                        "fade_in_end_sec": 4,
                        "fade_out_start_sec": 11,
                        "fade_out_end_sec": 14,
                    },
                },
                {
                    "id": "camera",
                    "type": "camera_motion",
                    "params": {"motion": "slow_push_in"},
                },
            ],
            "timing": {"intro_sec": 2, "hold_sec": 10, "outro_sec": 3},
            "review_required": True,
        }

        normalized = validate_effect_build_spec(spec)

        self.assertEqual(normalized["component"], "GenericRemotionEffect")
        self.assertEqual(normalized["layers"][0]["params"]["layout"], "full_bleed_hero")
        self.assertEqual(normalized["layers"][1]["type"], "radial_current")

    def test_accepts_generic_logo_3d_motion_layer(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        spec = {
            "component": "GenericRemotionEffect",
            "duration_sec": 15,
            "canvas": {"width": 1920, "height": 1080, "fps": 30},
            "layers": [
                {
                    "id": "logo",
                    "type": "image_layout",
                    "params": {"layout": "center_logo", "refs": [{"path": "logo.png"}]},
                },
                {
                    "id": "logo_motion",
                    "type": "logo_3d_motion",
                    "params": {"motion": "fly_in_orbit_out", "strength": "high", "orbit_count": 1.2},
                },
                {
                    "id": "outer_current",
                    "type": "radial_current",
                    "params": {"flow_style": "smooth_outer_ring"},
                },
            ],
            "timing": {"intro_sec": 4, "hold_sec": 7, "outro_sec": 4},
            "review_required": True,
        }

        normalized = validate_effect_build_spec(spec)

        self.assertEqual(normalized["layers"][1]["type"], "logo_3d_motion")
        self.assertEqual(normalized["layers"][1]["params"]["motion"], "fly_in_orbit_out")

    def test_rejects_unknown_generic_layer_type(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        with self.assertRaisesRegex(ValueError, "unsupported generic effect layer type: dragon_shader"):
            validate_effect_build_spec({
                "component": "GenericRemotionEffect",
                "duration_sec": 5,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": [
                    {"id": "dragon", "type": "dragon_shader", "params": {}},
                    {"id": "title", "type": "text", "params": {"content": "NOPE"}},
                ],
                "timing": {},
                "review_required": True,
            })

    def test_supported_generic_layer_types_come_from_manifest(self):
        from video_pipeline_core.effect_build_spec import SUPPORTED_GENERIC_LAYER_TYPES
        from video_pipeline_core.effect_layer_manifest import generic_layer_types, generic_worker_supported_layer_types

        self.assertEqual(SUPPORTED_GENERIC_LAYER_TYPES, generic_layer_types())
        self.assertLessEqual(generic_worker_supported_layer_types(), generic_layer_types())

    def test_rejects_generic_remotion_effect_without_layers(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        with self.assertRaisesRegex(ValueError, "layers must be a non-empty layer list"):
            validate_effect_build_spec({
                "component": "GenericRemotionEffect",
                "duration_sec": 5,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": [],
                "timing": {},
                "review_required": True,
            })

    def test_rejects_unknown_component_instead_of_silent_template_fallback(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        with self.assertRaisesRegex(ValueError, "unsupported effect_build_spec component: LightningDragon"):
            validate_effect_build_spec({
                "component": "LightningDragon",
                "duration_sec": 2,
            })

    def test_rejects_missing_required_fields_for_supported_component(self):
        from video_pipeline_core.effect_build_spec import validate_effect_build_spec

        with self.assertRaisesRegex(ValueError, "StoryToMVTransition missing required field: section_to"):
            validate_effect_build_spec({
                "component": "StoryToMVTransition",
                "duration_sec": 4,
                "section_from": "story",
                "pacing_shift": "slow_to_fast",
                "impact_moment_sec": 2.2,
                "thumbnail_acceleration": "medium",
                "motion_grammar": ["film_rail"],
                "phase_labels": ["STORY", "MONTAGE"],
            })

    def test_prompt_pack_rejects_unsupported_build_spec_component(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
        from tests.test_remotion_effects import _effect_intent_plan, _effect_revision_request, _timeline

        plan = _effect_intent_plan()
        plan["effects"][0]["prompt_parameters"] = {
            "effect_build_spec": {
                "component": "LightningDragon",
                "duration_sec": 2,
            }
        }

        with self.assertRaisesRegex(ValueError, "unsupported effect_build_spec component: LightningDragon"):
            build_remotion_prompt_pack(
                _effect_revision_request(),
                plan,
                timeline=_timeline(),
                output_dir="effects/remotion",
            )


if __name__ == "__main__":
    unittest.main()
