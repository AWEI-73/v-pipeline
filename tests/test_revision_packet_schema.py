import json
import unittest
import tempfile
from pathlib import Path
from video_pipeline_core.revision_packet_schema import RevisionPacket


class TestRevisionPacketSchema(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_to_dict(self):
        targets = [{
            "artifact": "effect_contract.json",
            "field": "prompt_parameters.motion",
            "issue": "motion too fast",
            "suggested_change": "slow down reveal timing"
        }]
        packet = RevisionPacket(
            source_review="effect_design_review.json",
            target_branch="effect-factory",
            problem_type="effect",
            severity="blocking",
            revision_targets=targets
        )

        data = packet.to_dict()
        self.assertEqual(data["artifact_role"], "revision_packet")
        self.assertEqual(data["source_review"], "effect_design_review.json")
        self.assertEqual(data["target_branch"], "effect-factory")
        self.assertEqual(data["problem_type"], "effect")
        self.assertEqual(data["severity"], "blocking")
        self.assertEqual(data["revision_targets"], targets)
        self.assertEqual(data["next_action"], "agent_decide_repair")

    def test_save_and_load(self):
        targets = [{
            "artifact": "effect_contract.json",
            "field": "prompt_parameters.motion",
            "issue": "motion too fast",
            "suggested_change": "slow down reveal timing"
        }]
        packet = RevisionPacket(
            source_review="effect_design_review.json",
            target_branch="effect-factory",
            problem_type="effect",
            severity="blocking",
            revision_targets=targets
        )

        file_path = self.temp_path / "test_revision_packet.json"
        packet.save(file_path)

        # Load back
        loaded = RevisionPacket.load(file_path)
        self.assertEqual(loaded.artifact_role, "revision_packet")
        self.assertEqual(loaded.source_review, "effect_design_review.json")
        self.assertEqual(loaded.target_branch, "effect-factory")
        self.assertEqual(loaded.problem_type, "effect")
        self.assertEqual(loaded.severity, "blocking")
        self.assertEqual(loaded.revision_targets, targets)

    def test_load_validation_errors(self):
        file_path = self.temp_path / "invalid.json"

        # Missing required fields
        file_path.write_text(json.dumps({"target_branch": "effect-factory"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            RevisionPacket.load(file_path)

        # Invalid JSON
        file_path.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(ValueError):
            RevisionPacket.load(file_path)

    def test_rejects_invalid_branch_type_severity_and_empty_targets(self):
        with self.assertRaises(ValueError):
            RevisionPacket(
                source_review="review.json",
                target_branch="stage2_material_map",
                problem_type="effect",
                severity="blocking",
                revision_targets=[{
                    "artifact": "effect_contract.json",
                    "field": "controls",
                    "issue": "bad",
                    "suggested_change": "fix",
                }],
            )
        with self.assertRaises(ValueError):
            RevisionPacket(
                source_review="review.json",
                target_branch="effect-factory",
                problem_type="ci_failure",
                severity="blocking",
                revision_targets=[{
                    "artifact": "effect_contract.json",
                    "field": "controls",
                    "issue": "bad",
                    "suggested_change": "fix",
                }],
            )
        with self.assertRaises(ValueError):
            RevisionPacket(
                source_review="review.json",
                target_branch="effect-factory",
                problem_type="effect",
                severity="fatal",
                revision_targets=[{
                    "artifact": "effect_contract.json",
                    "field": "controls",
                    "issue": "bad",
                    "suggested_change": "fix",
                }],
            )
        with self.assertRaises(ValueError):
            RevisionPacket(
                source_review="review.json",
                target_branch="effect-factory",
                problem_type="effect",
                severity="blocking",
                revision_targets=[],
            )

    def test_rejects_rerun_policy_without_agent_decision(self):
        with self.assertRaises(ValueError):
            RevisionPacket(
                source_review="review.json",
                target_branch="effect-factory",
                problem_type="effect",
                severity="blocking",
                revision_targets=[{
                    "artifact": "effect_contract.json",
                    "field": "controls",
                    "issue": "bad",
                    "suggested_change": "fix",
                }],
                rerun_policy={
                    "allowed": True,
                    "max_attempts": 4,
                    "requires_agent_decision": False,
                },
            )


if __name__ == "__main__":
    unittest.main()
