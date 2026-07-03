import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
            self.assertEqual(manifest["motion_graphics_contract"], "motion_graphics_contract.json")
            self.assertEqual(manifest["motion_graphics_render_plan"], "motion_graphics_render_plan.json")
            self.assertEqual(manifest["render_outputs"][0]["path"], "motion_graphics/title_001.ass")
            self.assertTrue((Path(d) / manifest["render_outputs"][0]["path"]).exists())
        self.assertTrue(result["ok"])
        self.assertEqual(len(manifest["render_outputs"]), 1)
        output = manifest["render_outputs"][0]
        self.assertEqual(output["backend"], "ffmpeg_libass")
        self.assertEqual(output["status"], "asset_ready")

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

    def test_html_playwright_writes_deterministic_info_card_html(self):
        item = {
            "id": "metric_001",
            "effect_type": "info_card",
            "text": {"main": "42", "subtitle": "completed"},
        }
        with tempfile.TemporaryDirectory() as d:
            path = motion_graphics._write_html_overlay(item, Path(d) / "metric.html")
            content = Path(path).read_text(encoding="utf-8")

        self.assertIn("window.setProgress", content)
        self.assertIn("42", content)
        self.assertIn("completed", content)
        self.assertIn("min-width:620px", content)
        self.assertIn("font-size:150px", content)
        self.assertIn("font-size:40px", content)

    def test_html_playwright_runner_records_rendered_overlay(self):
        contract = self._contract()
        contract["items"][0]["backend"] = "html_playwright"
        contract["items"][0]["effect_type"] = "info_card"
        with tempfile.TemporaryDirectory() as d, patch(
            "video_pipeline_core.motion_graphics._render_html_playwright_overlay"
        ) as render:
            overlay = Path(d) / "motion_graphics" / "title_001.overlay.mov"
            render.return_value = {
                "path": str(overlay),
                "html_path": str(Path(d) / "motion_graphics" / "title_001.html"),
                "frames_dir": str(Path(d) / "motion_graphics" / "title_001.frames"),
                "frame_count": 30,
            }
            result = motion_graphics.write_motion_graphics_artifacts(contract, d)
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

        output = manifest["render_outputs"][0]
        self.assertEqual(output["status"], "asset_ready")
        self.assertEqual(output["backend"], "html_playwright")
        self.assertEqual(output["frame_count"], 30)

    def test_composite_html_playwright_outputs_marks_asset_composited(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video = root / "final.mp4"
            overlay = root / "metric.overlay.mov"
            video.write_bytes(b"input")
            overlay.write_bytes(b"overlay")
            outputs = [{
                "effect_id": "metric_001",
                "backend": "html_playwright",
                "status": "asset_ready",
                "path": str(overlay),
                "start_sec": 2.0,
            }]

            def fake_run(command, **_kwargs):
                Path(command[-1]).write_bytes(b"composited")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("video_pipeline_core.motion_graphics.subprocess.run", fake_run):
                result = motion_graphics.composite_html_playwright_outputs(video, outputs)

            self.assertTrue(result["ok"], result)
            self.assertEqual(outputs[0]["status"], "composited")
            self.assertIn("overlay=eof_action=pass", " ".join(result["command"]))

    def test_composite_motion_graphics_outputs_dispatches_both_safe_backends(self):
        outputs = [{"backend": "ffmpeg_libass"}, {"backend": "html_playwright"}]
        with patch(
            "video_pipeline_core.motion_graphics.composite_ffmpeg_libass_outputs",
            return_value={"ok": True, "status": "skipped", "outputs": outputs},
        ) as libass, patch(
            "video_pipeline_core.motion_graphics.composite_html_playwright_outputs",
            return_value={"ok": True, "status": "composited", "outputs": outputs},
        ) as html_composite:
            result = motion_graphics.composite_motion_graphics_outputs("final.mp4", outputs)

        libass.assert_called_once()
        html_composite.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "composited")

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

    def test_contract_from_timeline_selects_functional_text_recipes(self):
        canonical = {"segments": [
            {"segment": 1, "text_layer": {"narrative": "Opening thought", "reason": "open"}},
            {"segment": 2, "text_layer": {"label": "Chapter Two", "reason": "chapter"}},
            {"segment": 3, "text_layer": {
                "name_super": {"text": "A. Lin", "title": "Director"},
                "reason": "identify speaker",
            }},
        ]}
        timeline = {"clips": [
            {"segment": 1, "timeline_in_sec": 0.0, "timeline_out_sec": 2.0},
            {"segment": 2, "timeline_in_sec": 2.0, "timeline_out_sec": 4.0},
            {"segment": 3, "timeline_in_sec": 4.0, "timeline_out_sec": 6.0},
        ]}

        contract = motion_graphics.contract_from_timeline(canonical, timeline)
        by_segment = {item["segment"]: item for item in contract["items"]}

        self.assertEqual(by_segment[1]["template"], "title_fade")
        self.assertEqual(by_segment[1]["style"]["motion"], "fade_scale")
        self.assertEqual(by_segment[2]["template"], "section_label")
        self.assertEqual(by_segment[2]["style"]["motion"], "pop")
        self.assertEqual(by_segment[3]["template"], "lower_third_clean")
        self.assertEqual(by_segment[3]["style"]["motion"], "slide_up")

    def test_contract_from_timeline_honors_runtime_lower_third_placement(self):
        canonical = {"segments": [{
            "segment": 1,
            "text_layer": {"narrative": "Opening thought", "reason": "open"},
        }]}
        timeline = {"clips": [{
            "segment": 1,
            "timeline_in_sec": 0.0,
            "timeline_out_sec": 2.0,
            "text_overlay": {
                "narrative": "Opening thought",
                "placement": "lower_third",
            },
        }]}

        contract = motion_graphics.contract_from_timeline(canonical, timeline)
        item = contract["items"][0]

        self.assertEqual(item["effect_type"], "lower_third")
        self.assertEqual(item["template"], "lower_third_clean")
        self.assertEqual(item["style"]["safe_area"], "lower_third")

    def test_contract_from_effect_intent_plan_creates_timed_ffmpeg_text_items(self):
        effect_plan = {
            "artifact_role": "effect_intent_plan",
            "version": 1,
            "effects": [{
                "effect_id": "fx_b01_lower",
                "role": "lower_third",
                "intent": "訓練中心第一天",
                "intensity": "low",
                "target": {"beat_id": "b01", "segment_id": "1"},
                "visual_language": ["clean lower third"],
                "required_for_story": False,
                "must_preserve_proof": True,
                "allowed_backends": ["ffmpeg_light_effects"],
                "fallback": "none",
            }, {
                "effect_id": "fx_b02_remotion",
                "role": "chapter_transition",
                "intent": "page turn",
                "intensity": "medium",
                "target": {"beat_id": "b02", "segment_id": "2"},
                "visual_language": [],
                "required_for_story": False,
                "must_preserve_proof": False,
                "allowed_backends": ["remotion_preview"],
                "fallback": "simple fade",
            }],
        }
        timeline = {"clips": [
            {"segment": 1, "timeline_in_sec": 2.0, "timeline_out_sec": 5.5},
            {"segment": 2, "timeline_in_sec": 6.0, "timeline_out_sec": 7.0},
        ]}

        contract = motion_graphics.contract_from_effect_intent_plan(
            effect_plan,
            timeline,
            backend="ffmpeg_libass",
            contract_hash="sha256:test",
        )

        self.assertEqual(contract["contract_hash"], "sha256:test")
        self.assertEqual(len(contract["items"]), 1)
        item = contract["items"][0]
        self.assertEqual(item["id"], "fxintent_fx_b01_lower")
        self.assertEqual(item["source_effect_id"], "fx_b01_lower")
        self.assertEqual(item["effect_type"], "lower_third")
        self.assertEqual(item["timing"], {"start_sec": 2.0, "duration_sec": 3.5})
        self.assertEqual(item["text"]["main"], "訓練中心第一天")

    def test_ffmpeg_libass_recipes_emit_motion_tags(self):
        contract = self._contract()
        contract["items"][0]["style"]["motion"] = "slide_up"
        with tempfile.TemporaryDirectory() as d:
            result = motion_graphics.write_motion_graphics_artifacts(contract, d)
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
            ass_path = Path(d) / manifest["render_outputs"][0]["path"]
            content = ass_path.read_text(encoding="utf-8-sig")

        self.assertIn(r"\move(", content)
        self.assertIn(r"\fad(", content)

    def test_composite_ffmpeg_libass_outputs_marks_assets_composited(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video = root / "final.mp4"
            overlay = root / "title.ass"
            video.write_bytes(b"input")
            overlay.write_text("[Script Info]\n", encoding="utf-8")
            outputs = [{
                "effect_id": "title_001",
                "backend": "ffmpeg_libass",
                "status": "asset_ready",
                "path": str(overlay),
            }]

            def fake_run(command, **_kwargs):
                Path(command[-1]).write_bytes(b"composited")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("video_pipeline_core.motion_graphics.subprocess.run", fake_run):
                result = motion_graphics.composite_ffmpeg_libass_outputs(video, outputs)

            self.assertTrue(result["ok"], result)
            self.assertEqual(video.read_bytes(), b"composited")
            self.assertEqual(outputs[0]["status"], "composited")
            self.assertIn("subtitles=", " ".join(result["command"]))


if __name__ == "__main__":
    unittest.main()
