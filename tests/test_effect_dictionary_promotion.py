import json
import tempfile
import unittest
from pathlib import Path


def _build_spec():
    return {
        "component": "GenericRemotionEffect",
        "duration_sec": 4,
        "canvas": {"width": 1920, "height": 1080, "fps": 30},
        "layers": [
            {"id": "arcs", "type": "electric_arcs", "params": {"strike_count": 4}},
            {"id": "title", "type": "text", "params": {"content": "POWER"}},
        ],
        "timing": {"duration_sec": 4},
        "review_required": True,
    }


class EffectDictionaryPromotionTest(unittest.TestCase):
    def test_promotes_only_reviewed_generic_graph(self):
        from video_pipeline_core.effect_dictionary_promotion import promote_effect_dictionary_entry

        with tempfile.TemporaryDirectory() as temp:
            dictionary = Path(temp) / "effect_dictionary.json"
            out = Path(temp) / "effect_dictionary.promoted.json"
            result = promote_effect_dictionary_entry(
                {
                    "entry_id": "electric_title_burst",
                    "display_name_zh": "電光標題爆發",
                    "intent_tags": ["lightning", "opening_title"],
                    "story_functions": ["impact_opening"],
                    "effect_build_spec": _build_spec(),
                    "review": {
                        "decision": "accept",
                        "reviewer": "director",
                        "evidence_refs": ["preview.mp4", "contact_sheet.jpg"],
                        "reason": "visible and readable",
                    },
                },
                dictionary,
                out,
            )

            self.assertTrue(result["ok"])
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "effect_factory_dictionary")
            self.assertEqual(payload["entries"][0]["id"], "electric_title_burst")
            self.assertEqual(payload["entries"][0]["layer_graph"][0]["type"], "electric_arcs")

    def test_refuses_unreviewed_promotion(self):
        from video_pipeline_core.effect_dictionary_promotion import promote_effect_dictionary_entry

        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "promotion requires accepted review evidence"):
                promote_effect_dictionary_entry(
                    {
                        "entry_id": "electric_title_burst",
                        "display_name_zh": "電光標題爆發",
                        "intent_tags": ["lightning"],
                        "story_functions": ["impact_opening"],
                        "effect_build_spec": _build_spec(),
                        "review": {"decision": "accept", "evidence_refs": []},
                    },
                    Path(temp) / "effect_dictionary.json",
                    Path(temp) / "effect_dictionary.promoted.json",
                )


if __name__ == "__main__":
    unittest.main()
