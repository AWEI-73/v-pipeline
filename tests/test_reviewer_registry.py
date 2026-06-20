import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import reviewer_registry


ROOT = Path(__file__).resolve().parents[1]


class ReviewerRegistryTest(unittest.TestCase):
    def test_policy_expands_to_expected_roles(self):
        self.assertEqual(
            reviewer_registry.expand_review_policy("light"),
            ["material_producer", "technical_verify"],
        )
        self.assertEqual(
            reviewer_registry.expand_review_policy("normal"),
            ["story_director", "material_producer", "editorial_timeline", "technical_verify"],
        )
        self.assertIn("literary_editor", reviewer_registry.expand_review_policy("deep"))
        self.assertIn("effect_reviewer", reviewer_registry.expand_review_policy("deep"))

    def test_unknown_policy_fails_closed(self):
        with self.assertRaises(ValueError):
            reviewer_registry.expand_review_policy("everything")

    def test_registry_declares_eval_principles_for_every_role(self):
        registry = reviewer_registry.build_reviewer_registry()
        roles = {r["reviewer_role"]: r for r in registry["reviewers"]}
        for role in reviewer_registry.expand_review_policy("deep"):
            self.assertIn(role, roles)
            spec = roles[role]
            self.assertTrue(spec["input_artifacts"], role)
            self.assertTrue(spec["output_artifact"], role)
            self.assertIn(spec["gate_strength"], reviewer_registry.VALID_GATE_STRENGTHS)
            self.assertGreaterEqual(len(spec["eval_principles"]), 3, role)
            self.assertTrue(all(p["criterion"] and p["evidence"] and p["failure_route"]
                                for p in spec["eval_principles"]), role)

    def test_review_artifact_validator_accepts_valid_review(self):
        review = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "story_director",
            "review_type": "creative_review",
            "input_artifact_role": "story_soul_blueprint",
            "decision": "revise",
            "gate_strength": "revise",
            "scores": {"narrative_device": 3},
            "findings": [{"severity": "major", "message": "Ending lacks turn"}],
            "next_action": "revise_story_soul",
        }
        result = reviewer_registry.validate_review_artifact(review)
        self.assertTrue(result["ok"], result)

    def test_review_artifact_validator_rejects_unknown_role_or_gate(self):
        bad_role = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "random_reviewer",
            "decision": "pass",
            "gate_strength": "advisory",
            "findings": [],
        }
        self.assertFalse(reviewer_registry.validate_review_artifact(bad_role)["ok"])
        bad_gate = dict(bad_role, reviewer_role="technical_verify", gate_strength="revise")
        self.assertFalse(reviewer_registry.validate_review_artifact(bad_gate)["ok"])

    def test_cli_writes_policy_packet(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "reviewer_policy_packet.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "reviewer-policy",
                    "--level",
                    "deep",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["artifact_role"], "reviewer_policy_packet")
            self.assertEqual(packet["review_policy"]["level"], "deep")
            self.assertIn("generated_material_art_director", packet["enabled_reviewers"])

    def test_docs_and_command_manifest_reference_reviewer_policy(self):
        for rel in [
            "docs/artifact-reviewer-map.md",
            "docs/video-pipeline-operating-map.md",
            "skills/video-pipeline-route.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("reviewer-policy", text, rel)
            self.assertIn("eval", text.lower(), rel)

        proc = subprocess.run(
            [sys.executable, "video_tools.py", "commands-manifest"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("reviewer-policy", proc.stdout)


if __name__ == "__main__":
    unittest.main()
