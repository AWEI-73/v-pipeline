import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from video_pipeline_core.generated_material_producer import (
    produce_generated_materials,
)


def _fallback_artifact():
    return {
        "artifact_role": "material_generation_fallback",
        "version": 1,
        "ok": True,
        "generation_jobs": [
            {
                "job_id": "gen_report_01",
                "need_id": "nd_report_memory",
                "source_type": "generated",
                "status": "planned",
                "media_type": "generated_image",
                "panel_count": 1,
                "story_function": "open the report-writing memory frame",
                "emotion": "quiet anticipation",
                "visual_family": "report_memory_insert",
                "angle_scale": "close",
                "action_family": "writing_reflection",
                "subject": "anonymous trainee hands writing internship report",
                "prompt": "0.66% of life; anonymous trainee hands writing an internship report; helmet beside notebook; warm desk lamp; 85mm close-up; muted amber grade",
                "negative_prompt": "text, watermark, readable logo, distorted hands",
                "review_criteria": [
                    "supports the beat story_function rather than decorative filler",
                    "must not be accepted without visual review and material-map satisfies edge",
                ],
                "material_map_return": {
                    "must_reingest": True,
                    "initial_satisfies_status": "candidate",
                },
                "honesty": {"must_not_claim_real_event": True},
            },
            {
                "job_id": "gen_bridge_01",
                "need_id": "nd_training_bridge",
                "source_type": "generated",
                "status": "planned",
                "media_type": "generated_image",
                "panel_count": 1,
                "story_function": "bridge hard training beats into one day of memory",
                "emotion": "breathing transition",
                "visual_family": "training_center_bridge",
                "angle_scale": "wide",
                "action_family": "empty_space_transition",
                "subject": "generic training center hallway without signage",
                "prompt": "0.66% of life; empty generic training center hallway before class; morning light; no readable signage; 35mm wide shot; cool blue-gray grade",
                "negative_prompt": "text, logo, people, fake event banner",
                "review_criteria": ["chapter bridge only"],
                "material_map_return": {
                    "must_reingest": True,
                    "initial_satisfies_status": "candidate",
                },
                "honesty": {"must_not_claim_real_event": True},
            },
        ],
        "review_gate": {
            "generated_assets_enter_as": "candidate",
            "must_reingest": True,
            "must_not_claim_real_footage": True,
        },
    }


def _needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "generated-flow-test",
        "needs": [
            {
                "need_id": "nd_report_memory",
                "category": "story",
                "type": "symbolic_panel",
                "purpose": "open the report-writing memory frame",
                "count": 1,
                "must_have": True,
                "fallback_tier": 2,
                "fallback_options": ["generated symbolic insert"],
            },
            {
                "need_id": "nd_training_bridge",
                "category": "bridge",
                "type": "chapter_bridge",
                "purpose": "bridge hard training beats into one day of memory",
                "count": 1,
                "must_have": False,
                "fallback_tier": 3,
                "fallback_options": ["generated chapter bridge"],
            },
        ],
    }


class GeneratedMaterialProducerTest(unittest.TestCase):
    def test_produce_writes_images_manifest_maps_and_quality_review(self):
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(
                _fallback_artifact(),
                td,
                material_needs=_needs(),
                style_profile={
                    "palette": ["#1d3557", "#f1c27d", "#f7f3e3"],
                    "look": "documentary memory inserts",
                    "aspect_ratio": "16:9",
                },
                provider="codex_imagegen",
                renderer="test_pil",
                allow_test_renderer=True,
            )
            out = Path(td)

            self.assertTrue(result["ok"], result.get("errors"))
            self.assertEqual(result["summary"]["image_count"], 2)
            self.assertTrue((out / "generated_asset_manifest.json").exists())
            self.assertTrue((out / "generated_material_quality_review.json").exists())
            self.assertTrue((out / "project_material_map.json").exists())
            for item in result["outputs"]:
                img = Path(item["file"])
                self.assertTrue(img.exists())
                with Image.open(img) as im:
                    self.assertEqual(im.size, (1280, 720))
                self.assertEqual(item["source"], "generated")
                self.assertTrue(item["forbidden_as_truth"])
                self.assertGreaterEqual(item["quality_score"], 80)
            review = json.loads(
                (out / "generated_material_quality_review.json").read_text(encoding="utf-8")
            )
            first = review["items"][0]
            self.assertIn("rubric", first)
            self.assertEqual(
                set(first["rubric"]),
                {
                    "story_fit",
                    "style_consistency",
                    "character_continuity",
                    "camera_language",
                    "truth_boundary",
                    "need_coverage",
                },
            )
            self.assertTrue(all("score" in value and "pass" in value
                                for value in first["rubric"].values()))

            project_map = json.loads((out / "project_material_map.json").read_text(encoding="utf-8"))
            self.assertEqual(project_map["artifact_role"], "project_material_map")
            self.assertEqual(project_map["metrics"]["asset_count"], 2)
            edge = project_map["assets"][0]["scenes"][0]["satisfies"][0]
            self.assertEqual(edge["status"], "candidate")
            self.assertIn(edge["need_id"], {"nd_report_memory", "nd_training_bridge"})

    def test_fails_closed_when_fallback_artifact_is_not_ok(self):
        bad = _fallback_artifact()
        bad["ok"] = False
        bad["errors"] = ["delta broken"]
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(bad, td)
            self.assertFalse(result["ok"])
            self.assertEqual(result["outputs"], [])
            self.assertFalse((Path(td) / "project_material_map.json").exists())

    def test_quality_review_penalizes_prompt_without_story_or_camera_language(self):
        artifact = _fallback_artifact()
        artifact["generation_jobs"][0]["prompt"] = "nice picture"
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(
                artifact, td, material_needs=_needs(), renderer="test_pil",
                allow_test_renderer=True)
            review = json.loads(
                (Path(td) / "generated_material_quality_review.json").read_text(encoding="utf-8")
            )
            weak = next(item for item in review["items"]
                        if item["job_id"].startswith("gen_report_01"))
            self.assertLess(weak["score"], 80)
            self.assertIn("story_function_missing_from_prompt", weak["findings"])
            self.assertFalse(weak["rubric"]["story_fit"]["pass"])
            self.assertFalse(weak["rubric"]["camera_language"]["pass"])
            self.assertFalse(result["quality_gate"]["pass"])

    def test_quality_review_penalizes_missing_style_and_character_anchors(self):
        artifact = _fallback_artifact()
        artifact["generation_jobs"][0]["prompt"] = (
            "anonymous trainee hands writing an internship report; 85mm close shot"
        )
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(
                artifact,
                td,
                material_needs=_needs(),
                renderer="test_pil",
                allow_test_renderer=True,
                style_profile={
                    "look": "documentary memory inserts",
                    "style_anchors": ["muted amber grade"],
                    "character_anchors": ["helmet beside notebook"],
                    "palette": ["#1d3557", "#f1c27d", "#f7f3e3"],
                },
            )
            review = json.loads(
                (Path(td) / "generated_material_quality_review.json").read_text(encoding="utf-8")
            )
            weak = next(item for item in review["items"]
                        if item["job_id"].startswith("gen_report_01"))
            self.assertFalse(result["quality_gate"]["pass"])
            self.assertFalse(weak["rubric"]["style_consistency"]["pass"])
            self.assertFalse(weak["rubric"]["character_continuity"]["pass"])

    def test_panel_count_expands_to_multiple_candidate_assets(self):
        artifact = _fallback_artifact()
        artifact["generation_jobs"][0]["panel_count"] = 2
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(
                artifact, td, material_needs=_needs(), renderer="test_pil",
                allow_test_renderer=True)
            report_outputs = [
                item for item in result["outputs"]
                if item["need_id"] == "nd_report_memory"
            ]
            self.assertEqual(len(report_outputs), 2)
            project_map = json.loads(
                (Path(td) / "project_material_map.json").read_text(encoding="utf-8"))
            count = 0
            for asset in project_map["assets"]:
                for scene in asset["scenes"]:
                    for edge in scene["satisfies"]:
                        if edge["need_id"] == "nd_report_memory":
                            count += 1
            self.assertEqual(count, 2)

    def test_cli_runs_small_project_flow(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fallback = d / "material_generation_fallback.json"
            needs = d / "material_needs.json"
            out_dir = d / "out"
            fallback.write_text(json.dumps(_fallback_artifact(), ensure_ascii=False), encoding="utf-8")
            needs.write_text(json.dumps(_needs(), ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-material-produce",
                    str(fallback),
                    "--needs",
                    str(needs),
                    "--out-dir",
                    str(out_dir),
                    "--renderer",
                    "test_pil",
                    "--allow-test-renderer",
                    "--provider",
                    "codex_imagegen",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            report = json.loads((out_dir / "generated_material_production.json").read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertEqual(report["summary"]["image_count"], 2)

    def test_test_renderer_requires_explicit_allow_flag_and_writes_no_images(self):
        with tempfile.TemporaryDirectory() as td:
            result = produce_generated_materials(
                _fallback_artifact(),
                td,
                material_needs=_needs(),
                renderer="test_pil",
                provider="codex_imagegen",
            )

            self.assertFalse(result["ok"])
            self.assertIn("test_pil renderer is test-only", "; ".join(result["errors"]))
            self.assertFalse((Path(td) / "generated_images").exists())
            self.assertEqual(result["summary"]["image_count"], 0)

    def test_cli_refuses_test_renderer_without_allow_flag(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fallback = d / "material_generation_fallback.json"
            needs = d / "material_needs.json"
            out_dir = d / "out"
            fallback.write_text(json.dumps(_fallback_artifact(), ensure_ascii=False), encoding="utf-8")
            needs.write_text(json.dumps(_needs(), ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-material-produce",
                    str(fallback),
                    "--needs",
                    str(needs),
                    "--out-dir",
                    str(out_dir),
                    "--renderer",
                    "test_pil",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("test_pil renderer is test-only", proc.stdout + proc.stderr)
            self.assertFalse((out_dir / "generated_images").exists())


if __name__ == "__main__":
    unittest.main()
