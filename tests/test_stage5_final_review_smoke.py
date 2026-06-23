import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.stage5_final_review_smoke import run_stage5_final_review_smoke


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_ready_run(root):
    _write(root / "stage4_build_smoke_report.json", {
        "artifact_role": "stage4_build_smoke_report",
        "ok": True,
        "issues": [],
        "clip_count": 3,
        "timeline_clip_count": 3,
    })
    _write(root / "boundary_report.json", {
        "artifact_role": "boundary_report",
        "stage": "stage5_final_review",
        "pass": True,
        "regressions": [],
    })
    _write(root / "editor_review.json", {
        "artifact_role": "editor_review",
        "decision": "human_review",
        "reason": "ready for final human review",
    })
    _write(root / "rough_cut_plan.json", {
        "artifact_role": "rough_cut_plan",
        "ok": True,
        "gaps": [],
    })
    _write(root / "timeline_build.json", {
        "artifact_role": "timeline_build",
        "clips": [{"segment": 1}],
    })


class Stage5FinalReviewSmokeTest(unittest.TestCase):
    def test_ready_run_passes_with_human_review_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)

            result = run_stage5_final_review_smoke(run_dir)

            self.assertTrue(result["ok"], result)
            report = json.loads((run_dir / "stage5_final_review_smoke_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["artifact_role"], "stage5_final_review_smoke_report")
            self.assertEqual(report["next_action"], "ready_for_render_or_human_review")
            self.assertEqual(report["blocking"], [])
            self.assertEqual(report["inputs"]["stage4_build_smoke_report"], "pass")
            self.assertEqual(report["inputs"]["boundary_report"], "pass")

    def test_stage4_failure_blocks_final_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)
            _write(run_dir / "stage4_build_smoke_report.json", {
                "artifact_role": "stage4_build_smoke_report",
                "ok": False,
                "issues": [{"rule": "timeline_mismatch", "message": "bad timeline"}],
            })

            result = run_stage5_final_review_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["report"]["next_action"], "repair:stage4_build")
            self.assertIn("stage4_build_failed", [item["rule"] for item in result["report"]["blocking"]])

    def test_boundary_failure_blocks_final_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)
            _write(run_dir / "boundary_report.json", {
                "artifact_role": "boundary_report",
                "stage": "stage5_final_review",
                "pass": False,
                "regressions": [{"rule": "caption_readability", "message": "overflow"}],
            })

            result = run_stage5_final_review_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["report"]["next_action"], "repair:stage5_final_review")
            self.assertIn("boundary_failed", [item["rule"] for item in result["report"]["blocking"]])

    def test_verify_failure_blocks_when_verify_result_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)
            _write(run_dir / "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": False,
                "score": 42,
                "issues": [{"rule": "duration_fit", "message": "too short"}],
            })

            result = run_stage5_final_review_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["report"]["next_action"], "repair:verify")
            self.assertIn("verify_failed", [item["rule"] for item in result["report"]["blocking"]])

    def test_missing_editor_review_blocks_final_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)
            (run_dir / "editor_review.json").unlink()

            result = run_stage5_final_review_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["report"]["next_action"], "repair:stage4_build")
            self.assertIn("missing_editor_review", [item["rule"] for item in result["report"]["blocking"]])

    def test_cli_outputs_json_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_ready_run(run_dir)

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/stage5_final_review_smoke.py",
                    "--run",
                    str(run_dir),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["report"]["next_action"], "ready_for_render_or_human_review")


if __name__ == "__main__":
    unittest.main()
