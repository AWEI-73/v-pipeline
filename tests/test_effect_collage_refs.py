import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _material_map(opening: Path, training: Path, reject: Path):
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "real_0001",
            "asset_type": "video",
            "source": str(opening),
            "scenes": [{"start": 0.0, "end": 8.0, "midpoint": 4.0, "caption": "opening scene"}],
        }, {
            "asset_id": "real_0002",
            "asset_type": "image",
            "source": str(training),
            "scenes": [{"caption": "training still"}],
        }, {
            "asset_id": "real_0003",
            "asset_type": "image",
            "source": str(reject),
            "scenes": [{"caption": "bad still"}],
        }],
    }


def _wall_verdict(opening_thumb: Path):
    return {
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "assets": [{
            "asset_id": "real_0001",
            "coarse_status": "keep",
            "visual_role": ["opening"],
            "thumbnail_path": str(opening_thumb),
        }, {
            "asset_id": "real_0002",
            "coarse_status": "keep",
            "visual_role": ["training"],
        }, {
            "asset_id": "real_0003",
            "coarse_status": "reject",
            "visual_role": ["opening"],
        }],
    }


class EffectCollageRefsTest(unittest.TestCase):
    def test_builds_collage_refs_from_reviewed_material_wall(self):
        from video_pipeline_core.effect_collage_refs import build_collage_media_refs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opening = root / "opening.mp4"
            training = root / "training.jpg"
            reject = root / "reject.jpg"
            thumb = root / "opening-thumb.jpg"
            for path in (opening, training, reject, thumb):
                path.write_bytes(b"x")

            artifact = build_collage_media_refs(
                _material_map(opening, training, reject),
                material_wall_review_verdict=_wall_verdict(thumb),
                max_refs=4,
            )

        self.assertEqual(artifact["artifact_role"], "effect_collage_media_refs")
        self.assertTrue(artifact["ok"], artifact)
        self.assertEqual([ref["ref_id"] for ref in artifact["collage_media_refs"]], [
            "real_0001",
            "real_0002",
        ])
        self.assertEqual(artifact["collage_media_refs"][0]["source_asset_id"], "real_0001")
        self.assertTrue(artifact["collage_media_refs"][0]["path"].startswith("file:///"))
        self.assertIn("opening", artifact["collage_media_refs"][0]["label"])
        self.assertEqual(artifact["diagnostics"]["skipped_rejected_count"], 1)

    def test_parses_workbench_media_urls_for_video_thumbnails(self):
        from urllib.parse import quote

        from video_pipeline_core.effect_collage_refs import build_collage_media_refs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "clip.mp4"
            thumb = root / "thumb.jpg"
            source.write_bytes(b"x")
            thumb.write_bytes(b"x")
            thumbnails = {
                "artifact_role": "workbench_thumbnails",
                "version": 1,
                "thumbnails": {
                    "real_0001": "http://localhost:8765/media?src=" + quote(str(thumb), safe=""),
                },
            }
            material_map = {
                "artifact_role": "project_material_map",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "asset_type": "video",
                    "source": str(source),
                    "scenes": [{"caption": "opening"}],
                }],
            }
            verdict = {
                "artifact_role": "material_wall_review_verdict",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "coarse_status": "keep",
                    "visual_role": ["opening"],
                }],
            }

            artifact = build_collage_media_refs(
                material_map,
                material_wall_review_verdict=verdict,
                workbench_thumbnails=thumbnails,
            )

        self.assertEqual(len(artifact["collage_media_refs"]), 1)
        self.assertEqual(artifact["collage_media_refs"][0]["path"], thumb.resolve().as_uri())

    def test_write_collage_refs_cli_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "training.jpg"
            image.write_bytes(b"x")
            material_map = {
                "artifact_role": "project_material_map",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "asset_type": "image",
                    "source": str(image),
                    "scenes": [{"caption": "training still"}],
                }],
            }
            verdict = {
                "artifact_role": "material_wall_review_verdict",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "coarse_status": "keep",
                    "visual_role": ["training"],
                }],
            }
            map_path = root / "project_material_map.json"
            verdict_path = root / "material_wall_review_verdict.json"
            out = root / "effect_collage_media_refs.json"
            map_path.write_text(json.dumps(material_map), encoding="utf-8")
            verdict_path.write_text(json.dumps(verdict), encoding="utf-8")

            from video_pipeline_core.effect_collage_refs import write_collage_media_refs

            written = write_collage_media_refs(map_path, out, material_wall_review_verdict_path=verdict_path)

            self.assertTrue(out.is_file())
            self.assertEqual(written["artifact_role"], "effect_collage_media_refs")
            self.assertEqual(written["collage_media_refs"][0]["source_asset_id"], "real_0001")

    def test_video_tools_cli_writes_collage_refs_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "opening.jpg"
            image.write_bytes(b"x")
            material_map = {
                "artifact_role": "project_material_map",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "asset_type": "image",
                    "source": str(image),
                    "scenes": [{"caption": "opening still"}],
                }],
            }
            verdict = {
                "artifact_role": "material_wall_review_verdict",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "coarse_status": "keep",
                    "visual_role": ["opening"],
                }],
            }
            map_path = root / "project_material_map.json"
            verdict_path = root / "material_wall_review_verdict.json"
            out = root / "effect_collage_media_refs.json"
            map_path.write_text(json.dumps(material_map), encoding="utf-8")
            verdict_path.write_text(json.dumps(verdict), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-collage-refs",
                "--project-map", str(map_path),
                "--wall-verdict", str(verdict_path),
                "--out", str(out),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "effect_collage_media_refs")
            self.assertEqual(payload["collage_media_refs"][0]["source_asset_id"], "real_0001")

    def test_video_wall_request_keyframe_can_supply_video_collage_ref(self):
        from video_pipeline_core.effect_collage_refs import build_collage_media_refs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "training.mp4"
            keyframe = root / "wall_kf_01.jpg"
            source.write_bytes(b"video")
            keyframe.write_bytes(b"jpg")
            material_map = {
                "artifact_role": "project_material_map",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "asset_type": "video",
                    "source": str(source),
                    "scenes": [{"caption": "training video"}],
                }],
            }
            verdict = {
                "artifact_role": "material_wall_review_verdict",
                "version": 1,
                "assets": [{
                    "asset_id": "real_0001",
                    "coarse_status": "keep",
                    "visual_role": ["training"],
                }],
            }
            wall_request = {
                "artifact_role": "material_wall_request",
                "version": 1,
                "batches": [{
                    "batch_id": "video_wall_01",
                    "type": "video_wall",
                    "assets": [{
                        "asset_id": "real_0001",
                        "frames": [{
                            "timestamp_sec": 1.0,
                            "image_path": str(keyframe),
                        }],
                    }],
                }],
            }

            artifact = build_collage_media_refs(
                material_map,
                material_wall_review_verdict=verdict,
                material_wall_request=wall_request,
            )

        self.assertTrue(artifact["ok"], artifact)
        self.assertEqual(len(artifact["collage_media_refs"]), 1)
        ref = artifact["collage_media_refs"][0]
        self.assertEqual(ref["source_asset_id"], "real_0001")
        self.assertEqual(ref["path"], keyframe.resolve().as_uri())
        self.assertEqual(ref["evidence_kind"], "material_wall_keyframe")


if __name__ == "__main__":
    unittest.main()
