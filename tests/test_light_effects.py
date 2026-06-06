import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import light_effects


class LightEffectsTest(unittest.TestCase):
    def _contract(self):
        return {
            "segments": [
                {
                    "segment": 1,
                    "core": {"section_role": "opening", "story_purpose": "open"},
                    "material_fit": {"visual_desc": "city opening", "media": "photo"},
                    "visual_style": {
                        "layout": "single",
                        "pace": "hold",
                        "grade": "warm",
                        "reason": "warm opening tone",
                    },
                    "text_layer": {
                        "label": "Opening",
                        "reason": "anchor the chapter",
                    },
                },
                {
                    "segment": 2,
                    "core": {"section_role": "montage", "story_purpose": "show work"},
                    "material_fit": {"visual_desc": "team work", "media": "video"},
                    "visual_style": {
                        "layout": "montage",
                        "pace": "fast",
                        "reason": "energy",
                    },
                    "text_layer": "none",
                },
            ]
        }

    def test_no_effects_profile_produces_empty_plan(self):
        plan = light_effects.build_light_effects_plan(
            self._contract(),
            {"render_profile": "no_effects", "effects_enabled": False},
        )
        self.assertEqual(plan["artifact_role"], "light_effects_plan")
        self.assertEqual(plan["items"], [])
        self.assertEqual(plan["status"], "skipped")

    def test_light_effects_profile_maps_contract_to_safe_operations(self):
        plan = light_effects.build_light_effects_plan(
            self._contract(),
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        operation_types = [item["operation"] for item in plan["items"]]
        self.assertIn("grade", operation_types)
        self.assertIn("kenburns", operation_types)
        self.assertIn("title_card", operation_types)
        self.assertIn("xfade", operation_types)
        self.assertEqual(plan["items"][0]["backend"], "ffmpeg")
        self.assertEqual(plan["status"], "planned")

    def test_write_light_effects_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            result = light_effects.write_light_effects_artifacts(
                self._contract(),
                {"render_profile": "light_effects", "effects_enabled": True},
                d,
            )
            plan = json.loads(Path(result["plan"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(plan["artifact_role"], "light_effects_plan")
        self.assertEqual(manifest["artifact_role"], "light_effects_manifest")
        self.assertEqual(manifest["light_effects_plan"], result["plan"])

    def test_video_tools_light_effects_plan_cli(self):
        with tempfile.TemporaryDirectory() as d:
            workdir = Path(d)
            contract_path = workdir / "segment_contract.json"
            profile_path = workdir / "build_profile.json"
            out_dir = workdir / "build"
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            profile_path.write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
            }), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "light-effects-plan",
                    str(contract_path),
                    "--build-profile",
                    str(profile_path),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads((out_dir / "light_effects_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["artifact_role"], "light_effects_plan")
            self.assertEqual(plan["status"], "planned")


if __name__ == "__main__":
    unittest.main()
