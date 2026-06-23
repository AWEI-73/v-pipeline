import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pipeline_home import summarize_run


def _write(root, name, payload):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class PipelineHomeTest(unittest.TestCase):
    def test_material_first_intent_routes_to_stage2(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "video_type": "graduation-event",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage2_material_map")
            self.assertIn("video_intent.json", summary["read"])

    def test_structure_first_intent_routes_to_stage1(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "structure-first",
                "video_type": "storybook",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage1_story_blueprint")
            self.assertIn("video_intent.json", summary["read"])

    def test_story_blueprint_routes_to_material_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "story_world.json", {"artifact_role": "story_world"})
            _write(tmp, "screenplay_beats.json", {"artifact_role": "screenplay_beats"})
            _write(tmp, "material_needs.json", {"artifact_role": "material_needs"})

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage2_material_map")
            self.assertIn("material_needs.json", summary["read"])

    def test_build_ready_lifecycle_routes_to_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "build_ready",
                "can_build": True,
                "next_action": "build",
                "refs": {
                    "material_delta": "material_delta.json",
                    "project_material_map": "project_material_map.json",
                },
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage4_dry_build")
            self.assertIn("boundary_smoke.py", summary["next"])
            self.assertIn("material_delta.json", summary["read"])

    def test_segment_contract_routes_to_stage4_without_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "segment_contract.json", {
                "artifact_role": "segment_contract",
                "segments": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage4_dry_build")
            self.assertIn("segment_contract.json", summary["read"])

    def test_timeline_routes_to_stage5_without_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "timeline_build.json", {"artifact_role": "timeline_build"})
            _write(tmp, "editor_review.json", {"artifact_role": "editor_review"})

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertIn("timeline_build.json", summary["read"])

    def test_await_map_review_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "await_map_review",
                "can_build": False,
                "next_action": "await_map_review",
                "refs": {
                    "material_delta": "material_delta.json",
                    "project_material_map": "project_material_map.json",
                },
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage3_review_apply")
            self.assertEqual(summary["resume"], "stage4_dry_build")
            self.assertIn("await_map_review", summary["reason"])

    def test_verify_pass_routes_to_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "final.mp4").write_bytes(b"fake video")
            _write(tmp, "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": True,
                "score": 98,
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "done")
            self.assertEqual(summary["cursor"], "complete")
            self.assertIsNone(summary["next"])

    def test_verify_pass_overrides_stale_build_ready_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "final.mp4").write_bytes(b"fake video")
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "build_ready",
                "can_build": True,
            })
            _write(tmp, "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": True,
                "score": 99,
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "done")
            self.assertEqual(summary["cursor"], "complete")

    def test_failed_boundary_report_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "boundary_report.json", {
                "artifact_role": "boundary_report",
                "stage": "stage5_final_review",
                "pass": False,
                "regressions": ["expected blocking artifact 'caption_audit'"],
                "refs": {"final_review": "actual/final_review_boundary.json"},
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertIn("caption_audit", summary["reason"])
            self.assertIn("actual/final_review_boundary.json", summary["read"])

    def test_cli_prints_json_contract(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "await_map_review",
                "can_build": False,
                "next_action": "await_map_review",
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/pipeline_home.py",
                    "--run",
                    tmp,
                    "--json",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["mode"], "repair")
            self.assertEqual(payload["cursor"], "stage3_review_apply")


if __name__ == "__main__":
    unittest.main()
