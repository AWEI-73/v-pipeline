import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.boundary_fixture_hub import discover_fixtures, run_fixture_hub


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class BoundaryFixtureHubTest(unittest.TestCase):
    def test_discovers_stage_fixtures_under_explicit_root_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "stage5_caption" / "input" / "boundary_config.json", {
                "stage": "stage5_final_review",
                "expected": {"pass": True},
            })
            _write(root / "not_a_fixture" / "boundary_config.json", {
                "stage": "stage5_final_review",
            })

            fixtures = discover_fixtures(root)

            self.assertEqual(len(fixtures), 1)
            self.assertEqual(fixtures[0]["name"], "stage5_caption")
            self.assertEqual(fixtures[0]["stage"], "stage5_final_review")

    def test_runs_fixture_batch_and_writes_manifest_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "stage5_pass" / "input"
            _write(input_dir / "boundary_config.json", {
                "stage": "stage5_final_review",
                "expected": {"pass": True},
            })
            _write(input_dir / "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": True,
                "score": 96,
            })

            summary = run_fixture_hub(root)

            self.assertTrue(summary["pass"], summary)
            self.assertEqual(summary["fixture_count"], 1)
            self.assertEqual(summary["results"][0]["name"], "stage5_pass")
            self.assertEqual(summary["results"][0]["stage"], "stage5_final_review")
            self.assertTrue((root / "boundary_fixture_report.json").exists())

    def test_repo_boundary_fixtures_cover_landing_stages(self):
        root = Path(__file__).resolve().parents[1] / "examples" / "boundary_fixtures"

        summary = run_fixture_hub(root)

        self.assertTrue(summary["pass"], summary)
        stages = {item["stage"] for item in summary["results"]}
        self.assertEqual(stages, {
            "stage1_story_blueprint",
            "stage3_review_apply",
            "stage4_dry_build",
            "stage5_final_review",
        })

    def test_cli_runs_from_repo_root(self):
        repo = Path(__file__).resolve().parents[1]
        fixture_root = repo / "examples" / "boundary_fixtures"

        proc = subprocess.run(
            [
                sys.executable,
                "tools/boundary_fixture_hub.py",
                str(fixture_root),
                "--json",
            ],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["pass"], payload)
        self.assertEqual(payload["fixture_count"], 4)


if __name__ == "__main__":
    unittest.main()
