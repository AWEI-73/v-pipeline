import unittest


class EffectTemplateDictionaryTest(unittest.TestCase):
    def test_training_recap_dictionary_records_reviewed_effect_templates(self):
        from video_pipeline_core.effect_template_dictionary import (
            load_effect_template_dictionary,
            templates_by_id,
        )

        dictionary = load_effect_template_dictionary()
        templates = templates_by_id(dictionary)

        expected_ids = {
            "training_opening_title",
            "module_label_white_blue",
            "speaker_subtitle_yellow_bar",
            "soft_light_transition",
            "highlight_warm_glow",
            "blurred_side_fill",
            "profile_memory_card",
            "film_strip_transition_card",
            "clean_white_quote_card",
        }
        self.assertEqual(dictionary["artifact_role"], "effect_template_dictionary")
        self.assertEqual(dictionary["version"], 1)
        self.assertTrue(expected_ids.issubset(set(templates)))
        self.assertEqual(
            templates["training_opening_title"]["default_presentation"]["background_style"],
            "black_collage",
        )
        self.assertEqual(
            templates["module_label_white_blue"]["default_presentation"]["background_style"],
            "white_blue_label",
        )

    def test_dictionary_rejects_duplicate_template_ids(self):
        from video_pipeline_core.effect_template_dictionary import validate_effect_template_dictionary

        payload = {
            "artifact_role": "effect_template_dictionary",
            "version": 1,
            "templates": [{
                "template_id": "same",
                "role": "title_card",
                "component_family": "title_reveal",
                "render_backend": "remotion_worker",
                "required_fields": [],
                "default_presentation": {
                    "text_position": "bottom_left",
                    "text_scale": "large",
                    "effect_strength": "medium",
                    "safe_area": "title_safe",
                },
            }, {
                "template_id": "same",
                "role": "title_card",
                "component_family": "title_reveal",
                "render_backend": "remotion_worker",
                "required_fields": [],
                "default_presentation": {
                    "text_position": "bottom_left",
                    "text_scale": "large",
                    "effect_strength": "medium",
                    "safe_area": "title_safe",
                },
            }],
        }
        with self.assertRaises(ValueError):
            validate_effect_template_dictionary(payload)


if __name__ == "__main__":
    unittest.main()
