import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from video_pipeline_core.generated_image_provider_packet import (
    build_generated_image_provider_packet,
    build_image_agent_prompt_handoff,
    fill_provider_outputs_from_codex_images,
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


def _png(path: Path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 360), color).save(path)


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
            second = packet["items"][1]
            self.assertEqual(first["job_id"], "gen_rooftop")
            self.assertEqual(first["panel_index"], 1)
            self.assertEqual(first["panel_count"], 2)
            self.assertEqual(second["panel_index"], 2)
            self.assertTrue(first["target_file"].endswith("provider_outputs/nd_rooftop_choice_gen_rooftop_p01.png"))
            self.assertIn("Use case: illustration-story", first["prompt"])
            self.assertIn("show the courier deciding", first["prompt"])
            self.assertIn("Panel variation: panel 1 of 2", first["prompt"])
            self.assertIn("Panel variation: panel 2 of 2", second["prompt"])
            self.assertNotEqual(first["panel_variation"], second["panel_variation"])
            self.assertNotEqual(first["prompt"], second["prompt"])
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

    def test_builds_image_agent_prompt_handoff_from_provider_packet(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            handoff_dir = d / "handoff"
            build_generated_image_provider_packet(
                _fallback(),
                packet_dir,
                style_profile=_style_profile(),
                providers=["codex_imagegen"],
            )

            result = build_image_agent_prompt_handoff(
                packet_dir / "generated_provider_packet.json",
                out_dir=handoff_dir,
                max_items=1,
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["item_count"], 1)
            handoff = json.loads(
                (handoff_dir / "image_agent_prompt_handoff.json").read_text(encoding="utf-8")
            )
            self.assertEqual(handoff["artifact_role"], "image_agent_prompt_handoff")
            self.assertEqual(handoff["next_action"], "call_image_generation_agent")
            self.assertTrue(handoff["fail_closed"])
            self.assertEqual(len(handoff["items"]), 1)
            first = handoff["items"][0]
            self.assertEqual(first["tool_mode"], "built_in_image_gen")
            self.assertTrue(first["target_file"].endswith(".png"))
            self.assertIn("Use case: illustration-story", first["prompt"])
            self.assertIn("Do not create a text card", first["save_policy"])
            prompt_md = (handoff_dir / "image_agent_prompt.md").read_text(encoding="utf-8")
            self.assertIn("Use a real image generation tool", prompt_md)
            self.assertNotIn("test_pil outputs are acceptable", prompt_md)

    def test_image_agent_prompt_handoff_fails_for_placeholder_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet = {
                "artifact_role": "generated_image_provider_packet",
                "items": [
                    {
                        "job_id": "bad",
                        "target_file": str(d / "bad.png"),
                        "prompt": "make a placeholder text card",
                    }
                ],
            }
            packet_path = d / "generated_provider_packet.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")

            result = build_image_agent_prompt_handoff(packet_path, out_dir=d / "handoff")

            self.assertFalse(result["ok"])
            self.assertIn("forbidden placeholder", "; ".join(result["errors"]))
            self.assertFalse((d / "handoff" / "image_agent_prompt_handoff.json").exists())

    def test_cli_writes_image_agent_prompt_handoff(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fallback = d / "fallback.json"
            packet_dir = d / "packet"
            handoff_dir = d / "handoff"
            fallback.write_text(json.dumps(_fallback(), ensure_ascii=False), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-image-provider-packet",
                    str(fallback),
                    "--out-dir",
                    str(packet_dir),
                    "--providers",
                    "codex_imagegen",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "image-agent-prompt-handoff",
                    str(packet_dir / "generated_provider_packet.json"),
                    "--out-dir",
                    str(handoff_dir),
                    "--max-items",
                    "1",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((handoff_dir / "image_agent_prompt_handoff.json").exists())
            self.assertTrue((handoff_dir / "image_agent_prompt.md").exists())

    def test_fill_provider_outputs_from_explicit_image_files(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            build_generated_image_provider_packet(
                _fallback(),
                packet_dir,
                style_profile=_style_profile(),
                providers=["codex_imagegen"],
            )
            img1 = d / "codex" / "a.png"
            img2 = d / "codex" / "b.png"
            _png(img1, (200, 60, 60))
            _png(img2, (60, 80, 200))

            result = fill_provider_outputs_from_codex_images(
                packet_dir / "generated_provider_packet.json",
                image_files=[img1, img2],
                out_path=packet_dir / "generated_provider_outputs.json",
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["copied_count"], 2)
            provider_outputs = json.loads(
                (packet_dir / "generated_provider_outputs.json").read_text(encoding="utf-8"))
            self.assertEqual(provider_outputs["artifact_role"], "generated_provider_outputs")
            for item in provider_outputs["items"]:
                self.assertEqual(item["provider"], "codex_imagegen")
                self.assertTrue(Path(item["file"]).exists())
                with Image.open(item["file"]) as im:
                    self.assertEqual(im.size, (640, 360))

    def test_fill_provider_outputs_accepts_files_already_at_target_paths(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            build_generated_image_provider_packet(
                _fallback(),
                packet_dir,
                style_profile=_style_profile(),
                providers=["codex_imagegen"],
            )
            packet = json.loads(
                (packet_dir / "generated_provider_packet.json").read_text(encoding="utf-8")
            )
            target1 = Path(packet["items"][0]["target_file"])
            target2 = Path(packet["items"][1]["target_file"])
            _png(target1, (200, 60, 60))
            _png(target2, (60, 80, 200))

            result = fill_provider_outputs_from_codex_images(
                packet_dir / "generated_provider_packet.json",
                image_files=[target1, target2],
                out_path=packet_dir / "generated_provider_outputs.json",
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["copied_count"], 2)
            provider_outputs = json.loads(
                (packet_dir / "generated_provider_outputs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(provider_outputs["items"][0]["file"], str(target1.resolve()).replace("\\", "/"))

    def test_fill_provider_outputs_from_latest_generated_images_session(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            build_generated_image_provider_packet(
                _fallback(),
                packet_dir,
                style_profile=_style_profile(),
                providers=["codex_imagegen"],
            )
            old_session = d / "generated_images" / "old"
            new_session = d / "generated_images" / "new"
            _png(old_session / "old.png", (10, 10, 10))
            _png(new_session / "one.png", (120, 10, 10))
            _png(new_session / "two.png", (10, 120, 10))

            result = fill_provider_outputs_from_codex_images(
                packet_dir / "generated_provider_packet.json",
                generated_root=d / "generated_images",
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["refs"]["source_session"].replace("\\", "/").split("/")[-1], "new")
            target_files = [Path(item["file"]) for item in result["provider_outputs"]["items"]]
            self.assertEqual(len(target_files), 2)
            self.assertTrue(all(path.exists() for path in target_files))

    def test_fill_provider_outputs_prefers_latest_session_with_enough_images_on_mtime_tie(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            build_generated_image_provider_packet(
                _fallback(),
                packet_dir,
                style_profile=_style_profile(),
                providers=["codex_imagegen"],
            )
            old_session = d / "generated_images" / "old"
            new_session = d / "generated_images" / "new"
            paths = [
                old_session / "old.png",
                new_session / "one.png",
                new_session / "two.png",
            ]
            for path, color in zip(paths, [(10, 10, 10), (120, 10, 10), (10, 120, 10)]):
                _png(path, color)
                os.utime(path, (1000, 1000))

            result = fill_provider_outputs_from_codex_images(
                packet_dir / "generated_provider_packet.json",
                generated_root=d / "generated_images",
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["refs"]["source_session"].replace("\\", "/").split("/")[-1], "new")

    def test_fill_provider_outputs_fails_when_images_are_insufficient(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            packet_dir = d / "packet"
            build_generated_image_provider_packet(_fallback(), packet_dir)
            img1 = d / "only.png"
            _png(img1, (200, 60, 60))

            result = fill_provider_outputs_from_codex_images(
                packet_dir / "generated_provider_packet.json",
                image_files=[img1],
            )

            self.assertFalse(result["ok"])
            self.assertIn("not enough image files", "; ".join(result["errors"]))
            self.assertFalse((packet_dir / "generated_provider_outputs.json").exists())

    def test_cli_fills_provider_outputs_from_explicit_image_files(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fallback = d / "fallback.json"
            packet_dir = d / "packet"
            fallback.write_text(json.dumps(_fallback(), ensure_ascii=False), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-image-provider-packet",
                    str(fallback),
                    "--out-dir",
                    str(packet_dir),
                    "--providers",
                    "codex_imagegen",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            img1 = d / "a.png"
            img2 = d / "b.png"
            _png(img1, (200, 60, 60))
            _png(img2, (60, 80, 200))

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "codex-imagegen-provider-fill",
                    str(packet_dir / "generated_provider_packet.json"),
                    "--image-files",
                    str(img1),
                    str(img2),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((packet_dir / "generated_provider_outputs.json").exists())


if __name__ == "__main__":
    unittest.main()
