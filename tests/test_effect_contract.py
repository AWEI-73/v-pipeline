import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_contract import (
    compile_effect_contract,
    validate_effect_asset_spec,
    validate_effect_intent_plan,
)
from video_pipeline_core.tool_command_catalog import build_command_manifest, build_workflow_manifest


class EffectContractTest(unittest.TestCase):
    def _shot_plan(self):
        return {
            "artifact_role": "director_shot_plan",
            "beats": [
                {
                    "beat_id": "b01",
                    "segment_id": "seg_01",
                    "story_function": "opening_hook",
                    "effect_intent": {
                        "role": "title_card",
                        "intent": "0.66 percent memory title",
                        "intensity": "medium",
                        "visual_language": ["paper_texture", "number_overlay"],
                        "required_for_story": True,
                        "fallback": "simple_title_card_fade",
                    },
                },
                {
                    "beat_id": "b02",
                    "segment_id": "seg_02",
                    "story_function": "proof_training",
                    "effect_intent": {
                        "role": "color_grade",
                        "intent": "warm training memory",
                        "intensity": "low",
                        "must_preserve_proof": True,
                    },
                },
            ],
        }

    def test_compiles_neutral_effect_intent_without_backend_lockin(self):
        compiled = compile_effect_contract(self._shot_plan())
        plan = compiled["effect_intent_plan"]
        spec = compiled["effect_asset_spec"]

        self.assertEqual(plan["artifact_role"], "effect_intent_plan")
        self.assertEqual(spec["artifact_role"], "effect_asset_spec")
        self.assertEqual(len(plan["effects"]), 2)
        first = plan["effects"][0]
        self.assertEqual(first["effect_id"], "fx_b01_title_card")
        self.assertEqual(first["target"]["beat_id"], "b01")
        self.assertEqual(first["required_for_story"], True)
        self.assertEqual(first["allowed_backends"], ["ffmpeg_light_effects", "motion_graphics", "remotion_preview"])
        self.assertNotIn("component", first)
        self.assertNotIn("durationFrames", json.dumps(plan["effects"]))
        self.assertEqual(spec["assets"][0]["asset_role"], "effect")
        self.assertEqual(spec["assets"][0]["must_not_satisfy_material_need"], True)

    def test_validate_rejects_remotion_specific_fields_in_neutral_plan(self):
        plan = compile_effect_contract(self._shot_plan())["effect_intent_plan"]
        plan["effects"][0]["remotion_component"] = "ReportPageFlip"
        with self.assertRaises(ValueError):
            validate_effect_intent_plan(plan)

    def test_validate_rejects_effect_asset_as_material_coverage(self):
        spec = compile_effect_contract(self._shot_plan())["effect_asset_spec"]
        spec["assets"][0]["asset_role"] = "material"
        with self.assertRaises(ValueError):
            validate_effect_asset_spec(spec)

    def test_invalid_effect_role_fails_closed(self):
        shot_plan = self._shot_plan()
        shot_plan["beats"][0]["effect_intent"]["role"] = "teleport"
        with self.assertRaises(ValueError):
            compile_effect_contract(shot_plan)

    def test_empty_or_absent_effect_intents_produce_empty_artifacts(self):
        compiled = compile_effect_contract({"beats": [{"beat_id": "b01"}]})
        self.assertEqual(compiled["effect_intent_plan"]["effects"], [])
        self.assertEqual(compiled["effect_asset_spec"]["assets"], [])

    def test_cli_writes_plan_and_spec(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shot = root / "director_shot_plan.json"
            plan = root / "effect_intent_plan.json"
            spec = root / "effect_asset_spec.json"
            shot.write_text(json.dumps(self._shot_plan()), encoding="utf-8")

            import subprocess
            import sys

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "video_tools.py"),
                    "effect-intent-plan",
                    str(shot),
                    "--out-plan",
                    str(plan),
                    "--out-spec",
                    str(spec),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(plan.read_text(encoding="utf-8"))["artifact_role"], "effect_intent_plan")
            self.assertEqual(json.loads(spec.read_text(encoding="utf-8"))["artifact_role"], "effect_asset_spec")

    def test_command_catalog_exposes_effect_workflow(self):
        commands = ["effect-intent-plan", "light-effects-plan"]
        manifest = build_command_manifest(commands)
        workflow = build_workflow_manifest(commands)
        self.assertEqual(manifest["commands"]["effect-intent-plan"]["group"], "contract")
        self.assertIn("effects_contract", workflow["workflows"])
        missing_for_effects = [
            item for item in workflow["missing_commands"]
            if item["workflow"] == "effects_contract"
        ]
        self.assertEqual(missing_for_effects, [])

    def test_upstream_skills_document_effect_intent_boundary(self):
        root = Path(__file__).resolve().parents[1]
        story_skill = (root / "skills" / "story-soul-blueprint.md").read_text(encoding="utf-8")
        workflow_skill = (root / "skills" / "video-workflow.md").read_text(encoding="utf-8")
        self.assertIn("Effect Intent Hook", story_skill)
        self.assertIn("effect_intent", story_skill)
        self.assertIn("effect-intent-plan", story_skill)
        self.assertIn("effect_direction", workflow_skill)
        self.assertIn("effect_intent_plan.json", workflow_skill)


if __name__ == "__main__":
    unittest.main()
