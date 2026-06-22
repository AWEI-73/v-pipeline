import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.reviewer_aggregation import aggregate_reviews


ROOT = Path(__file__).resolve().parents[1]


def _review(role: str, decision: str, gate: str, *, finding_code: str, next_action: str) -> dict:
    return {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": role,
        "decision": decision,
        "gate_strength": gate,
        "findings": [
            {
                "severity": "major",
                "code": finding_code,
                "message": f"{role} found {finding_code}",
                "failure_route": next_action,
            }
        ],
        "next_action": next_action,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ReviewerAggregationTest(unittest.TestCase):
    def test_aggregate_reviews_prioritizes_hard_gates_before_creative_revisions(self):
        creative = _review(
            "story_director",
            "revise",
            "revise",
            finding_code="visual_rhythm_too_sparse",
            next_action="revise_shot_plan",
        )
        material = _review(
            "material_producer",
            "block",
            "hard_gate",
            finding_code="missing_required_material",
            next_action="await_material",
        )

        payload = aggregate_reviews([creative, material])

        self.assertEqual(payload["artifact_role"], "reviewer_aggregation")
        self.assertEqual(payload["overall_decision"], "block")
        self.assertEqual(payload["next_action"], "await_material")
        self.assertEqual(payload["priority_queue"][0]["reviewer_role"], "material_producer")
        self.assertEqual(payload["priority_queue"][0]["finding_code"], "missing_required_material")
        self.assertEqual(payload["priority_queue"][1]["reviewer_role"], "story_director")

    def test_aggregate_reviews_turns_revise_into_guided_route_task_packet(self):
        creative = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "editorial_timeline",
            "status": "revise",
            "decision": "revise",
            "blocking_level": "soft_block",
            "gate_strength": "revise",
            "findings": [
                {
                    "severity": "major",
                    "code": "pace_too_slow",
                    "message": "Story pauses too long in the middle.",
                    "failure_route": "workbench_edit",
                }
            ],
            "required_revisions": ["Shorten the middle hold and add one visual beat."],
            "recommended_actions": ["Open workbench and revise timing."],
            "handoff_to": "workbench_edit",
            "can_continue_to_delivery": False,
        }

        payload = aggregate_reviews([creative])

        self.assertEqual(payload["overall_status"], "revise")
        self.assertFalse(payload["can_continue_to_delivery"])
        self.assertEqual(payload["route_task_packet"]["handoff_to"], "workbench_edit")
        self.assertEqual(payload["route_task_packet"]["required_revisions"],
                         ["Shorten the middle hold and add one visual beat."])

    def test_aggregate_reviews_blocks_delivery_when_unresolved_revise_exists(self):
        creative = _review(
            "story_director",
            "revise",
            "revise",
            finding_code="missing_emotional_turn",
            next_action="revise_shot_plan",
        )

        payload = aggregate_reviews([creative])

        self.assertEqual(payload["overall_status"], "revise")
        self.assertFalse(payload["can_continue_to_delivery"])

    def test_cli_writes_reviewer_aggregation_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            creative_path = root / "story_director_review.json"
            material_path = root / "material_producer_review.json"
            out = root / "reviewer_aggregation.json"
            _write_json(
                creative_path,
                _review(
                    "story_director",
                    "revise",
                    "revise",
                    finding_code="visual_rhythm_too_sparse",
                    next_action="revise_shot_plan",
                ),
            )
            _write_json(
                material_path,
                _review(
                    "material_producer",
                    "block",
                    "hard_gate",
                    finding_code="missing_required_material",
                    next_action="await_material",
                ),
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "reviewer-aggregate",
                    "--review",
                    str(creative_path),
                    "--review",
                    str(material_path),
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
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_decision"], "block")
            self.assertEqual(payload["priority_queue"][0]["next_action"], "await_material")


if __name__ == "__main__":
    unittest.main()
