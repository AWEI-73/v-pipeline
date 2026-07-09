import unittest
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.graduation_product_route_runner import ROUTE_STAGES


class RouteClosureIntegrityTest(unittest.TestCase):
    def test_invalid_route_kind_is_reported(self):
        from video_pipeline_core.route_closure_integrity import validate_route_closure

        result = validate_route_closure(
            route_stages=[
                {
                    "stage_id": "bad_stage",
                    "owner": "main-pipeline",
                    "artifact": "bad.json",
                    "kind": "maybe_review",
                }
            ],
            branch_registry={
                "branches": [
                    {
                        "branch_id": "main-pipeline",
                        "canonical_outputs": ["bad.json"],
                        "handoff_outputs": [],
                    }
                ]
            },
            next_actions={"repair_or_complete_upstream_gate"},
            reviewer_roles=set(),
        )

        self.assertFalse(result["ok"])
        self.assertIn("invalid_kind:bad_stage:maybe_review", result["errors"])

    def test_signed_review_stage_without_review_artifact_is_reported(self):
        from video_pipeline_core.route_closure_integrity import validate_route_closure

        result = validate_route_closure(
            route_stages=[
                {
                    "stage_id": "signed_missing_review",
                    "owner": "main-pipeline",
                    "artifact": "gate.json",
                    "kind": "signed_review",
                }
            ],
            branch_registry={
                "branches": [
                    {
                        "branch_id": "main-pipeline",
                        "canonical_outputs": ["gate.json"],
                        "handoff_outputs": [],
                    }
                ]
            },
            next_actions={"repair_or_complete_upstream_gate"},
            reviewer_roles=set(),
        )

        self.assertFalse(result["ok"])
        self.assertIn("missing_review_artifact:signed_missing_review", result["errors"])

    def test_current_graduation_route_closure_is_valid(self):
        from video_pipeline_core.route_closure_integrity import validate_current_route_closure

        result = validate_current_route_closure(Path.cwd())

        self.assertTrue(result["ok"], result)
        stage_ids = {stage["stage_id"] for stage in result["route_stages"]}
        self.assertEqual(stage_ids, {stage["stage_id"] for stage in ROUTE_STAGES})

    def test_cli_runs_directly_from_tools_path(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "route_closure_integrity.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/route_closure_integrity.py",
                    "--repo-root",
                    ".",
                    "--out",
                    str(out),
                    "--json",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
