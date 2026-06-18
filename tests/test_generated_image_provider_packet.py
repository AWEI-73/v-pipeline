import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.generated_image_provider_packet import (
    build_generated_image_provider_packet,
)


def _fallback():
    return {
        "artifact_role": "material_generation_fallback",
        "version": 1,
        "ok": True,
        "generation_jobs": [
            {
                "job_id": "gen_rooftop",
                "need_id": "nd_rooftop_choice",
                "source_type": "generated",
                "status": "planned",
                "media_type": "generated_image",
                "panel_count": 2,
                "story_function": "show the courier deciding to cross the rooftops",
                "emotion": "quiet courage",
                "visual_family": "rooftop_choice",
                "angle_scale": "wide",
                "action_family": "decision",
                "subject": "young courier with red scarf above a sunset city",
                "prompt": "young courier with red scarf above a sunset city, wide 35mm shot, manga watercolor",
                "negative_prompt": "text, logo, watermark, fake documentary proof",
                "material_map_return": {
                    "must_reingest": True,
                    "initial_satisfies_status": "candidate",
                },
                "honesty": {"must_not_claim_real_event": True},
            }
        ],
    }


def _style_profile():
    return {
        "look": "manga watercolor with soft ink line",
        "style_anchors": ["manga watercolor", "soft ink line", "warm sunset"],
        "character_anchors": ["young courier", "red scarf"],
        "palette": ["#203040", "#f2a65a", "#f6ecd2"],
    }


class GeneratedImageProviderPacketTest(unittest.TestCase):
    def test_builds_provider_packet_with_target_files_and_import_template(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "packet"
            result = build_generated_image_provider_packet(
                _fallback(),
                out,
                style_profile=_style_profile(),
                providers=["codex_imagegen", "gemini", "antigravity"],
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["image_count"], 2)
            packet = json.loads((out / "generated_provider_packet.json").read_text(encoding="utf-8"))
            template = json.loads(
                (out / "generated_provider_outputs.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(packet["artifact_role"], "generated_image_provider_packet")
            self.assertEqual(packet["provider_priority"][0], "codex_imagegen")
            self.assertEqual(len(packet["items"]), 2)
            first = packet["items"][0]
            self.assertEqual(first["job_id"], "gen_rooftop")
            self.assertEqual(first["panel_index"], 1)
            self.assertTrue(first["target_file"].endswith("provider_outputs/nd_rooftop_choice_gen_rooftop_p01.png"))
            self.assertIn("Use case: illustration-story", first["prompt"])
            self.assertIn("show the courier deciding", first["prompt"])
            self.assertIn("manga watercolor", first["style_anchors"])
            self.assertIn("young courier", first["character_anchors"])
            self.assertTrue(first["forbidden_as_truth"])

            self.assertEqual(template["artifact_role"], "generated_provider_outputs")
            self.assertEqual(len(template["items"]), 2)
            self.assertEqual(template["items"][0]["file"], first["target_file"])
            self.assertEqual(template["items"][0]["provider"], "codex_imagegen")

    def test_fails_closed_for_non_ok_fallback_or_no_real_provider(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _fallback()
            bad["ok"] = False
            result = build_generated_image_provider_packet(bad, Path(td) / "bad")
            self.assertFalse(result["ok"])
            self.assertIn("material_generation_fallback is not ok", result["errors"])
            self.assertFalse((Path(td) / "bad" / "generated_provider_packet.json").exists())

            result = build_generated_image_provider_packet(
                _fallback(), Path(td) / "test-pil", providers=["test_pil"])
            self.assertFalse(result["ok"])
            self.assertIn("provider list must include a real image provider", "; ".join(result["errors"]))

    def test_cli_writes_packet_and_prompt_markdown(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fallback = d / "material_generation_fallback.json"
            style = d / "style_profile.json"
            out = d / "packet"
            fallback.write_text(json.dumps(_fallback(), ensure_ascii=False), encoding="utf-8")
            style.write_text(json.dumps(_style_profile(), ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-image-provider-packet",
                    str(fallback),
                    "--style-profile",
                    str(style),
                    "--out-dir",
                    str(out),
                    "--providers",
                    "codex_imagegen,gemini,antigravity",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((out / "generated_provider_packet.json").exists())
            self.assertTrue((out / "generated_provider_prompts.md").exists())
            self.assertIn(
                "generated-material-import",
                (out / "generated_provider_prompts.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
