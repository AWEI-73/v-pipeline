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
