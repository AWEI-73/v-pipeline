import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import contract_adapter as ca
from video_pipeline_core.platform_tools import resolve_ffmpeg


class EffectsE2ETest(unittest.TestCase):
    def _write_media(self, root):
        ffmpeg = resolve_ffmpeg()
        image = root / "panel.png"
        audio = root / "bgm.wav"
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "color=c=blue:s=640x360:d=1", "-vframes", "1", str(image),
        ], capture_output=True, check=True)
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "sine=frequency=440:duration=5", "-c:a", "pcm_s16le", str(audio),
        ], capture_output=True, check=True)
        return image, audio

    def _segment(self, segment, desc):
        return {
            "segment": segment,
            "core": {
                "section_role": "montage",
                "story_purpose": desc,
                "timeline_source": "beat",
            },
            "material_fit": {"visual_desc": desc, "reason": "e2e fixture"},
            "audio": {"role": "music", "reason": "e2e fixture"},
            "visual_style": {"layout": "single", "pace": "hold", "reason": "e2e fixture"},
            "text_layer": "none",
            "requested_duration_sec": 2.0,
        }

    def test_effect_intent_plan_reaches_real_render_and_gap_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out_dir = root / "out"
            out_dir.mkdir()
            image, audio = self._write_media(root)

            material_map = root / "panel.map.json"
            material_map.write_text(json.dumps({
                "asset_id": "panel-a",
                "source": str(image),
                "asset_type": "photo",
                "scenes": [{"start": 0, "end": 0, "caption": "blue training panel"}],
            }), encoding="utf-8")
            material_db = root / "material_db.json"
            material_db.write_text(json.dumps({
                "files": [{"path": str(image), "material_map": "panel.map.json"}],
            }), encoding="utf-8")

            effect_plan = root / "effect_intent_plan.json"
            effect_plan.write_text(json.dumps({
                "artifact_role": "effect_intent_plan",
                "version": 1,
                "effects": [{
                    "effect_id": "fx_lower",
                    "role": "lower_third",
                    "intent": "Chapter 1: Assembly",
                    "intensity": "low",
                    "target": {"beat_id": "b01", "segment_id": "1"},
                    "visual_language": ["clean lower third"],
                    "required_for_story": False,
                    "must_preserve_proof": True,
                    "allowed_backends": ["ffmpeg_light_effects"],
                    "fallback": "none",
                }, {
                    "effect_id": "fx_page_turn",
                    "role": "chapter_transition",
                    "intent": "Page turn to next memory",
                    "intensity": "medium",
                    "target": {"beat_id": "b02", "segment_id": "2"},
                    "visual_language": ["paper turn"],
                    "required_for_story": False,
                    "must_preserve_proof": False,
                    "allowed_backends": ["remotion_preview"],
                    "fallback": "simple fade",
                }],
            }), encoding="utf-8")

            profile = root / "build_profile.json"
            profile.write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
                "motion_graphics_backend": "ffmpeg_libass",
            }), encoding="utf-8")

            contract = root / "contract.json"
            contract.write_text(json.dumps({
                "style": "mv",
                "effect_intent_plan_ref": "effect_intent_plan.json",
                "segments": [
                    self._segment(1, "blue training panel"),
                    self._segment(2, "blue training panel"),
                ],
            }), encoding="utf-8")

            result = ca.run_contract(
                contract,
                material_db=material_db,
                out_path=out_dir / "final.mp4",
                music_path=audio,
                mat_dir=out_dir,
                verbose=False,
                build_profile_config_path=profile,
            )

            self.assertTrue(result["render_ok"], result)
            self.assertTrue((out_dir / "final.mp4").exists())
            self.assertGreater((out_dir / "final.mp4").stat().st_size, 0)

            light_plan = json.loads((out_dir / "light_effects_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {item["source_effect_id"] for item in light_plan["items"]},
                {"fx_lower", "fx_page_turn"},
            )

            motion_manifest = json.loads(
                (out_dir / "motion_graphics_manifest.json").read_text(encoding="utf-8")
            )
            motion_outputs = motion_manifest["render_outputs"]
            self.assertTrue(any(
                output.get("source_effect_id") == "fx_lower"
                and output.get("status") == "composited"
                for output in motion_outputs
            ))

            light_manifest = json.loads(
                (out_dir / "light_effects_manifest.json").read_text(encoding="utf-8")
            )
            self.assertTrue(any(
                output.get("source_effect_id") == "fx_lower"
                and output.get("status") == "composited"
                for output in light_manifest["render_outputs"]
            ))

            baseline = json.loads(
                (out_dir / "light_effects_baseline_review.json").read_text(encoding="utf-8")
            )
            gap_sources = {
                item["source_effect_id"]
                for planned in light_plan["items"]
                for item in [planned]
                if planned["id"] in {gap["effect_id"] for gap in baseline["gaps"]}
            }
            self.assertNotIn("fx_lower", gap_sources)
            self.assertIn("fx_page_turn", gap_sources)
            self.assertEqual(baseline["metrics"]["rendered_count"], 1)
            self.assertEqual(baseline["metrics"]["gap_count"], 1)


if __name__ == "__main__":
    unittest.main()
