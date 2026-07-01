import json
import tempfile
import unittest
from pathlib import Path


class EffectCapabilityReviewTest(unittest.TestCase):
    def test_supports_generic_lightning_layer_graph(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "electric lightning title opening",
            "effect_role": "opening_title",
            "effect_build_spec": {
                "component": "GenericRemotionEffect",
                "duration_sec": 4,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": [
                    {"id": "arcs", "type": "electric_arcs", "params": {}},
                    {"id": "sparks", "type": "particle_overlay", "params": {}},
                    {"id": "title", "type": "text", "params": {}},
                ],
                "timing": {},
                "review_required": True,
            },
        })

        self.assertEqual(review["artifact_role"], "effect_capability_review")
        self.assertEqual(review["decision"], "supported")
        self.assertTrue(review["build_allowed"])
        self.assertEqual(review["backend_policy"]["worker"], "remotion-effect-worker")
        self.assertIn("electric_arcs", review["supported_layer_types"])

    def test_suggests_radial_current_for_outer_ring_energy_request(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "subtle electric current on the outer ring of a logo intro",
            "effect_role": "opening_title",
            "duration_sec": 15,
        })

        self.assertEqual(review["decision"], "partial")
        self.assertFalse(review["build_allowed"])
        self.assertIn("radial_current", review["suggested_layer_types"])
        self.assertEqual(review["next_action"], "confirm_or_adjust_effect_build_spec")

    def test_rejects_unavailable_3d_character_animation(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "make a realistic 3D dragon character fly around the trainee",
            "effect_role": "opening_title",
        })

        self.assertEqual(review["decision"], "unsupported")
        self.assertFalse(review["build_allowed"])
        self.assertEqual(review["next_action"], "revise_effect_request_or_choose_supported_layers")

    def test_invalid_build_spec_returns_unsupported_artifact_instead_of_raising(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "unsupported shader title",
            "effect_role": "opening_title",
            "effect_build_spec": {
                "component": "GenericRemotionEffect",
                "duration_sec": 4,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": [{"id": "shader", "type": "dragon_shader", "params": {}}],
                "timing": {},
                "review_required": True,
            },
        })

        self.assertEqual(review["decision"], "unsupported")
        self.assertFalse(review["build_allowed"])
        self.assertIn("unsupported generic effect layer type", review["reason"])
        self.assertEqual(review["next_action"], "revise_effect_build_spec")

    def test_supported_layers_still_need_handoff_context_before_build_allowed(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "electric lightning title opening",
            "effect_build_spec": {
                "component": "GenericRemotionEffect",
                "duration_sec": 4,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": [
                    {"id": "arcs", "type": "electric_arcs", "params": {}},
                    {"id": "title", "type": "text", "params": {}},
                ],
                "timing": {},
                "review_required": True,
            },
        })

        self.assertEqual(review["decision"], "supported")
        self.assertFalse(review["build_allowed"])
        self.assertFalse(review["production_handoff_allowed"])
        self.assertIn("effect_role", review["missing_inputs"])
        self.assertEqual(review["next_action"], "complete_effect_handoff_context")

    def test_reroutes_story_scene_generation_out_of_effect_factory(self):
        from video_pipeline_core.effect_capability_review import review_effect_capability

        review = review_effect_capability({
            "request": "generate a new sakura forest scene with two children walking",
            "effect_role": "story_scene",
        })

        self.assertEqual(review["decision"], "reroute_material")
        self.assertEqual(review["reroute_to"], "generated_material_provider")
        self.assertFalse(review["build_allowed"])

    def test_writes_review_artifact(self):
        from video_pipeline_core.effect_capability_review import write_effect_capability_review

        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "effect_capability_review.json"
            result = write_effect_capability_review({
                "request": "terminal data stream title",
                "effect_role": "opening_title",
            }, out)

            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "effect_capability_review")
            self.assertEqual(payload["decision"], result["decision"])


if __name__ == "__main__":
    unittest.main()
