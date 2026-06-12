import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import generated_assets


class GeneratedAssetsTest(unittest.TestCase):
    def _contract(self):
        return {
            "segments": [
                {
                    "segment": 1,
                    "core": {
                        "section_role": "montage",
                        "story_purpose": "抽象概念補圖",
                        "timeline_source": "beat",
                    },
                    "material_fit": {
                        "visual_desc": "乾淨明亮的工作空間與團隊協作",
                        "search_query": "clean bright workspace teamwork",
                        "fallback_policy": "generated",
                        "reason": "stock 不易命中特定概念",
                    },
                    "audio": {"role": "music", "reason": "r"},
                    "text_layer": "none",
                    "visual_style": {"layout": "single", "pace": "hold", "reason": "r"},
                },
                {
                    "segment": 2,
                    "core": {
                        "section_role": "hold",
                        "story_purpose": "主任本人致詞",
                        "timeline_source": "fixed",
                        "review_required": True,
                    },
                    "material_fit": {
                        "visual_desc": "主任本人站在講台致詞",
                        "must_include": "主任本人",
                        "fallback_policy": "generated",
                        "reason": "identity 段不可生成替代",
                    },
                    "audio": {"role": "duck", "reason": "r"},
                    "text_layer": {"subtitle": "auto", "reason": "r"},
                    "visual_style": {"layout": "single", "pace": "hold", "reason": "r"},
                },
            ]
        }

    def test_build_requests_only_for_allowed_generated_segments(self):
        request = generated_assets.build_generated_asset_requests(
            self._contract(),
            provider_priority=["assistant_imagegen", "antigravity"],
        )
        self.assertEqual(request["artifact_role"], "generated_asset_requests")
        self.assertEqual(request["provider_priority"], ["assistant_imagegen", "antigravity"])
        self.assertEqual(len(request["items"]), 1)
        item = request["items"][0]
        self.assertEqual(item["segment"], 1)
        self.assertEqual(item["provider"], "assistant_imagegen")
        self.assertTrue(item["forbidden_as_truth"])
        self.assertIn("乾淨明亮的工作空間", item["prompt"])
        # the raw desc is a seed, not a generation-ready prompt: the request must
        # carry the expansion obligation + hints so no agent feeds it verbatim
        self.assertTrue(item["prompt_expansion_required"])
        self.assertIn("story_purpose", item["expansion_hints"])
        self.assertIn("generative-director", item["expansion_hints"]["skill"])

    def test_rejects_comfyui_provider_priority(self):
        with self.assertRaises(ValueError):
            generated_assets.build_generated_asset_requests(
                self._contract(),
                provider_priority=["comfyui"],
            )

    def test_write_manifest_records_external_outputs_without_truth_claim(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            generated_file = outdir / "seg1.png"
            generated_file.write_bytes(b"png")
            request = generated_assets.build_generated_asset_requests(self._contract())
            result = generated_assets.write_generated_asset_manifest(
                request,
                [{"segment": 1, "provider": "assistant_imagegen", "file": str(generated_file)}],
                outdir / "generated_asset_manifest.json",
            )
            manifest = json.loads(Path(result).read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifact_role"], "generated_asset_manifest")
        self.assertEqual(manifest["items"][0]["source"], "generated")
        self.assertEqual(manifest["items"][0]["provider"], "assistant_imagegen")
        self.assertTrue(manifest["items"][0]["external_provider"])
        self.assertTrue(manifest["items"][0]["forbidden_as_truth"])

    def test_write_manifest_from_outputs_file_validates_external_files(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            generated_file = outdir / "seg1.png"
            generated_file.write_bytes(b"png")
            request = generated_assets.build_generated_asset_requests(self._contract())
            request_path = outdir / "generated_asset_requests.json"
            outputs_path = outdir / "generated_asset_outputs.json"
            manifest_path = outdir / "generated_asset_manifest.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            outputs_path.write_text(json.dumps({
                "items": [{"segment": 1, "file": str(generated_file)}]
            }), encoding="utf-8")

            result = generated_assets.write_generated_asset_manifest_from_outputs(
                request_path,
                outputs_path,
                manifest_path,
            )

            manifest = json.loads(Path(result).read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_role"], "generated_asset_manifest")
            self.assertEqual(manifest["items"][0]["provider"], "assistant_imagegen")
            self.assertEqual(manifest["items"][0]["file"], str(generated_file))

    def test_write_manifest_from_outputs_file_rejects_missing_external_file(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            request = generated_assets.build_generated_asset_requests(self._contract())
            request_path = outdir / "generated_asset_requests.json"
            outputs_path = outdir / "generated_asset_outputs.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            outputs_path.write_text(json.dumps({
                "items": [{"segment": 1, "file": str(outdir / "missing.png")}]
            }), encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                generated_assets.write_generated_asset_manifest_from_outputs(
                    request_path,
                    outputs_path,
                    outdir / "generated_asset_manifest.json",
                )

    def test_video_tools_generated_manifest_cli_exposes_runtime_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            generated_file = outdir / "seg1.png"
            generated_file.write_bytes(b"png")
            request = generated_assets.build_generated_asset_requests(self._contract())
            request_path = outdir / "generated_asset_requests.json"
            outputs_path = outdir / "generated_asset_outputs.json"
            manifest_path = outdir / "generated_asset_manifest.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            outputs_path.write_text(json.dumps({
                "items": [{"segment": 1, "file": str(generated_file)}]
            }), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-manifest",
                    str(request_path),
                    "--outputs",
                    str(outputs_path),
                    "--out",
                    str(manifest_path),
                ],
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_role"], "generated_asset_manifest")
            self.assertEqual(manifest["items"][0]["file"], str(generated_file))

    def test_attach_generated_manifest_updates_artifact_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            artifact_manifest = outdir / "artifact_manifest.json"
            generated_manifest = outdir / "generated_asset_manifest.json"
            artifact_manifest.write_text(json.dumps({
                "artifact_role": "artifact_manifest",
                "generated_asset_requests": "generated_asset_requests.json",
            }), encoding="utf-8")
            generated_manifest.write_text(json.dumps({
                "artifact_role": "generated_asset_manifest",
                "items": [],
            }), encoding="utf-8")

            result = generated_assets.attach_generated_manifest_to_artifact_manifest(
                artifact_manifest,
                generated_manifest,
            )

            self.assertEqual(result, str(artifact_manifest))
            payload = json.loads(artifact_manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["generated_asset_manifest"], str(generated_manifest))


if __name__ == "__main__":
    unittest.main()
