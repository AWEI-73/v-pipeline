import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _write_inputs(root: Path) -> tuple[Path, Path, Path]:
    source = root / "training.mp4"
    keyframe = root / "wall_kf_01.jpg"
    source.write_bytes(b"video")
    keyframe.write_bytes(b"jpg")
    project_map = {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "real_0001",
            "asset_type": "video",
            "source": str(source),
            "scenes": [{"caption": "training key moment"}],
        }],
    }
    wall_verdict = {
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "assets": [{
            "asset_id": "real_0001",
            "coarse_status": "keep",
            "visual_role": ["opening"],
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
    project_map_path = root / "project_material_map.json"
    wall_verdict_path = root / "material_wall_review_verdict.json"
    wall_request_path = root / "material_wall_request.json"
    project_map_path.write_text(json.dumps(project_map), encoding="utf-8")
    wall_verdict_path.write_text(json.dumps(wall_verdict), encoding="utf-8")
    wall_request_path.write_text(json.dumps(wall_request), encoding="utf-8")
    return project_map_path, wall_verdict_path, wall_request_path


class RemotionMaterialFirstMemoryAcceptanceTest(unittest.TestCase):
    def test_material_first_memory_acceptance_writes_gate_artifacts_without_final(self):
        from video_pipeline_core.remotion_material_first_acceptance import (
            run_material_first_memory_acceptance,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            project_map, wall_verdict, wall_request = _write_inputs(root)

            report = run_material_first_memory_acceptance(
                run_dir,
                project_map=project_map,
                wall_verdict=wall_verdict,
                wall_request=wall_request,
                max_refs=3,
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["artifact_role"], "remotion_material_first_memory_acceptance_report")
            self.assertEqual(report["failed_stage"], None)
            self.assertEqual(report["summary"]["selected_ref_count"], 1)
            self.assertEqual(report["summary"]["evidence_kinds"], ["material_wall_keyframe"])
            self.assertEqual(report["summary"]["build_component"], "MemoryPhotoWall")
            self.assertFalse((run_dir / "final.mp4").exists())
            for name in [
                "effect_collage_media_refs.json",
                "effect_intent_plan.json",
                "effect_revision_request.json",
                "timeline_build.json",
                "remotion_prompt_pack.json",
                "remotion_worker_outputs.json",
                "remotion_effect_review.json",
                "effect_render_verification.json",
                "remotion_material_first_memory_acceptance_report.json",
            ]:
                self.assertTrue((run_dir / name).is_file(), name)
            verification = json.loads((run_dir / "effect_render_verification.json").read_text(encoding="utf-8"))
            self.assertTrue(verification["pass"], verification)

    def test_cli_runs_material_first_memory_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            project_map, wall_verdict, wall_request = _write_inputs(root)

            proc = subprocess.run([
                sys.executable,
                "tools/remotion_material_first_memory_acceptance.py",
                "--run-dir", str(run_dir),
                "--project-map", str(project_map),
                "--wall-verdict", str(wall_verdict),
                "--wall-request", str(wall_request),
                "--json",
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertFalse((run_dir / "final.mp4").exists())
            self.assertTrue((run_dir / "remotion_material_first_memory_acceptance_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
