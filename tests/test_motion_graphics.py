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
            self.assertTrue(Path(manifest["render_outputs"][0]["path"]).exists())
        self.assertTrue(result["ok"])
        self.assertEqual(manifest["motion_graphics_contract"], result["contract"])
        self.assertEqual(manifest["motion_graphics_render_plan"], result["render_plan"])
        self.assertEqual(len(manifest["render_outputs"]), 1)
        output = manifest["render_outputs"][0]
        self.assertEqual(output["backend"], "ffmpeg_libass")
        self.assertEqual(output["status"], "rendered")

    def test_ffmpeg_libass_runner_writes_timed_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            plan = motion_graphics.build_motion_graphics_render_plan(self._contract())
            outputs = motion_graphics.run_motion_graphics_render_plan(plan, d)
            ass_path = Path(outputs[0]["path"])
            content = ass_path.read_text(encoding="utf-8-sig")

        self.assertEqual(outputs[0]["effect_id"], "title_001")
        self.assertIn("[Events]", content)
        self.assertIn("Dialogue: 0,0:00:00.00,0:00:04.00", content)
        self.assertIn("fade", outputs[0]["motion"])

    def test_unimplemented_backend_is_explicitly_pending(self):
        contract = self._contract()
        contract["items"][0]["backend"] = "remotion"
        with tempfile.TemporaryDirectory() as d:
            result = motion_graphics.write_motion_graphics_artifacts(contract, d)
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

        self.assertEqual(manifest["render_outputs"][0]["status"], "pending")
        self.assertEqual(manifest["render_outputs"][0]["backend"], "remotion")
        self.assertIsNone(manifest["render_outputs"][0]["path"])

    def test_contract_from_timeline_maps_canonical_text_to_exact_timing(self):
        canonical = {
            "segments": [{
                "segment": 2,
                "text_layer": {"label": "Chapter Two", "reason": "chapter marker"},
            }],
        }
        timeline = {"clips": [
            {"segment": 2, "timeline_in_sec": 3.0, "timeline_out_sec": 5.0},
            {"segment": 2, "timeline_in_sec": 5.0, "timeline_out_sec": 7.5},
        ]}
        contract = motion_graphics.contract_from_timeline(
            canonical, timeline, backend="ffmpeg_libass", contract_hash="sha256:abc"
        )
        item = contract["items"][0]

        self.assertEqual(item["effect_type"], "chapter_card")
        self.assertEqual(item["text"]["main"], "Chapter Two")
        self.assertEqual(item["timing"], {"start_sec": 3.0, "duration_sec": 4.5})


if __name__ == "__main__":
    unittest.main()
