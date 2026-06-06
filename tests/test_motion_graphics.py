import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import motion_graphics


class MotionGraphicsTest(unittest.TestCase):
    def _contract(self, **overrides):
        contract = {
            "motion_graphics_version": 1,
            "contract_hash": "sha256:abc",
            "items": [
                {
                    "id": "title_001",
                    "segment": 1,
                    "effect_type": "title_sequence",
                    "timing": {"start_sec": 0.0, "duration_sec": 4.0},
                    "text": {"main": "礙子清掃", "subtitle": "現場作業紀錄"},
                    "style": {"motion": "fade", "safe_area": "title_safe"},
                    "reason": "開場建立任務主題",
                }
            ],
        }
        contract.update(overrides)
        return contract

    def test_validate_accepts_title_contract(self):
        result = motion_graphics.validate_motion_graphics_contract(self._contract())
        self.assertTrue(result["ok"], result)

    def test_validate_rejects_unknown_backend(self):
        contract = self._contract()
        contract["items"][0]["backend"] = "unknown"
        result = motion_graphics.validate_motion_graphics_contract(contract)
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["field"], "items[0].backend")

    def test_build_render_plan_uses_safe_default_backend(self):
        plan = motion_graphics.build_motion_graphics_render_plan(self._contract())
        item = plan["items"][0]
        self.assertEqual(plan["artifact_role"], "motion_graphics_render_plan")
        self.assertEqual(item["backend"], "ffmpeg_libass")
        self.assertEqual(item["output_mode"], "overlay")
        self.assertEqual(item["duration_sec"], 4.0)

    def test_heavy_backend_requires_policy(self):
        contract = self._contract()
        contract["items"][0]["backend"] = "blender"
        with self.assertRaises(ValueError):
            motion_graphics.build_motion_graphics_render_plan(contract)
        plan = motion_graphics.build_motion_graphics_render_plan(
            contract,
            backend_policy={"allow_heavy_backend": True},
        )
        self.assertEqual(plan["items"][0]["backend"], "blender")

    def test_write_motion_graphics_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            result = motion_graphics.write_motion_graphics_artifacts(self._contract(), d)
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(manifest["motion_graphics_contract"], result["contract"])
        self.assertEqual(manifest["motion_graphics_render_plan"], result["render_plan"])


if __name__ == "__main__":
    unittest.main()
