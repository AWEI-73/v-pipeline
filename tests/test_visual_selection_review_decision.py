import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.visual_selection_gate import evaluate_visual_selection_gate
from video_pipeline_core.visual_selection_review_decision import (
    build_visual_selection_review,
    write_visual_selection_review,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "write_visual_selection_review.py"


def _candidate_payload():
    return {
        "artifact_role": "visual_selection_candidates",
        "version": 1,
        "selections": [
            {
                "beat_id": "newcomer_training_start",
                "source_relative_path": "工安早會/IMG_2120.JPG",
                "candidate_source": "token_folder_match",
            },
            {
                "beat_id": "basic_training",
                "source_relative_path": "工安早會/IMG_2124.JPG",
                "candidate_source": "token_folder_match",
            },
            {
                "beat_id": "supervisor_source_speech",
                "source_relative_path": "主任勉勵/IMG_2141.MOV",
                "candidate_source": "token_folder_match",
            },
        ],
    }


def _accepted_decisions():
    return [
        {
            "beat_id": "newcomer_training_start",
            "decision": "accepted",
            "reviewer_type": "agent_visual_review",
            "candidate_source": "agent_visual_review",
            "representative_frame": "frames/newcomer.jpg",
            "reason": "visible trainees at morning roll call",
            "forbidden_role_flags_checked": True,
            "forbidden_role_flags": {
                "supervisor_primary": False,
                "director_primary": False,
                "portrait_primary": False,
            },
        },
        {
            "beat_id": "basic_training",
            "decision": "accepted",
            "reviewer_type": "agent_visual_review",
            "candidate_source": "agent_visual_review",
            "representative_frame": "frames/basic.jpg",
            "reason": "visible training preparation",
            "forbidden_role_flags_checked": True,
            "forbidden_role_flags": {
                "supervisor_primary": False,
                "director_primary": False,
                "portrait_primary": False,
            },
        },
        {
            "beat_id": "supervisor_source_speech",
            "decision": "accepted",
            "reviewer_type": "agent_visual_review",
            "candidate_source": "agent_visual_review",
            "representative_frame": "frames/supervisor.jpg",
            "reason": "talking-head supervisor source-speech clip",
            "forbidden_role_flags_checked": True,
            "video_evidence": True,
            "audio_evidence": True,
            "speech_evidence": True,
        },
    ]


class VisualSelectionReviewDecisionTest(unittest.TestCase):
    def test_accepted_review_requires_visual_evidence(self):
        decisions = _accepted_decisions()
        decisions[0].pop("representative_frame")

        with self.assertRaises(ValueError):
            build_visual_selection_review(_candidate_payload(), decisions)

    def test_accepted_newcomer_basic_fails_on_forbidden_primary_flags(self):
        decisions = _accepted_decisions()
        decisions[1]["forbidden_role_flags"]["supervisor_primary"] = True

        with self.assertRaises(ValueError):
            build_visual_selection_review(_candidate_payload(), decisions)

    def test_supervisor_source_speech_requires_video_audio_speech_evidence(self):
        decisions = _accepted_decisions()
        decisions[2].pop("speech_evidence")

        with self.assertRaises(ValueError):
            build_visual_selection_review(_candidate_payload(), decisions)

    def test_rejected_and_needs_repick_write_review_but_gate_blocks(self):
        decisions = [
            {
                "beat_id": "newcomer_training_start",
                "decision": "rejected",
                "reviewer_type": "human",
                "reason": "wrong primary visual",
            },
            {
                "beat_id": "basic_training",
                "decision": "needs_repick",
                "reviewer_type": "human",
                "reason": "needs visually confirmed training material",
            },
        ]
        review = build_visual_selection_review(_candidate_payload(), decisions)

        gate = evaluate_visual_selection_gate(review)

        self.assertFalse(gate["pass"])
        self.assertEqual(
            [item["rule"] for item in gate["blocking"]],
            ["visual_selection_rejected", "visual_selection_needs_repick"],
        )

    def test_accepted_review_with_valid_visual_evidence_passes_gate(self):
        review = build_visual_selection_review(_candidate_payload(), _accepted_decisions())

        gate = evaluate_visual_selection_gate(review)

        self.assertTrue(gate["pass"], gate)
        self.assertEqual(gate["accepted_visual_evidence_count"], 3)

    def test_cli_fixture_writes_review_and_gate_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "visual_selection_candidates.json"
            candidates.write_text(
                json.dumps(_candidate_payload(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            out_dir = root / "out"

            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--candidates",
                    str(candidates),
                    "--out-dir",
                    str(out_dir),
                    "--fixture",
                    "accepted-valid",
                    "--json",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            review = json.loads((out_dir / "visual_selection_review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["artifact_role"], "visual_selection_review")
            self.assertTrue(json.loads(proc.stdout)["gate_pass"])


if __name__ == "__main__":
    unittest.main()
