import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.reviewer_flow_acceptance import run_acceptance


ROOT = Path(__file__).resolve().parents[1]


class ReviewerFlowAcceptanceTest(unittest.TestCase):
    def test_normal_route_smoke_validates_core_reviewers(self):
        result = run_acceptance(level="normal", scenario="route_smoke")
        self.assertTrue(result["ok"], result)
        self.assertEqual(
            result["scenario_reviewers"],
            ["story_director", "material_producer", "editorial_timeline", "technical_verify"],
        )
        self.assertTrue(result["negative_checks"]["technical_verify_rejects_revise_gate"])

    def test_upstream_story_requires_deep_policy(self):
        result = run_acceptance(level="deep", scenario="upstream_story")
        self.assertTrue(result["ok"], result)
        roles = {r["reviewer_role"] for r in result["reviews"]}
        self.assertIn("literary_editor", roles)
        self.assertIn("story_director", roles)
        self.assertIn("generated_material_art_director", roles)

    def test_effects_brownfield_reviewers_are_covered(self):
        result = run_acceptance(level="deep", scenario="effects_brownfield")
        self.assertTrue(result["ok"], result)
        roles = {r["reviewer_role"] for r in result["reviews"]}
        self.assertEqual(
            roles,
            {"editorial_timeline", "audio_subtitle_reviewer", "effect_reviewer", "technical_verify"},
        )

    def test_light_policy_fails_for_effects_brownfield(self):
        result = run_acceptance(level="light", scenario="effects_brownfield")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any("missing scenario reviewer" in e for e in result["errors"]))

    def test_cli_writes_report_packet_and_review_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "reviewer_flow_acceptance.json"
            artifacts = root / "reviewer_artifacts"
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/reviewer_flow_acceptance.py",
                    "--level",
                    "deep",
                    "--scenario",
                    "all",
                    "--artifact-dir",
                    str(artifacts),
                    "--out",
                    str(report),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"], result)
            self.assertTrue((artifacts / "reviewer_policy_packet.json").is_file())
            self.assertTrue((artifacts / "artifact_reviews" / "effect_reviewer.artifact_review.json").is_file())
            self.assertTrue((artifacts / "artifact_reviews" / "literary_editor.artifact_review.json").is_file())


if __name__ == "__main__":
    unittest.main()
