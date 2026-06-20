import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from video_pipeline_core.generated_material_producer import (
    produce_generated_materials_from_provider_outputs,
)


def _needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "provider-intake-test",
        "needs": [
            {
                "need_id": "nd_hero_panel",
                "category": "story",
                "type": "generated_panel",
                "purpose": "show the lead character choosing courage",
                "count": 2,
                "must_have": True,
                "fallback_tier": 2,
                "fallback_options": ["generated comic panels"],
            }
        ],
    }


def _fallback():
    return {
        "artifact_role": "material_generation_fallback",
        "version": 1,
        "ok": True,
        "generation_jobs": [
            {
                "job_id": "gen_hero",
                "need_id": "nd_hero_panel",
                "source_type": "generated",
                "status": "planned",
                "media_type": "generated_image",
                "panel_count": 2,
                "story_function": "show the lead character choosing courage",
                "emotion": "quiet resolve",
                "visual_family": "hero_choice_panel",
                "angle_scale": "medium",
                "action_family": "choice_moment",
                "subject": "lead apprentice holding a lantern",
                "prompt": "lead apprentice holding a lantern, medium shot, quiet resolve, watercolor comic",
                "negative_prompt": "text, watermark, logo",
                "material_map_return": {
                    "must_reingest": True,
                    "initial_satisfies_status": "candidate",
                },
                "honesty": {"must_not_claim_real_event": True},
            }
        ],
        "review_gate": {
            "generated_assets_enter_as": "candidate",
            "must_reingest": True,
            "must_not_claim_real_footage": True,
        },
    }


def _style():
    return {
        "look": "watercolor comic",
        "style_anchors": ["watercolor", "soft ink line"],
        "character_anchors": ["lead apprentice", "amber lantern"],
        "palette": ["#203040", "#e0aa55", "#f5eedc"],
    }


def _png(path: Path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 360), color).save(path)


def _provider_outputs(a: Path, b: Path):
    return {
        "items": [
            {
                "job_id": "gen_hero",
                "file": str(a),
                "provider": "codex_imagegen",
                "style_anchors": ["watercolor", "soft ink line"],
                "character_anchors": ["lead apprentice", "amber lantern"],
            },
            {
                "job_id": "gen_hero",
                "file": str(b),
                "provider": "codex_imagegen",
                "style_anchors": ["watercolor", "soft ink line"],
                "character_anchors": ["lead apprentice", "amber lantern"],
            },
        ]
    }


class GeneratedMaterialProviderIntakeTest(unittest.TestCase):
    def test_imports_provider_outputs_into_manifest_maps_and_quality_review(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = d / "provider" / "hero-a.png"
            p2 = d / "provider" / "hero-b.png"
            _png(p1, (120, 80, 40))
            _png(p2, (30, 90, 120))

            result = produce_generated_materials_from_provider_outputs(
                _fallback(),
                _provider_outputs(p1, p2),
                d / "out",
                material_needs=_needs(),
                style_profile=_style(),
            )

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["image_count"], 2)
            self.assertTrue(result["quality_gate"]["pass"])
            for output in result["outputs"]:
                self.assertEqual(output["source"], "generated")
                self.assertTrue(output["forbidden_as_truth"])
                self.assertTrue(Path(output["file"]).exists())
                self.assertIn("generated_images", output["file"])
            project_map = json.loads(
                (d / "out" / "project_material_map.json").read_text(encoding="utf-8"))
            edges = [
                scene["satisfies"][0]
                for asset in project_map["assets"]
                for scene in asset["scenes"]
            ]
            self.assertEqual(len(edges), 2)
            self.assertTrue(all(edge["status"] == "candidate" for edge in edges))
            review = json.loads(
                (d / "out" / "generated_material_quality_review.json").read_text(encoding="utf-8"))
            first = review["items"][0]
            self.assertTrue(first["rubric"]["style_consistency"]["pass"])
            self.assertTrue(first["rubric"]["character_continuity"]["pass"])

    def test_missing_required_panel_fails_before_writing_project_map(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = d / "provider" / "hero-a.png"
            _png(p1, (120, 80, 40))
            outputs = _provider_outputs(p1, d / "provider" / "missing.png")
            outputs["items"] = outputs["items"][:1]

            result = produce_generated_materials_from_provider_outputs(
                _fallback(), outputs, d / "out",
                material_needs=_needs(), style_profile=_style())

            self.assertFalse(result["ok"])
            self.assertIn("missing provider output", "; ".join(result["errors"]))
            self.assertFalse((d / "out" / "project_material_map.json").exists())

    def test_style_or_character_anchor_mismatch_fails_quality_gate(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = d / "provider" / "hero-a.png"
            p2 = d / "provider" / "hero-b.png"
            _png(p1, (120, 80, 40))
            _png(p2, (30, 90, 120))
            outputs = _provider_outputs(p1, p2)
            outputs["items"][1]["character_anchors"] = ["wrong character"]

            result = produce_generated_materials_from_provider_outputs(
                _fallback(), outputs, d / "out",
                material_needs=_needs(), style_profile=_style())

            self.assertFalse(result["ok"])
            self.assertFalse(result["quality_gate"]["pass"])
            review = json.loads(
                (d / "out" / "generated_material_quality_review.json").read_text(encoding="utf-8"))
            self.assertFalse(review["items"][1]["rubric"]["character_continuity"]["pass"])
            self.assertFalse((d / "out" / "project_material_map.json").exists())

    def test_cli_imports_provider_outputs(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = d / "provider" / "hero-a.png"
            p2 = d / "provider" / "hero-b.png"
            _png(p1, (120, 80, 40))
            _png(p2, (30, 90, 120))
            fallback = d / "fallback.json"
            needs = d / "needs.json"
            outputs = d / "provider_outputs.json"
            style = d / "style.json"
            fallback.write_text(json.dumps(_fallback()), encoding="utf-8")
            needs.write_text(json.dumps(_needs()), encoding="utf-8")
            outputs.write_text(json.dumps(_provider_outputs(p1, p2)), encoding="utf-8")
            style.write_text(json.dumps(_style()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-material-import",
                    str(fallback),
                    "--needs",
                    str(needs),
                    "--provider-outputs",
                    str(outputs),
                    "--style-profile",
                    str(style),
                    "--out-dir",
                    str(d / "out"),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads(
                (d / "out" / "generated_material_production.json").read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
